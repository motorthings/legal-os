"""
Legal AI OS — Legal Research & Citation Intelligence API

Descrybe-powered research integrated with matters, KM, and governance.
Access is per-user OAuth; every tool call runs under the connected user's
Descrybe account.
"""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.auth import get_current_user, User
from app.database import get_supabase
from app.services.descrybe import DescrybeClient, ResearchResponse

router = APIRouter()


def get_descrybe_client(user: User = Depends(get_current_user)) -> DescrybeClient:
    """Resolve the Descrybe client for the authenticated user's account."""
    return DescrybeClient(user_id=user.id)


def _require_descrybe(user: User) -> None:
    from app.services.descrybe_oauth import is_connected

    if not is_connected(user.id):
        raise HTTPException(
            status_code=503,
            detail="Descrybe is not connected for this account. Connect Descrybe first.",
        )


# ---------------------------------------------------------------------------
# Governance contract
# ---------------------------------------------------------------------------
@router.get("/health")
async def legal_research_health():
    return {
        "function": "legal-research",
        "status": "healthy",
        "version": "0.2.0",
        "auth_model": "per-user-oauth",
        "capabilities": [
            "concept_search",
            "text_search",
            "law_search",
            "citation_lookup",
            "quote_verification",
            "case_status_check",
            "citing_case_search",
            "case_summary",
            "case_passages",
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
    _require_descrybe(user)

    query_type = data.get("query_type")
    query_text = data.get("query_text")

    if not query_type or not query_text:
        raise HTTPException(status_code=400, detail="query_type and query_text are required")

    function_id = client.get_function_id()

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


@router.post("/verify-citation")
async def verify_citation(
    data: dict,
    user: User = Depends(get_current_user),
    client: DescrybeClient = Depends(get_descrybe_client),
):
    """
    Resolve a citation and optional quoted language against Descrybe's corpus.

    Body:
        citation: the citation to verify
        quote: optional exact quote to verify
        matter_id: optional matter association
        jurisdiction: optional jurisdiction
    """
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")
    _require_descrybe(user)

    citation = data.get("citation")
    if not citation:
        raise HTTPException(status_code=400, detail="citation is required")

    function_id = client.get_function_id()

    return await client.verify_citation(
        citation=citation,
        quote=data.get("quote"),
        client_id=user.client_id,
        initiated_by=user.id,
        matter_id=data.get("matter_id"),
        function_id=function_id,
    )


# ---------------------------------------------------------------------------
# Citation intelligence suite (case-level tools)
# ---------------------------------------------------------------------------
@router.get("/cases/{case_id}")
async def get_case_details(
    case_id: str,
    user: User = Depends(get_current_user),
    client: DescrybeClient = Depends(get_descrybe_client),
):
    """Fetch full case details by Descrybe case_id."""
    _require_descrybe(user)
    try:
        return await client.get_case_by_id(case_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Case lookup failed: {str(e)}")


@router.get("/cases/{case_id}/summary")
async def get_case_summary(
    case_id: str,
    simplified: bool = False,
    user: User = Depends(get_current_user),
    client: DescrybeClient = Depends(get_descrybe_client),
):
    """Fetch a case's precomputed summary."""
    _require_descrybe(user)
    try:
        return await client.get_case_summary(case_id, simplified=simplified)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary failed: {str(e)}")


@router.get("/cases/{case_id}/status")
async def get_case_status(
    case_id: str,
    user: User = Depends(get_current_user),
    client: DescrybeClient = Depends(get_descrybe_client),
):
    """Check a case's treatment / good-law status."""
    _require_descrybe(user)
    try:
        return await client.check_case_status(case_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.get("/cases/{case_id}/citing")
async def get_citing_cases(
    case_id: str,
    user: User = Depends(get_current_user),
    client: DescrybeClient = Depends(get_descrybe_client),
):
    """Find later cases that cite this case."""
    _require_descrybe(user)
    try:
        return await client.find_cases_that_cite(case_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Citing-case search failed: {str(e)}")


@router.post("/verify-quote")
async def verify_quote(
    data: dict,
    user: User = Depends(get_current_user),
    client: DescrybeClient = Depends(get_descrybe_client),
):
    """Verify a quote word-for-word against a known case.

    Body: {case_id, quote}
    """
    _require_descrybe(user)
    case_id = data.get("case_id")
    quote = data.get("quote")
    if not case_id or not quote:
        raise HTTPException(status_code=400, detail="case_id and quote are required")
    try:
        return await client.verify_quote(case_id, quote)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quote verification failed: {str(e)}")


@router.post("/cite-check")
async def cite_check(
    data: dict,
    user: User = Depends(get_current_user),
):
    """
    Validate a brief/filing against Descrybe. Streams a live progress log,
    then a findings report and an annotated copy of the brief (new name).

    Body: {text, name?, deep?}

    When ``deep`` is true, each flagged item is drilled for a fix: misquotes get
    the correct passage (get_case_passages), caution cites get the negative
    forward-citation (find_cases_that_cite), unknown cites get a summary check.
    """
    _require_descrybe(user)

    text = (data.get("text") or "").strip()
    name = data.get("name")
    deep = bool(data.get("deep"))
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    from app.services.cite_check import run_cite_check

    async def event_stream():
        async for event in run_cite_check(text, name, user.id, deep=deep):
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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
    _require_descrybe(user)

    from app.services.matter_enrichment import enrich_matter

    return await enrich_matter(
        matter_id=matter_id,
        initiated_by=user.id,
    )
