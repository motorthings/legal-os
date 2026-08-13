"""
Legal AI OS — Legal Research & Citation Intelligence API

Descrybe-powered research integrated with matters, KM, and governance.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, User
from app.config import settings
from app.database import get_supabase
from app.services.descrybe import DescrybeClient, ResearchResponse, get_descrybe_client

router = APIRouter()


# ---------------------------------------------------------------------------
# Governance contract
# ---------------------------------------------------------------------------
@router.get("/health")
async def legal_research_health():
    healthy = bool(settings.descrybe_api_key)
    return {
        "function": "legal-research",
        "status": "healthy" if healthy else "degraded",
        "version": "0.1.0",
        "descrybe_configured": healthy,
        "capabilities": [
            "concept_search",
            "text_search",
            "law_search",
            "citation_lookup",
            "quote_verification",
            "case_status_check",
            "matter_enrichment",
        ],
    }


@router.get("/metrics")
async def legal_research_metrics():
    supabase = get_supabase()
    queries = supabase.table("legal_research_queries").select("id", count="exact").execute()
    cached = (
        supabase.table("legal_research_queries")
        .select("id", count="exact")
        .eq("cached", True)
        .execute()
    )
    results = supabase.table("legal_research_results").select("id", count="exact").execute()

    return {
        "function": "legal-research",
        "total_queries": queries.count if hasattr(queries, "count") else 0,
        "cached_queries": cached.count if hasattr(cached, "count") else 0,
        "total_results": results.count if hasattr(results, "count") else 0,
    }


@router.get("/targets")
async def legal_research_targets():
    return {
        "function": "legal-research",
        "targets": {
            "query_latency_ms": "< 5000",
            "cache_hit_rate": "> 0.30",
            "citation_verification_precision": "> 0.95",
            "results_per_query": "5-10",
            "audit_coverage": "1.0",
        },
    }


# ---------------------------------------------------------------------------
# Research endpoints
# ---------------------------------------------------------------------------
@router.post("/research")
async def research(
    data: dict,
    user: User = Depends(get_current_user),
    client: DescrybeClient = Depends(get_descrybe_client),
) -> ResearchResponse:
    """
    Run a Descrybe legal research query.

    Body:
        query_type: concept_search | text_search | law_search | citation_lookup
        query_text: the search term or citation
        matter_id: optional matter to associate
        jurisdiction: optional jurisdiction filter
        practice_area: optional practice area
        extra_filters: optional provider-specific filters
        limit: max results (default 10)
        use_cache: whether to use cached results (default true)
    """
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    query_type = data.get("query_type")
    query_text = data.get("query_text")

    if not query_type or not query_text:
        raise HTTPException(status_code=400, detail="query_type and query_text are required")

    function_id = client.get_function_id()

    try:
        return await client.research(
            query_type=query_type,
            query_text=query_text,
            client_id=user.client_id,
            initiated_by=user.id,
            matter_id=data.get("matter_id"),
            function_id=function_id,
            jurisdiction=data.get("jurisdiction"),
            practice_area=data.get("practice_area"),
            extra_filters=data.get("extra_filters", {}),
            limit=data.get("limit", 10),
            use_cache=data.get("use_cache", True),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")


@router.post("/verify-citation")
async def verify_citation(
    data: dict,
    user: User = Depends(get_current_user),
    client: DescrybeClient = Depends(get_descrybe_client),
):
    """
    Verify a citation and optional quoted language.

    Body:
        citation: the citation to verify
        quote: optional exact quote to verify
        matter_id: optional matter association
        jurisdiction: optional jurisdiction
    """
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    citation = data.get("citation")
    if not citation:
        raise HTTPException(status_code=400, detail="citation is required")

    function_id = client.get_function_id()

    try:
        return await client.verify_citation(
            citation=citation,
            quote=data.get("quote"),
            client_id=user.client_id,
            initiated_by=user.id,
            matter_id=data.get("matter_id"),
            function_id=function_id,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Citation verification failed: {str(e)}")


# ---------------------------------------------------------------------------
# Matter-scoped research history
# ---------------------------------------------------------------------------
@router.get("/queries")
async def list_queries(
    user: User = Depends(get_current_user),
    matter_id: UUID | None = None,
    query_type: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    """List research queries for the user's client."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    query = (
        get_supabase()
        .table("legal_research_queries")
        .select("*, matters(name, matter_number)")
        .eq("client_id", str(user.client_id))
        .order("created_at", desc=True)
        .limit(limit)
        .offset(offset)
    )
    if matter_id:
        query = query.eq("matter_id", str(matter_id))
    if query_type:
        query = query.eq("query_type", query_type)

    result = query.execute()
    return result.data or []


@router.get("/queries/{query_id}")
async def get_query(query_id: UUID, user: User = Depends(get_current_user)):
    """Get a single research query with its results."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()
    query = (
        supabase.table("legal_research_queries")
        .select("*")
        .eq("id", str(query_id))
        .eq("client_id", str(user.client_id))
        .execute()
    )
    if not query.data:
        raise HTTPException(status_code=404, detail="Query not found")

    results = (
        supabase.table("legal_research_results")
        .select("*")
        .eq("query_id", str(query_id))
        .execute()
    )

    return {
        **query.data[0],
        "results": results.data or [],
    }


@router.get("/matters/{matter_id}/summary")
async def matter_research_summary(
    matter_id: UUID,
    user: User = Depends(get_current_user),
):
    """Get a research summary for a specific matter."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    result = (
        get_supabase()
        .table("matter_research_summary")
        .select("*")
        .eq("matter_id", str(matter_id))
        .execute()
    )
    if not result.data:
        return {
            "matter_id": str(matter_id),
            "total_queries": 0,
            "total_results": 0,
            "descrybe_results": 0,
            "total_cost_usd": 0,
            "last_research_at": None,
        }
    return result.data[0]


@router.post("/matters/{matter_id}/enrich")
async def enrich_matter_endpoint(
    matter_id: UUID,
    user: User = Depends(get_current_user),
):
    """Auto-run Descrybe research for a matter based on its jurisdiction and practice area."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    from app.services.matter_enrichment import enrich_matter

    return await enrich_matter(
        matter_id=matter_id,
        initiated_by=user.id,
    )


# ---------------------------------------------------------------------------
# Case detail lookup
# ---------------------------------------------------------------------------
@router.get("/cases/{case_id}")
async def get_case_details(
    case_id: str,
    user: User = Depends(get_current_user),
    client: DescrybeClient = Depends(get_descrybe_client),
):
    """Fetch full case details by Descrybe case_id."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    try:
        return await client.get_case_by_id(case_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Case lookup failed: {str(e)}")
