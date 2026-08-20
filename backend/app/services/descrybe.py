"""
Legal AI OS — Descrybe Legal Engine Service

Async wrapper over the ``descrybe-legal-engine`` SDK. Descrybe has no static
API key: access is per-user OAuth, and every tool call goes to Descrybe's
Streamable HTTP MCP endpoint (``https://mcp.descrybe.com/mcp``).

This client resolves the current user's access token from
``app.services.descrybe_oauth`` (auto-refreshing on expiry) and routes each
query type to the matching Descrybe tool. Every query is cached in Postgres
and audited.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.database import get_supabase
from app.services.audit import AuditTrail


# ---------------------------------------------------------------------------
# Descrybe Legal Engine tool names (MCP endpoint)
# ---------------------------------------------------------------------------
TOOL_SEARCH_CONCEPT = "search_cases_by_concept"
TOOL_SEARCH_TEXT = "search_case_text"
TOOL_SEARCH_LAWS = "search_laws_and_rules"
TOOL_RESOLVE = "find_case_from_reference"
TOOL_CASE_DETAILS = "get_case_details"
TOOL_CASE_SUMMARY = "get_case_summary"
TOOL_CASE_PASSAGES = "get_case_passages"
TOOL_CASE_STATUS = "check_case_status"
TOOL_CITING = "find_cases_that_cite"
TOOL_VERIFY_QUOTE = "verify_quote"
TOOL_EXTRACT_REFS = "extract_case_references"
TOOL_CASE_PDF = "get_case_pdf"
TOOL_ANALYZE = "analyze_legal_question"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass
class ResearchResult:
    """A single legal research result normalized across source types."""

    source: str = "descrybe"
    source_id: str | None = None
    case_id: str | None = None
    title: str = ""
    citation: str | None = None
    jurisdiction: str | None = None
    court: str | None = None
    decision_year: int | None = None
    source_url: str | None = None
    snippet: str | None = None
    summary: str | None = None
    full_text: str | None = None
    passages: list[dict] = field(default_factory=list)
    relevance_score: float | None = None
    treatment: str | None = None
    treatment_category: str | None = None
    is_good_law: bool | None = None
    authority_label: str | None = None
    why_relevant: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class ResearchResponse:
    """Aggregated response from a research query."""

    query_id: UUID | None = None
    query_type: str = ""
    query_text: str = ""
    cached: bool = False
    results: list[ResearchResult] = field(default_factory=list)
    processing_time_ms: int = 0
    cost_usd: float = 0.0
    raw_response: dict | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class DescrybeClient:
    """
    Async Descrybe client backed by the DLE SDK.

    Construct with either ``user_id`` (resolve token via the OAuth store) or an
    explicit ``access_token_provider`` callable. Raises a clear error if the
    user has not connected Descrybe yet.
    """

    def __init__(
        self,
        user_id: UUID | None = None,
        access_token_provider: Callable[[], str | None] | None = None,
    ):
        if access_token_provider is None and user_id is not None:
            from app.services.descrybe_oauth import get_access_token

            access_token_provider = lambda: get_access_token(user_id)

        self._access_token_provider = access_token_provider
        self._engine = None
        self.cache_ttl = settings.descrybe_cache_ttl_seconds
        self.audit = AuditTrail()

    def _get_engine(self):
        """Lazily build the DLE LegalEngine wrapper."""
        if self._engine is None:
            from descrybe_legal_engine import LegalEngine
            from descrybe_legal_engine.config import DLEConfig

            config = DLEConfig(
                issuer_url=settings.descrybe_issuer_url.rstrip("/"),
                mcp_url=settings.descrybe_mcp_url,
                scopes=tuple(s for s in settings.descrybe_oauth_scopes.split() if s),
                timeout_seconds=settings.descrybe_timeout_seconds,
            )
            self._engine = LegalEngine(self._access_token_provider, config=config)
        return self._engine

    # ------------------------------------------------------------------
    # Public research API
    # ------------------------------------------------------------------
    async def research(
        self,
        *,
        query_type: str,
        query_text: str,
        client_id: UUID,
        initiated_by: UUID,
        matter_id: UUID | None = None,
        function_id: UUID | None = None,
        jurisdiction: str | None = None,
        practice_area: str | None = None,
        extra_filters: dict | None = None,
        limit: int = 10,
        use_cache: bool = True,
    ) -> ResearchResponse:
        """
        Run a Descrybe research query, with caching and audit trail.

        query_type: concept_search | text_search | law_search | citation_lookup
        """
        start = time.monotonic()
        filters = extra_filters or {}

        # 1. Create the audit + query record first
        audit_entry = self.audit.record(
            client_id=client_id,
            function_id=function_id,
            matter_id=matter_id,
            event_type="function_invocation",
            event_summary=f"Descrybe {query_type}: {query_text[:120]}",
            initiated_by=initiated_by,
            model_used="descrybe-legal-engine",
            prompt_raw=json.dumps({
                "query_type": query_type,
                "query_text": query_text,
                "jurisdiction": jurisdiction,
                "practice_area": practice_area,
                "limit": limit,
                "filters": filters,
            }, indent=2),
        )
        audit_id = UUID(audit_entry["id"]) if audit_entry else None

        query_row = self._create_query_record(
            client_id=client_id,
            matter_id=matter_id,
            function_id=function_id,
            audit_trail_id=audit_id,
            query_type=query_type,
            query_text=query_text,
            jurisdiction=jurisdiction,
            practice_area=practice_area,
            extra_filters=filters,
            initiated_by=initiated_by,
        )
        query_id = UUID(query_row["id"])

        # 2. Check cache
        if use_cache:
            cached_results = self._check_cache(
                query_type=query_type,
                query_text=query_text,
                jurisdiction=jurisdiction,
                practice_area=practice_area,
                filters=filters,
            )
            if cached_results:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                self._attach_cached_results(query_id, cached_results)
                return ResearchResponse(
                    query_id=query_id,
                    query_type=query_type,
                    query_text=query_text,
                    cached=True,
                    results=cached_results,
                    processing_time_ms=elapsed_ms,
                    cost_usd=0.0,
                )

        # 3. Call Descrybe
        try:
            raw_data, results = await self._call_descrybe(
                query_type=query_type,
                query_text=query_text,
                jurisdiction=jurisdiction,
                practice_area=practice_area,
                filters=filters,
                limit=limit,
            )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            self._update_query_metadata(query_id, 0, elapsed_ms, 0.0, cached=False)
            return ResearchResponse(
                query_id=query_id,
                query_type=query_type,
                query_text=query_text,
                cached=False,
                results=[],
                processing_time_ms=elapsed_ms,
                error=str(exc),
            )

        elapsed_ms = int((time.monotonic() - start) * 1000)
        cost_usd = 0.0

        # 4. Store results
        self._store_results(query_id, results)
        self._update_query_metadata(query_id, len(results), elapsed_ms, cost_usd, cached=False)

        # 5. Update audit with response
        if audit_id:
            self.audit.record(
                client_id=client_id,
                function_id=function_id,
                matter_id=matter_id,
                event_type="evaluator_reasoning",
                event_summary=f"Descrybe returned {len(results)} results",
                initiated_by=initiated_by,
                model_used="descrybe-legal-engine",
                response_raw=json.dumps(raw_data, default=str)[:100000],
                processing_time_ms=elapsed_ms,
                cost_usd=cost_usd,
                correlation_id=audit_id,
            )

        return ResearchResponse(
            query_id=query_id,
            query_type=query_type,
            query_text=query_text,
            cached=False,
            results=results,
            processing_time_ms=elapsed_ms,
            cost_usd=cost_usd,
            raw_response=raw_data,
        )

    async def verify_citation(
        self,
        *,
        citation: str,
        quote: str | None = None,
        client_id: UUID,
        initiated_by: UUID,
        matter_id: UUID | None = None,
        function_id: UUID | None = None,
    ) -> ResearchResponse:
        """Resolve a citation (and optional quote) against Descrybe's corpus."""
        return await self.research(
            query_type="citation_lookup",
            query_text=citation,
            client_id=client_id,
            initiated_by=initiated_by,
            matter_id=matter_id,
            function_id=function_id,
            extra_filters={"quote": quote} if quote else {},
            limit=5,
        )

    # ------------------------------------------------------------------
    # Case-level tools (citation intelligence suite)
    # ------------------------------------------------------------------
    async def call_case_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call any Descrybe case-level tool and unwrap the MCP result."""
        raw = await asyncio.to_thread(self._get_engine().call_tool, tool_name, arguments)
        return self._unwrap_tool_result(raw)

    async def get_case_by_id(self, case_id: str) -> dict:
        return await self.call_case_tool(TOOL_CASE_DETAILS, {"case_id": case_id})

    async def get_case_summary(self, case_id: str, simplified: bool = False) -> dict:
        args = {"case_id": case_id}
        if simplified:
            args["simplified"] = True
        return await self.call_case_tool(TOOL_CASE_SUMMARY, args)

    async def get_case_passages(self, case_id: str, focus: str) -> dict:
        return await self.call_case_tool(TOOL_CASE_PASSAGES, {"case_id": case_id, "focus": focus})

    async def check_case_status(self, case_id: str) -> dict:
        return await self.call_case_tool(TOOL_CASE_STATUS, {"case_id": case_id})

    async def find_cases_that_cite(self, case_id: str) -> dict:
        return await self.call_case_tool(TOOL_CITING, {"case_id": case_id})

    async def verify_quote(self, case_id: str, quote: str) -> dict:
        return await self.call_case_tool(TOOL_VERIFY_QUOTE, {"case_id": case_id, "quote": quote})

    async def search_case_text(self, term: str, jurisdiction: str = "all") -> dict:
        """Full-text search the case corpus for an exact phrase (any case)."""
        return await self.call_case_tool(TOOL_SEARCH_TEXT, {"term": term, "jurisdiction": jurisdiction})

    async def extract_references(self, text: str, resolve: bool = False) -> dict:
        return await self.call_case_tool(TOOL_EXTRACT_REFS, {"text": text, "resolve": resolve})

    async def get_case_pdf(self, case_id: str) -> dict:
        return await self.call_case_tool(TOOL_CASE_PDF, {"case_id": case_id})

    # ------------------------------------------------------------------
    # Descrybe call routing + normalization
    # ------------------------------------------------------------------
    def _build_tool_call(
        self,
        query_type: str,
        query_text: str,
        jurisdiction: str | None,
        practice_area: str | None,
        filters: dict,
    ) -> tuple[str, dict]:
        jur = jurisdiction or "all"

        if query_type == "concept_search":
            args = {"term": query_text, "jurisdiction": jur}
            if filters.get("search_focus"):
                args["search_focus"] = filters["search_focus"]
            if filters.get("sort"):
                args["sort"] = filters["sort"]
            return TOOL_SEARCH_CONCEPT, args

        if query_type == "text_search":
            return TOOL_SEARCH_TEXT, {"term": query_text, "jurisdiction": jur}

        if query_type == "law_search":
            args = {"term": query_text, "jurisdiction": jur}
            if filters.get("doc_type"):
                args["doc_type"] = filters["doc_type"]
            return TOOL_SEARCH_LAWS, args

        if query_type == "citation_lookup":
            args = {"reference": query_text}
            if jurisdiction:
                args["jurisdiction"] = jurisdiction
            if filters.get("quote"):
                args["context_text"] = filters["quote"]
            return TOOL_RESOLVE, args

        raise ValueError(f"Unsupported query_type: {query_type}")

    async def _call_descrybe(
        self,
        *,
        query_type: str,
        query_text: str,
        jurisdiction: str | None,
        practice_area: str | None,
        filters: dict,
        limit: int,
    ) -> tuple[dict, list[ResearchResult]]:
        """Route to the correct Descrybe tool and normalize results."""
        tool_name, arguments = self._build_tool_call(
            query_type, query_text, jurisdiction, practice_area, filters
        )

        raw = await asyncio.to_thread(self._get_engine().call_tool, tool_name, arguments)
        data = self._unwrap_tool_result(raw)

        if query_type == "law_search":
            results = self._normalize_law_search(data)
        else:
            results = self._normalize_case_search(data)

        return data, results[:limit]

    @staticmethod
    def _unwrap_tool_result(raw: Any) -> dict:
        """
        Extract the structured tool payload from the SDK's MCP response.

        Descrybe's MCP server returns the real data in
        ``result.structuredContent.data`` (matching each tool's outputSchema);
        ``result.content[].text`` is only a human-readable rendering of it.
        Prefer ``structuredContent``, then fall back to parsing text content.
        """
        if not isinstance(raw, dict):
            return {"results": []}

        result = raw.get("result") if isinstance(raw.get("result"), dict) else None

        if result is not None:
            structured = result.get("structuredContent")
            if isinstance(structured, dict):
                data = structured.get("data")
                return data if isinstance(data, dict) else structured

            # Fallback: servers that only return a text content block
            content = result.get("content")
            if isinstance(content, list):
                texts = [
                    c.get("text", "")
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                ]
                if texts:
                    joined = "\n".join(texts).strip()
                    try:
                        parsed = json.loads(joined)
                        if isinstance(parsed, dict):
                            return parsed
                    except Exception:
                        pass
            if "results" in result or "status" in result:
                return result

        # Harness-style wrapper passed directly: {"data": {...}}
        data = raw.get("data")
        if isinstance(data, dict):
            return data

        return raw if isinstance(raw, dict) else {"results": []}

    def _normalize_case_search(self, data: dict) -> list[ResearchResult]:
        """Normalize Descrybe case-search results into ResearchResult."""
        results = []
        for item in data.get("results", []):
            if not isinstance(item, dict):
                continue

            treatment = item.get("treatment") or {}
            indicator = treatment.get("indicator")
            category = treatment.get("category")

            is_good_law: bool | None = None
            if indicator == "positive" or category == "followed":
                is_good_law = True
            elif indicator == "negative" or category == "overruled":
                is_good_law = False

            decision_date = item.get("decision_date")
            year = None
            if isinstance(decision_date, str) and decision_date[:4].isdigit():
                year = int(decision_date[:4])

            rv = item.get("research_value") or {}

            results.append(ResearchResult(
                source="descrybe",
                source_id=item.get("case_id"),
                case_id=item.get("case_id"),
                title=item.get("title") or "Unknown",
                citation=item.get("citation"),
                jurisdiction=item.get("state") or item.get("court"),
                court=item.get("court"),
                decision_year=year,
                source_url=item.get("url"),
                snippet=item.get("body"),
                summary=item.get("why_relevant"),
                relevance_score=item.get("score"),
                treatment=indicator,
                treatment_category=category,
                is_good_law=is_good_law,
                authority_label=rv.get("label"),
                why_relevant=item.get("why_relevant"),
                raw=item,
            ))
        return results

    def _normalize_law_search(self, data: dict) -> list[ResearchResult]:
        """Normalize Descrybe laws/rules search results."""
        results = []
        for item in data.get("results", []):
            if not isinstance(item, dict):
                continue
            results.append(ResearchResult(
                source="descrybe",
                source_id=item.get("id") or item.get("citation"),
                title=item.get("title") or "Unknown",
                citation=item.get("citation"),
                jurisdiction=item.get("jurisdiction"),
                snippet=item.get("matched_passage") or item.get("summary"),
                summary=item.get("summary"),
                relevance_score=item.get("score"),
                raw=item,
            ))
        return results

    # ------------------------------------------------------------------
    # Caching + persistence
    # ------------------------------------------------------------------
    def _cache_key(
        self,
        query_type: str,
        query_text: str,
        jurisdiction: str | None,
        practice_area: str | None,
        filters: dict,
    ) -> str:
        payload = {
            "query_type": query_type,
            "query_text": query_text.strip().lower(),
            "jurisdiction": jurisdiction,
            "practice_area": practice_area,
            "filters": filters,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def _check_cache(
        self,
        query_type: str,
        query_text: str,
        jurisdiction: str | None,
        practice_area: str | None,
        filters: dict,
    ) -> list[ResearchResult]:
        cache_key = self._cache_key(query_type, query_text, jurisdiction, practice_area, filters)
        cutoff = (datetime.now(timezone.utc).timestamp() - self.cache_ttl) * 1000

        try:
            result = (
                get_supabase()
                .table("legal_research_queries")
                .select("id")
                .eq("query_type", query_type)
                .eq("query_text", query_text.strip().lower())
                .eq("cached", False)
                .gte("created_at", datetime.fromtimestamp(cutoff / 1000, tz=timezone.utc).isoformat())
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if not result.data:
                return []

            source_query_id = result.data[0]["id"]
            cached = (
                get_supabase()
                .table("legal_research_results")
                .select("*")
                .eq("query_id", source_query_id)
                .execute()
            )
            return [self._row_to_result(r) for r in (cached.data or [])]
        except Exception:
            return []

    def _create_query_record(
        self,
        *,
        client_id: UUID,
        matter_id: UUID | None,
        function_id: UUID | None,
        audit_trail_id: UUID | None,
        query_type: str,
        query_text: str,
        jurisdiction: str | None,
        practice_area: str | None,
        extra_filters: dict,
        initiated_by: UUID,
    ) -> dict:
        row = {
            "client_id": str(client_id),
            "matter_id": str(matter_id) if matter_id else None,
            "function_id": str(function_id) if function_id else None,
            "audit_trail_id": str(audit_trail_id) if audit_trail_id else None,
            "query_type": query_type,
            "query_text": query_text.strip().lower(),
            "jurisdiction": jurisdiction,
            "practice_area": practice_area,
            "extra_filters": extra_filters,
            "results_count": 0,
            "cached": False,
            "initiated_by": str(initiated_by),
        }
        result = get_supabase().table("legal_research_queries").insert(row).execute()
        return result.data[0]

    def _store_results(self, query_id: UUID, results: list[ResearchResult]) -> None:
        if not results:
            return

        rows = []
        for r in results:
            rows.append({
                "query_id": str(query_id),
                "source": r.source,
                "source_id": r.source_id,
                "case_id": r.case_id,
                "title": r.title,
                "citation": r.citation,
                "jurisdiction": r.jurisdiction,
                "decision_year": r.decision_year,
                "source_url": r.source_url,
                "snippet": r.snippet,
                "summary": r.summary,
                "full_text": r.full_text,
                "passages": r.passages,
                "relevance_score": r.relevance_score,
                "treatment": r.treatment,
                "is_good_law": r.is_good_law,
                "raw": r.raw,
            })

        get_supabase().table("legal_research_results").insert(rows).execute()

    def _attach_cached_results(self, query_id: UUID, results: list[ResearchResult]) -> None:
        self._store_results(query_id, results)
        get_supabase().table("legal_research_queries").update({
            "results_count": len(results),
            "cached": True,
        }).eq("id", str(query_id)).execute()

    def _update_query_metadata(
        self,
        query_id: UUID,
        results_count: int,
        processing_time_ms: int,
        cost_usd: float,
        cached: bool,
    ) -> None:
        get_supabase().table("legal_research_queries").update({
            "results_count": results_count,
            "processing_time_ms": processing_time_ms,
            "cost_usd": cost_usd,
            "cached": cached,
        }).eq("id", str(query_id)).execute()

    def _row_to_result(self, row: dict) -> ResearchResult:
        raw = row.get("raw") or {}
        rv = raw.get("research_value") or {}
        treatment = raw.get("treatment") or {}
        return ResearchResult(
            source=row.get("source", "descrybe"),
            source_id=row.get("source_id"),
            case_id=row.get("case_id"),
            title=row.get("title", ""),
            citation=row.get("citation"),
            jurisdiction=row.get("jurisdiction"),
            court=row.get("court") or raw.get("court"),
            decision_year=row.get("decision_year"),
            source_url=row.get("source_url"),
            snippet=row.get("snippet"),
            summary=row.get("summary"),
            full_text=row.get("full_text"),
            passages=row.get("passages") or [],
            relevance_score=row.get("relevance_score"),
            treatment=row.get("treatment") or treatment.get("indicator"),
            treatment_category=treatment.get("category"),
            is_good_law=row.get("is_good_law"),
            authority_label=rv.get("label"),
            why_relevant=raw.get("why_relevant"),
            raw=raw,
        )

    # ------------------------------------------------------------------
    # Function registry
    # ------------------------------------------------------------------
    def get_function_id(self) -> UUID | None:
        """Resolve the legal-research function UUID from the registry."""
        try:
            result = (
                get_supabase()
                .table("functions")
                .select("id")
                .eq("slug", "legal-research")
                .execute()
            )
            if result.data:
                return UUID(result.data[0]["id"])
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Module-level helper (no-auth factory — for tests / internal use only)
# ---------------------------------------------------------------------------
def get_descrybe_client() -> DescrybeClient:
    """Factory for the Descrybe client (no user token — callers must inject one)."""
    return DescrybeClient()
