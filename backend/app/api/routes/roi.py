"""
Legal AI OS — ROI API Routes

Powers the portfolio dashboard and client value reports with:
- Cost impact (time saved × rate)
- Quality metrics (override rate, accuracy, agreement)
- Adoption rates (active / eligible)
- ROI summaries (cost avoided − AI cost)
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, User
from app.database import get_supabase
from app.services.roi import (
    calculate_cost_avoided,
    get_active_rate,
    get_calibrated_baseline,
    get_quality_summary,
    get_adoption_rate,
    get_roi_summary,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Governance contract
# ---------------------------------------------------------------------------

@router.get("/health")
async def roi_health():
    return {
        "function": "roi-framework",
        "status": "healthy",
        "version": "0.1.0",
        "capabilities": [
            "cost_impact_calculation",
            "calibrated_baselines",
            "quality_metrics",
            "adoption_tracking",
            "roi_summary",
        ],
    }


@router.get("/metrics")
async def roi_metrics():
    supabase = get_supabase()
    result = (
        supabase.table("metrics")
        .select("time_saved_ms, cost_usd")
        .order("started_at", desc=True)
        .limit(100)
        .execute()
    )
    total_saved = sum(r.get("time_saved_ms", 0) for r in (result.data or []))
    total_cost = sum(float(r.get("cost_usd", 0)) for r in (result.data or []))
    return {
        "function": "roi-framework",
        "total_hours_saved": round(total_saved / 3_600_000, 1),
        "total_ai_cost_usd": round(total_cost, 2),
        "roi_ratio": round((total_saved / 3_600_000 * 350) / total_cost, 2) if total_cost > 0 else None,
    }


@router.get("/targets")
async def roi_targets():
    return {
        "function": "roi-framework",
        "targets": {
            "accuracy_rate": "> 85%",
            "override_rate": "< 15%",
            "adoption_rate": "> 60% within 6 months",
            "roi_ratio": "> 5:1",
        },
    }


# ---------------------------------------------------------------------------
# Rate cards
# ---------------------------------------------------------------------------

@router.get("/rates")
async def list_rates(
    user: User = Depends(get_current_user),
    practice_group_id: Optional[str] = None,
):
    """List active rate cards for the user's client."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()
    query = (
        supabase.table("rate_cards")
        .select("*")
        .eq("client_id", str(user.client_id))
        .is_("effective_to", "null")
        .order("rate_type")
    )
    if practice_group_id:
        query = query.eq("practice_group_id", practice_group_id)

    result = query.execute()
    return result.data or []


@router.post("/rates")
async def create_rate(
    rate_type: str = Query(default="blended"),
    hourly_rate_usd: float = Query(...),
    practice_group_id: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """Create a new rate card entry."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()
    row = {
        "client_id": str(user.client_id),
        "practice_group_id": practice_group_id,
        "rate_type": rate_type,
        "hourly_rate_usd": hourly_rate_usd,
        "created_by": str(user.id),
    }
    result = supabase.table("rate_cards").insert(row).execute()
    return result.data[0] if result.data else {}


@router.get("/rates/active")
async def active_rate(
    user: User = Depends(get_current_user),
    practice_group_id: Optional[str] = None,
    rate_type: str = "blended",
):
    """Get the currently active rate for the user's client."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    rate = get_active_rate(
        user.client_id,
        UUID(practice_group_id) if practice_group_id else None,
        rate_type,
    )
    return {
        "client_id": str(user.client_id),
        "practice_group_id": practice_group_id,
        "rate_type": rate_type,
        "hourly_rate_usd": rate,
    }


# ---------------------------------------------------------------------------
# Cost impact
# ---------------------------------------------------------------------------

@router.get("/cost-impact")
async def cost_impact(
    user: User = Depends(get_current_user),
    time_saved_ms: int = Query(...),
    practice_group_id: Optional[str] = None,
    rate_type: str = "blended",
):
    """Calculate cost avoided for a given time savings."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    return calculate_cost_avoided(
        time_saved_ms,
        user.client_id,
        UUID(practice_group_id) if practice_group_id else None,
        rate_type,
    )


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------

@router.get("/baselines")
async def list_baselines(
    user: User = Depends(get_current_user),
):
    """List calibrated baselines for the user's client."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()
    result = (
        supabase.table("time_saved_baselines")
        .select("*")
        .or_(f"client_id.eq.{user.client_id},client_id.is.null")
        .execute()
    )
    return result.data or []


@router.put("/baselines/{function_id}")
async def update_baseline(
    function_id: str,
    baseline_seconds: int = Query(...),
    methodology: Optional[str] = None,
    sample_size: Optional[int] = None,
    confidence_level: Optional[str] = "medium",
    reason: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """Update a baseline with calibration metadata. Logs the change."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()

    # Get old baseline for change log
    old = (
        supabase.table("time_saved_baselines")
        .select("baseline_seconds")
        .eq("function_id", function_id)
        .eq("client_id", str(user.client_id))
        .limit(1)
        .execute()
    )
    old_seconds = old.data[0]["baseline_seconds"] if old.data else None

    # Upsert baseline
    row = {
        "function_id": function_id,
        "client_id": str(user.client_id),
        "baseline_seconds": baseline_seconds,
        "methodology": methodology,
        "calibrated_by": str(user.id),
        "calibrated_at": "now",
        "sample_size": sample_size,
        "confidence_level": confidence_level,
    }

    # Check if exists
    existing = (
        supabase.table("time_saved_baselines")
        .select("id")
        .eq("function_id", function_id)
        .eq("client_id", str(user.client_id))
        .limit(1)
        .execute()
    )

    if existing.data:
        result = (
            supabase.table("time_saved_baselines")
            .update(row)
            .eq("id", existing.data[0]["id"])
            .execute()
        )
    else:
        result = supabase.table("time_saved_baselines").insert(row).execute()

    # Log the calibration change
    supabase.table("baseline_calibrations").insert({
        "function_id": function_id,
        "client_id": str(user.client_id),
        "old_baseline_seconds": old_seconds,
        "new_baseline_seconds": baseline_seconds,
        "methodology": methodology,
        "sample_size": sample_size,
        "confidence_level": confidence_level,
        "reason": reason or "Manual calibration update",
        "calibrated_by": str(user.id),
    }).execute()

    return result.data[0] if result.data else {"status": "updated"}


# ---------------------------------------------------------------------------
# Quality metrics
# ---------------------------------------------------------------------------

@router.post("/quality")
async def record_quality_review(
    invocation_id: str = Query(...),
    function_id: str = Query(...),
    accuracy: str = Query(...),
    false_positive: bool = Query(default=False),
    false_negative: bool = Query(default=False),
    human_overrode: bool = Query(default=False),
    override_reason: Optional[str] = None,
    agreement_score: Optional[int] = None,
    reviewer_notes: Optional[str] = None,
    review_time_ms: Optional[int] = None,
    audit_trail_id: Optional[str] = None,
    practice_group_id: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """Record a quality review for an AI invocation."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()
    row = {
        "invocation_id": invocation_id,
        "audit_trail_id": audit_trail_id,
        "function_id": function_id,
        "client_id": str(user.client_id),
        "practice_group_id": practice_group_id,
        "reviewer_id": str(user.id),
        "accuracy": accuracy,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "human_overrode": human_overrode,
        "override_reason": override_reason,
        "agreement_score": agreement_score,
        "reviewer_notes": reviewer_notes,
        "review_time_ms": review_time_ms,
    }
    result = supabase.table("quality_reviews").insert(row).execute()
    return result.data[0] if result.data else {}


@router.get("/quality/summary")
async def quality_summary(
    user: User = Depends(get_current_user),
    function_id: Optional[str] = None,
    period_days: int = Query(default=90, le=365),
):
    """Get quality metrics summary for the user's client."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    period_end = date.today()
    period_start = period_end - timedelta(days=period_days)

    return get_quality_summary(
        function_id=UUID(function_id) if function_id else None,
        client_id=user.client_id,
        period_start=period_start,
        period_end=period_end,
    )


# ---------------------------------------------------------------------------
# Adoption
# ---------------------------------------------------------------------------

@router.get("/adoption")
async def adoption(
    user: User = Depends(get_current_user),
    function_id: Optional[str] = None,
    practice_group_id: Optional[str] = None,
    period_days: int = Query(default=30, le=365),
):
    """Get adoption rate for the user's client."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    return get_adoption_rate(
        client_id=user.client_id,
        function_id=UUID(function_id) if function_id else None,
        practice_group_id=UUID(practice_group_id) if practice_group_id else None,
        period_days=period_days,
    )


# ---------------------------------------------------------------------------
# Eligible users
# ---------------------------------------------------------------------------

@router.get("/eligible-users")
async def list_eligible_users(
    user: User = Depends(get_current_user),
    practice_group_id: Optional[str] = None,
    function_id: Optional[str] = None,
):
    """List eligible users for adoption tracking."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()
    query = (
        supabase.table("eligible_users")
        .select("*, user_profiles(display_name, email)")
        .eq("client_id", str(user.client_id))
        .is_("eligible_until", "null")
    )
    if practice_group_id:
        query = query.eq("practice_group_id", practice_group_id)
    if function_id:
        query = query.or_(f"function_id.eq.{function_id},function_id.is.null")

    result = query.execute()
    return result.data or []


@router.post("/eligible-users")
async def add_eligible_user(
    user_id: str = Query(...),
    practice_group_id: Optional[str] = None,
    function_id: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """Mark a user as eligible for AI tools."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()
    row = {
        "client_id": str(user.client_id),
        "practice_group_id": practice_group_id,
        "user_id": user_id,
        "function_id": function_id,
        "created_by": str(user.id),
    }
    result = supabase.table("eligible_users").insert(row).execute()
    return result.data[0] if result.data else {}


# ---------------------------------------------------------------------------
# ROI Summary — the "return on innovation" number
# ---------------------------------------------------------------------------

@router.get("/summary")
async def roi_summary(
    user: User = Depends(get_current_user),
    function_id: Optional[str] = None,
    practice_group_id: Optional[str] = None,
    period_days: int = Query(default=90, le=730),
):
    """Full ROI summary: cost avoided, AI cost, net ROI, ROI ratio.

    This is the number the JD asks for: "return on innovation."
    """
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    period_end = date.today()
    period_start = period_end - timedelta(days=period_days)

    return get_roi_summary(
        client_id=user.client_id,
        function_id=UUID(function_id) if function_id else None,
        practice_group_id=UUID(practice_group_id) if practice_group_id else None,
        period_start=period_start,
        period_end=period_end,
    )
