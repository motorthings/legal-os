"""
Legal AI OS — Maturity Assessment Service

Orchestrates the maturity assessment pipeline:
1. Fetch documents from knowledge_documents
2. If total text > 100K chars, chunk and summarize via LLM (two-pass)
3. Call LegalMaturityAgent with all document context
4. Parse and store result
5. Record audit trail + metrics

Deterministic fallback: _synthesize_maturity() when LLM output is malformed.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.agents.legal_maturity_agent import (
    LegalMaturityAgent,
    DIMENSION_DEFINITIONS,
    DIMENSION_KEYS,
    LEVEL_LABELS,
)
from app.database import get_supabase
from app.llm import LLMProvider


# ---------------------------------------------------------------------------
# Keyword heuristics for deterministic fallback
# ---------------------------------------------------------------------------

# Keywords that suggest maturity in each dimension
DIMENSION_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "knowledge_management": {
        "high": [
            "knowledge management", "km system", "precedent database",
            "knowledge base", "dms", "document management system",
            "searchable", "tagged", "taxonomy", "metadata",
            "institutional knowledge", "know-how", "template library",
            "imanage", "netdocuments", "sharepoint", "notion",
        ],
        "medium": [
            "shared drive", "templates", "playbook", "style guide",
            "research memo", "prior work product", "brief bank",
        ],
    },
    "workflow_process": {
        "high": [
            "workflow", "process map", "standard operating procedure",
            "sop", "intake process", "conflict check process",
            "matter lifecycle", "stage gate", "kanban", "lean",
            "six sigma", "cycle time", "throughput", "bottleneck",
            "allocation", "staffing process", "closing process",
        ],
        "medium": [
            "checklist", "intake form", "conflict check", "opening procedure",
            "closing letter", "assignment", "delegation of authority",
        ],
    },
    "governance_risk": {
        "high": [
            "ai governance", "ai policy", "acceptable use policy",
            "ethical wall", "conflict waiver", "engagement letter",
            "approval authority", "delegation authority",
            "risk committee", "compliance committee", "audit trail",
            "human in the loop", "model card", "bias review",
            "confidentiality", "privilege", "data protection",
        ],
        "medium": [
            "governance", "policy", "approval", "sign-off",
            "ethics", "compliance", "risk management", "bar rules",
        ],
    },
    "team_capability": {
        "high": [
            "ai training", "ai literacy", "ai competency",
            "prompt engineering", "ai workshop", "ai champion",
            "lunch and learn", "cle", "continuing education",
            "ai adoption", "change management", "digital literacy",
            "ai roadmap", "innovation", "ai strategy",
        ],
        "medium": [
            "training", "workshop", "webinar", "pilot program",
            "early adopter", "experiment", "trial",
        ],
    },
    "technology_data": {
        "high": [
            "api", "integration", "clio", "practice management",
            "billing system", "time tracking", "crm", "data warehouse",
            "data lake", "structured data", "data quality",
            "single source of truth", "cloud", "saas",
            "interoperability", "data migration", "clean data",
        ],
        "medium": [
            "practice management", "billing", "accounting",
            "document management", "email", "calendar",
            "spreadsheet", "excel", "database",
        ],
    },
}


def _keyword_score(text: str, keywords: dict[str, list[str]]) -> int:
    """Score a dimension 1-5 based on keyword matches in document text."""
    text_lower = text.lower()
    high_hits = sum(
        1 for kw in keywords["high"] if kw.lower() in text_lower
    )
    medium_hits = sum(
        1 for kw in keywords["medium"] if kw.lower() in text_lower
    )

    # Heuristic scoring
    if high_hits >= 4:
        return 4
    elif high_hits >= 2 or (high_hits >= 1 and medium_hits >= 3):
        return 3
    elif medium_hits >= 2 or high_hits >= 1:
        return 2
    else:
        return 1


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class MaturityService:
    """
    Orchestrates AI maturity assessment from document upload to stored result.

    Usage:
        service = MaturityService()
        assessment = await service.run_assessment(
            client_id=UUID("..."),
            user_id=UUID("..."),
            document_ids=[UUID("..."), UUID("...")],
        )
    """

    # Maximum characters to send to the LLM in one pass
    MAX_CONTEXT_CHARS = 100_000
    # Characters per chunk for summarization pass
    CHUNK_SIZE = 30_000

    async def run_assessment(
        self,
        client_id: UUID,
        user_id: UUID,
        document_ids: list[UUID],
    ) -> dict:
        """
        Run a full maturity assessment against the given documents.

        Returns the stored assessment row.
        """
        supabase = get_supabase()

        # 1. Fetch document texts
        docs = await self._fetch_documents(document_ids, str(client_id))
        if not docs:
            raise ValueError("No documents found for the given IDs")

        texts = [d["raw_text"] for d in docs if d.get("raw_text")]
        if not texts:
            raise ValueError("All documents have empty content")

        total_chars = sum(len(t) for t in texts)

        # 2. If too large, summarize first (two-pass)
        if total_chars > self.MAX_CONTEXT_CHARS:
            texts = await self._summarize_documents(texts)

        # 3. Run agent
        agent = LegalMaturityAgent()
        result = await agent.assess(texts)

        # 4. Store assessment
        assessment_id = uuid4()
        dimensions = result.get("dimensions", [])

        row = {
            "id": str(assessment_id),
            "client_id": str(client_id),
            "version": 1,
            "overall_level": result["overall_level"],
            "overall_level_label": result["overall_level_label"],
            "bottleneck_dimension": result["bottleneck_dimension"],
            "bottleneck_why": result["bottleneck_why"],
            "bottleneck_what_this_means": result["bottleneck_what_this_means"],
            "dimensions": json.dumps(dimensions),
            "stage_gaps": json.dumps(result.get("stage_gaps", [])),
            "summary": result["summary"],
            "document_count": len(document_ids),
            "document_ids": [str(did) for did in document_ids],
            "cost_usd": result.get("_llm_cost_usd", 0),
            "created_by": str(user_id),
        }

        stored = supabase.table("maturity_assessments").insert(row).execute()
        if not stored.data:
            raise RuntimeError("Failed to store maturity assessment")

        # 5. Link documents back to this assessment
        for did in document_ids:
            supabase.table("knowledge_documents").update(
                {"maturity_assessment_id": str(assessment_id)}
            ).eq("id", str(did)).eq("client_id", str(client_id)).execute()

        return stored.data[0]

    async def get_assessments(
        self, client_id: UUID, limit: int = 20
    ) -> list[dict]:
        """List past assessments for a client."""
        result = (
            get_supabase()
            .table("maturity_assessments")
            .select(
                "id, version, overall_level, overall_level_label, "
                "bottleneck_dimension, document_count, cost_usd, created_at"
            )
            .eq("client_id", str(client_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    async def get_assessment(
        self, assessment_id: UUID, client_id: UUID
    ) -> dict | None:
        """Get a single assessment with full detail."""
        result = (
            get_supabase()
            .table("maturity_assessments")
            .select("*")
            .eq("id", str(assessment_id))
            .eq("client_id", str(client_id))
            .execute()
        )
        if not result.data:
            return None

        data = result.data[0]
        # Parse JSONB fields
        if isinstance(data.get("dimensions"), str):
            data["dimensions"] = json.loads(data["dimensions"])
        if isinstance(data.get("stage_gaps"), str):
            data["stage_gaps"] = json.loads(data["stage_gaps"])
        return data

    # ------------------------------------------------------------------
    # Document helpers
    # ------------------------------------------------------------------

    async def _fetch_documents(
        self, document_ids: list[UUID], client_id: str
    ) -> list[dict]:
        """Fetch document texts from knowledge_documents."""
        supabase = get_supabase()
        docs = []
        for did in document_ids:
            result = (
                supabase.table("knowledge_documents")
                .select("id, title, raw_text, document_type, source_file")
                .eq("id", str(did))
                .eq("client_id", client_id)
                .eq("is_active", True)
                .execute()
            )
            if result.data:
                docs.extend(result.data)
        return docs

    async def _summarize_documents(self, texts: list[str]) -> list[str]:
        """
        Two-pass approach: chunk large documents, summarize each chunk
        with an LLM, then return the summaries as the analysis context.
        """
        # Combine all texts, chunk, and summarize each chunk
        combined = "\n\n---\n\n".join(texts)
        chunks = self._chunk_text(combined, self.CHUNK_SIZE)

        if len(chunks) <= 1:
            return texts

        llm = LLMProvider(function_slug="maturity-assessment")
        summaries = []

        async def summarize_chunk(chunk: str, idx: int) -> str:
            response = await llm.call(
                system_prompt=(
                    "You are summarizing legal operational documents for an AI "
                    "maturity assessment. Extract: what systems/tools are mentioned, "
                    "what processes are documented, what governance structures exist, "
                    "what training or AI initiatives are described, and what gaps or "
                    "pain points are visible. Be terse and factual. No commentary."
                ),
                user_message=(
                    f"Summarize this document excerpt for AI maturity assessment. "
                    f"Focus on systems, processes, governance, people, and data:\n\n{chunk}"
                ),
                temperature=0.1,
                max_tokens=1024,
            )
            return f"[Document Summary {idx + 1}]\n{response.text}"

        # Run summaries concurrently
        tasks = [summarize_chunk(chunk, i) for i, chunk in enumerate(chunks)]
        summaries = await asyncio.gather(*tasks)
        return list(summaries)

    @staticmethod
    def _chunk_text(text: str, chunk_size: int) -> list[str]:
        """Split text into roughly equal chunks at paragraph boundaries."""
        paragraphs = text.split("\n\n")
        chunks = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) > chunk_size and current:
                chunks.append(current.strip())
                current = para
            else:
                if current:
                    current += "\n\n" + para
                else:
                    current = para
        if current.strip():
            chunks.append(current.strip())
        return chunks or [text]

    # ------------------------------------------------------------------
    # Deterministic fallback
    # ------------------------------------------------------------------

    @staticmethod
    def synthesize_maturity(document_texts: list[str]) -> dict:
        """
        Deterministic fallback when the LLM output is unparseable.
        Uses keyword heuristics to score each dimension.
        """
        combined = " ".join(document_texts)

        dimensions = []
        scores = []
        for key in DIMENSION_KEYS:
            score = _keyword_score(combined, DIMENSION_KEYWORDS.get(key, {"high": [], "medium": []}))
            dimensions.append({
                "key": key,
                "name": DIMENSION_DEFINITIONS[key]["name"],
                "score": score,
                "rationale": "Keyword-based heuristic (LLM output was unparseable).",
            })
            scores.append(score)

        overall = min(scores)
        bottleneck_idx = scores.index(overall)
        bottleneck_key = DIMENSION_KEYS[bottleneck_idx]
        bottleneck_name = DIMENSION_DEFINITIONS[bottleneck_key]["name"]

        stage_gaps = []
        for i in range(4):
            from_level = i + 1
            to_level = i + 2
            if from_level < overall:
                whats_missing = "Already achieved."
                what_it_unlocks = "Already unlocked."
            else:
                whats_missing = (
                    f"Need stronger evidence in {bottleneck_name} and other "
                    f"dimensions to confirm Level {to_level}."
                )
                what_it_unlocks = (
                    f"Progress to {LEVEL_LABELS.get(to_level, f'Level {to_level}')}."
                )
            stage_gaps.append({
                "from_level": from_level,
                "to_level": to_level,
                "from_label": LEVEL_LABELS.get(from_level, ""),
                "to_label": LEVEL_LABELS.get(to_level, ""),
                "whats_missing": whats_missing,
                "what_it_unlocks": what_it_unlocks,
            })

        return {
            "overall_level": overall,
            "overall_level_label": LEVEL_LABELS.get(overall, "AI Aware"),
            "bottleneck_dimension": bottleneck_key,
            "bottleneck_why": (
                f"{bottleneck_name} scored {overall}/5 based on keyword analysis "
                f"of uploaded documents. This dimension has the least evidence of maturity."
            ),
            "bottleneck_what_this_means": (
                f"The firm is held at {LEVEL_LABELS.get(overall, f'Level {overall}')} "
                f"because {bottleneck_name.lower()} shows the least maturity. "
                f"Address this dimension to advance."
            ),
            "summary": (
                f"Deterministic assessment (LLM fallback). Overall level: "
                f"{LEVEL_LABELS.get(overall, f'Level {overall}')}. "
                f"Bottleneck: {bottleneck_name} ({overall}/5). "
                f"Upload more detailed operational documents for a richer assessment."
            ),
            "dimensions": dimensions,
            "stage_gaps": stage_gaps,
            "_llm_model": "deterministic-fallback",
            "_llm_provider": "none",
            "_llm_cost_usd": 0.0,
            "_llm_tokens": 0,
        }
