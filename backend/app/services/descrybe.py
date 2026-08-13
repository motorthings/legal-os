"""
Legal AI OS — Descrybe Legal Research Service

Shared async client for Descrybe's legal research API.
Every call is cached in Postgres and audited.

NOTE: Endpoint paths below assume a standard Descrybe REST API layout.
If your account uses different paths, override via DESCRYBE_BASE_URL
and update the endpoint constants before first use.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.database import get_supabase
from app.services.audit import AuditTrail


# ---------------------------------------------------------------------------
# Endpoint constants — adjust if Descrybe's API uses different paths
# ---------------------------------------------------------------------------
ENDPOINTS = {
    "search_cases_by_concept": "/v1/cases/search/concept",
    "search_case_text": "/v1/cases/search/text",
    "search_laws_and_rules": "/v1/laws/search",
    "find_case_from_reference": "/v1/cases/resolve",
    "get_case_details": "/v1/cases/{case_id}/details",
    "get_case_summary": "/v1/cases/{case_id}/summary",
    "get_case_passages": "/v1/cases/{case_id}/passages",
    "check_case_status": "/v1/cases/{case_id}/status",
    "find_cases_that_cite": "/v1/cases/{case_id}/citing",
    "verify_quote": "/v1/quotes/verify",
    "extract_case_references": "/v1/references/extract",
}


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
    decision_year: int | None = None
    source_url: str | None = None
    snippet: str | None = None
    summary: str | None = None
    full_text: str | None = None
    passages: list[dict] = field(default_factory=list)
    relevance_score: float | None = None
    treatment: str | None = None
    is_good_law: bool | None = None
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


class DescrybeClient:
    """
    Async Descrybe API client with caching, retries, and audit trail capture.

    Usage:
        client = DescrybeClient()
        response = await client.research(
            query_type="concept_search",
            query_text="workplace discrimination retaliation",
            jurisdiction="US",
            practice_area="employment",
            client_id=...,
            matter_id=...,
            initiated_by=...,
        )
    """

    def __init__(self):
        if not settings.descrybe_api_key:
            raise RuntimeError("DESCRYBE_API_KEY is not configured")

        self.base_url = settings.descrybe_base_url.rstrip("/")
        self.timeout = settings.descrybe_timeout_seconds
        self.cache_ttl = settings.descrybe_cache_ttl_seconds
        self.audit = AuditTrail()
        self._headers = {
            "Authorization": f"Bearer {settings.descrybe_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ------------------------------------------------------------------
    # Public API
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
        Run a legal research query, with caching and audit trail.

        query_type: concept_search | text_search | citation_lookup | law_search
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
            model_used="descrybe-api",
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
        cached_results: list[ResearchResult] = []
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
        raw_response, results = await self._call_descrybe(
            query_type=query_type,
            query_text=query_text,
            jurisdiction=jurisdiction,
            practice_area=practice_area,
            filters=filters,
            limit=limit,
        )

        elapsed_ms = int((time.monotonic() - start) * 1000)
        cost_usd = raw_response.get("cost_usd", 0.0) if isinstance(raw_response, dict) else 0.0

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
                model_used="descrybe-api",
                response_raw=json.dumps(raw_response, default=str)[:100000],
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
            raw_response=raw_response,
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
        """Verify a citation (and optional quote) against Descrybe's corpus."""
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

    async def get_case_by_id(self, case_id: str) -> dict:
        """Fetch full case details by Descrybe case_id."""
        url = self._url("get_case_details", case_id=case_id)
        return await self._get(url)

    # ------------------------------------------------------------------
    # Core HTTP helpers
    # ------------------------------------------------------------------
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _post(self, endpoint: str, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers) as client:
            response = await client.post(self.base_url + endpoint, json=payload)
            response.raise_for_status()
            return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _get(self, url: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    def _url(self, endpoint_key: str, **path_params) -> str:
        path = ENDPOINTS[endpoint_key].format(**path_params)
        return f"{self.base_url}{path}"

    # ------------------------------------------------------------------
    # Descrybe call routing + normalization
    # ------------------------------------------------------------------
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
        """Route to the correct Descrybe endpoint and normalize results."""

        if query_type == "concept_search":
            payload = {
                "term": query_text,
                "jurisdiction": jurisdiction or "all",
                "search_focus": filters.get("search_focus", "general"),
                "sort": filters.get("sort", "authority"),
            }
            raw = await self._post(ENDPOINTS["search_cases_by_concept"], payload)
            results = self._normalize_case_search(raw)

        elif query_type == "text_search":
            payload = {
                "term": query_text,
                "jurisdiction": jurisdiction or "all",
            }
            raw = await self._post(ENDPOINTS["search_case_text"], payload)
            results = self._normalize_case_search(raw)

        elif query_type == "law_search":
            payload = {
                "term": query_text,
                "jurisdiction": jurisdiction or "all",
                "doc_type": filters.get("doc_type", "all"),
            }
            raw = await self._post(ENDPOINTS["search_laws_and_rules"], payload)
            results = self._normalize_law_search(raw)

        elif query_type == "citation_lookup":
            payload = {
                "reference": query_text,
                "jurisdiction": jurisdiction or "all",
                "context_text": filters.get("quote"),
            }
            raw = await self._post(ENDPOINTS["find_case_from_reference"], payload)
            results = self._normalize_case_search(raw)

        else:
            raise ValueError(f"Unsupported query_type: {query_type}")

        # Trim to limit
        return raw, results[:limit]

    def _normalize_case_search(self, raw: dict) -> list[ResearchResult]:
        """Normalize Descrybe case search results."""
        results = []
        for item in raw.get("results", raw.get("cases", [])):
            if not isinstance(item, dict):
                continue
            results.append(ResearchResult(
                source="descrybe",
                source_id=item.get("case_id"),
                case_id=item.get("case_id"),
                title=item.get("case_name") or item.get("title") or "Unknown",
                citation=item.get("citation"),
                jurisdiction=item.get("jurisdiction"),
                decision_year=item.get("year"),
                source_url=item.get("url"),
                snippet=item.get("summary") or item.get("snippet"),
                summary=item.get("summary"),
                relevance_score=item.get("score"),
                treatment=item.get("treatment"),
                raw=item,
            ))
        return results

    def _normalize_law_search(self, raw: dict) -> list[ResearchResult]:
        """Normalize Descrybe laws/rules search results."""
        results = []
        for item in raw.get("results", []):
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
        """Deterministic cache key for a query."""
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
        """Return cached results if a recent identical query exists."""
        cache_key = self._cache_key(query_type, query_text, jurisdiction, practice_area, filters)
        cutoff = (datetime.now(timezone.utc).timestamp() - self.cache_ttl) * 1000

        try:
            result = (
                get_supabase()
                .table("legal_research_queries")
                .select("id")
                .eq("query_type", query_type)
                .eq("query_text", query_text.strip().lower())
                .eq("cached", False)  # only use real API results as cache source
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
        """Copy cached results to the new query record."""
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
        return ResearchResult(
            source=row.get("source", "descrybe"),
            source_id=row.get("source_id"),
            case_id=row.get("case_id"),
            title=row.get("title", ""),
            citation=row.get("citation"),
            jurisdiction=row.get("jurisdiction"),
            decision_year=row.get("decision_year"),
            source_url=row.get("source_url"),
            snippet=row.get("snippet"),
            summary=row.get("summary"),
            full_text=row.get("full_text"),
            passages=row.get("passages") or [],
            relevance_score=row.get("relevance_score"),
            treatment=row.get("treatment"),
            is_good_law=row.get("is_good_law"),
            raw=row.get("raw") or {},
        )

    # ------------------------------------------------------------------
    # Convenience sync helpers for background tasks / Celery
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
# Module-level helper
# ---------------------------------------------------------------------------
def get_descrybe_client() -> DescrybeClient:
    """Factory for the Descrybe client."""
    return DescrybeClient()
