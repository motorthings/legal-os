"""
Legal AI OS — Matter Enrichment Service

Auto-runs Descrybe research when a matter is created or updated,
surfacing relevant case law and statutes before human review.

Callable directly, or from a matter-intake hook / background task.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.database import get_supabase
from app.services.descrybe import DescrybeClient


def _build_queries(matter: dict) -> list[dict]:
    """Build a set of Descrybe queries from matter context."""
    jurisdiction = matter.get("jurisdiction")
    practice_area = matter.get("practice_area") or ""
    name = matter.get("name") or ""
    description = matter.get("description") or ""
    adverse = matter.get("adverse_parties") or []

    queries = []

    # 1. Practice-area + subject concept search
    if practice_area:
        subject = f"{practice_area} {name}".strip()
        queries.append({
            "query_type": "concept_search",
            "query_text": subject,
            "jurisdiction": jurisdiction,
            "practice_area": practice_area,
        })

    # 2. Jurisdiction-specific law/regulations
    if practice_area and jurisdiction:
        queries.append({
            "query_type": "law_search",
            "query_text": practice_area,
            "jurisdiction": jurisdiction,
            "practice_area": practice_area,
        })

    # 3. Adverse-party / case-name lookup (if a party name looks like a case)
    for party in adverse[:3]:
        if party and len(party) > 3:
            queries.append({
                "query_type": "citation_lookup",
                "query_text": party,
                "jurisdiction": jurisdiction,
                "practice_area": practice_area,
            })

    # 4. Description-driven search (fallback when practice_area is sparse)
    if description and not practice_area:
        queries.append({
            "query_type": "concept_search",
            "query_text": description[:200],
            "jurisdiction": jurisdiction,
            "practice_area": practice_area,
        })

    return queries


async def enrich_matter(
    matter_id: UUID,
    initiated_by: UUID | None = None,
    limit: int = 5,
) -> dict:
    """
    Run Descrybe enrichment for a matter. Returns a summary of what was found.

    Graceful: never raises — enrichment is best-effort and non-blocking.
    """
    supabase = get_supabase()

    # Load matter
    matter = (
        supabase.table("matters")
        .select("*")
        .eq("id", str(matter_id))
        .execute()
    )
    if not matter.data:
        return {"error": "Matter not found", "matter_id": str(matter_id)}

    matter = matter.data[0]
    client_id = UUID(matter["client_id"])
    initiated_by = initiated_by or UUID(matter.get("created_by") or matter["client_id"])

    # Build queries
    queries = _build_queries(matter)
    if not queries:
        return {"matter_id": str(matter_id), "queries_run": 0, "results": []}

    # Run enrichment
    try:
        client = DescrybeClient()
        function_id = client.get_function_id()
    except RuntimeError:
        return {"matter_id": str(matter_id), "queries_run": 0, "reason": "descrybe_not_configured"}

    results = []
    for q in queries:
        try:
            response = await client.research(
                query_type=q["query_type"],
                query_text=q["query_text"],
                client_id=client_id,
                initiated_by=initiated_by,
                matter_id=matter_id,
                function_id=function_id,
                jurisdiction=q.get("jurisdiction"),
                practice_area=q.get("practice_area"),
                limit=limit,
            )
            results.append({
                "query_type": q["query_type"],
                "query_text": q["query_text"],
                "cached": response.cached,
                "results_count": len(response.results),
            })
        except Exception as e:
            results.append({
                "query_type": q["query_type"],
                "query_text": q["query_text"],
                "error": str(e),
            })

    return {
        "matter_id": str(matter_id),
        "queries_run": len(results),
        "results": results,
    }


def enrich_matter_sync(matter_id: UUID, initiated_by: UUID | None = None, limit: int = 5) -> dict:
    """Blocking wrapper for background tasks / Celery."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(enrich_matter(matter_id, initiated_by, limit))
    finally:
        loop.close()
