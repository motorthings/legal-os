"""
Legal AI OS — ROI Calculation Engine

Powers the JD requirement: "Develop frameworks to track AI solution performance,
including time saved, cost impact, and quality metrics."

Cost impact = time saved × the right rate. Quality = structured, not free-text.
Adoption = active / eligible. ROI = cost avoided − AI cost.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from app.database import get_supabase


# ---------------------------------------------------------------------------
# Rate cards
# ---------------------------------------------------------------------------

def get_active_rate(
    client_id: UUID,
    practice_group_id: UUID | None = None,
    rate_type: str = "blended",
) -> float | None:
    """Get the active hourly rate for a client/practice-group/type combination.
    Falls back: exact match → client default (null practice_group) → None.

    Returns None if rate_cards table doesn't exist yet (graceful degradation).
    """
    supabase = get_supabase()

    try:
        # Exact match (practice_group_id may be null)
        query = (
            supabase.table("rate_cards")
            .select("hourly_rate_usd")
            .eq("client_id", str(client_id))
            .eq("rate_type", rate_type)
            .is_("effective_to", "null")
            .limit(1)
        )
        if practice_group_id:
            query = query.eq("practice_group_id", str(practice_group_id))
        else:
            query = query.is_("practice_group_id", "null")

        result = query.execute()
        if result.data:
            return float(result.data[0]["hourly_rate_usd"])

        # Fallback: client default (null practice_group) — only if we didn't already query for it
        if practice_group_id is not None:
            result = (
                supabase.table("rate_cards")
                .select("hourly_rate_usd")
                .eq("client_id", str(client_id))
                .is_("practice_group_id", "null")
                .eq("rate_type", rate_type)
                .is_("effective_to", "null")
                .limit(1)
                .execute()
            )
            if result.data:
                return float(result.data[0]["hourly_rate_usd"])
    except Exception:
        # Table doesn't exist yet — run migrations
        pass

    return None


def calculate_cost_avoided(
    time_saved_ms: int,
    client_id: UUID,
    practice_group_id: UUID | None = None,
    rate_type: str = "blended",
) -> dict:
    """Convert time saved to cost avoided using the configured rate card.

    Returns:
        {
            "hours_saved": 12.5,
            "hourly_rate_usd": 350.00,
            "cost_avoided_usd": 4375.00
        }
    """
    hours_saved = time_saved_ms / 3_600_000
    rate = get_active_rate(client_id, practice_group_id, rate_type) or 0.0
    cost_avoided = round(hours_saved * rate, 2)

    return {
        "hours_saved": round(hours_saved, 2),
        "hourly_rate_usd": rate,
        "cost_avoided_usd": cost_avoided,
    }


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------

def get_calibrated_baseline(
    function_id: UUID,
    client_id: UUID | None = None,
) -> dict | None:
    """Get the calibrated baseline for a function, with methodology metadata."""
    supabase = get_supabase()
    query = (
        supabase.table("time_saved_baselines")
        .select("*")
        .eq("function_id", str(function_id))
    )
    if client_id:
        query = query.eq("client_id", str(client_id))
    else:
        query = query.is_("client_id", "null")

    result = query.execute()
    if result.data:
        row = result.data[0]
        return {
            "function_id": row["function_id"],
            "client_id": row.get("client_id"),
            "baseline_seconds": row["baseline_seconds"],
            "methodology": row.get("methodology"),
            "calibrated_by": row.get("calibrated_by"),
            "calibrated_at": row.get("calibrated_at"),
            "sample_size": row.get("sample_size"),
            "confidence_level": row.get("confidence_level", "medium"),
        }
    return None


# ---------------------------------------------------------------------------
# Quality metrics
# ---------------------------------------------------------------------------

def get_quality_summary(
    function_id: UUID | None = None,
    client_id: UUID | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
) -> dict:
    """Aggregate quality metrics for a function/client/period.

    Returns override rate, accuracy rate, false positive rate, and avg agreement.
    """
    supabase = get_supabase()
    query = supabase.table("quality_reviews").select("*")

    if function_id:
        query = query.eq("function_id", str(function_id))
    if client_id:
        query = query.eq("client_id", str(client_id))
    if period_start:
        query = query.gte("created_at", f"{period_start.isoformat()}T00:00:00+00:00")
    if period_end:
        query = query.lte("created_at", f"{period_end.isoformat()}T23:59:59+00:00")

    result = query.execute()
    rows = result.data or []
    total = len(rows)

    if total == 0:
        return {
            "total_reviews": 0,
            "accuracy_rate": None,
            "override_rate": None,
            "false_positive_rate": None,
            "false_negative_rate": None,
            "avg_agreement_score": None,
        }

    correct = sum(1 for r in rows if r["accuracy"] == "correct")
    minor = sum(1 for r in rows if r["accuracy"] == "minor_issues")
    overrode = sum(1 for r in rows if r.get("human_overrode"))
    fp = sum(1 for r in rows if r.get("false_positive"))
    fn = sum(1 for r in rows if r.get("false_negative"))
    agreements = [r["agreement_score"] for r in rows if r.get("agreement_score") is not None]

    return {
        "total_reviews": total,
        "correct_count": correct,
        "minor_issues_count": minor,
        "major_issues_count": sum(1 for r in rows if r["accuracy"] == "major_issues"),
        "incorrect_count": sum(1 for r in rows if r["accuracy"] == "incorrect"),
        "accuracy_rate": round(((correct + minor) / total) * 100, 1),
        "override_rate": round((overrode / total) * 100, 1),
        "false_positive_rate": round((fp / total) * 100, 1),
        "false_negative_rate": round((fn / total) * 100, 1),
        "avg_agreement_score": round(sum(agreements) / len(agreements), 1) if agreements else None,
    }


# ---------------------------------------------------------------------------
# Adoption
# ---------------------------------------------------------------------------

def get_adoption_rate(
    client_id: UUID,
    function_id: UUID | None = None,
    practice_group_id: UUID | None = None,
    period_days: int = 30,
) -> dict:
    """Calculate adoption rate: active users / eligible users.

    Active = at least one invocation in the trailing period.
    """
    supabase = get_supabase()

    # Eligible users
    eligible_query = (
        supabase.table("eligible_users")
        .select("user_id")
        .eq("client_id", str(client_id))
        .is_("eligible_until", "null")
    )
    if function_id:
        eligible_query = eligible_query.or_(
            f"function_id.eq.{function_id},function_id.is.null"
        )
    if practice_group_id:
        eligible_query = eligible_query.eq("practice_group_id", str(practice_group_id))

    eligible_result = eligible_query.execute()
    eligible_ids = {r["user_id"] for r in (eligible_result.data or [])}
    eligible_count = len(eligible_ids)

    if eligible_count == 0:
        return {
            "eligible_count": 0,
            "active_count": 0,
            "adoption_pct": 0.0,
            "period_days": period_days,
        }

    # Active users in period
    from datetime import timedelta
    start_date = (datetime.now(timezone.utc) - timedelta(days=period_days)).isoformat()

    active_query = (
        supabase.table("metrics")
        .select("initiated_by")
        .eq("client_id", str(client_id))
        .gte("started_at", start_date)
    )
    if function_id:
        active_query = active_query.eq("function_id", str(function_id))
    active_result = active_query.execute()

    active_ids = {r["initiated_by"] for r in (active_result.data or []) if r.get("initiated_by")}
    active_in_eligible = len(active_ids & eligible_ids)
    adoption_pct = round((active_in_eligible / eligible_count) * 100, 1)

    return {
        "eligible_count": eligible_count,
        "active_count": active_in_eligible,
        "adoption_pct": adoption_pct,
        "period_days": period_days,
    }


# ---------------------------------------------------------------------------
# ROI Summary
# ---------------------------------------------------------------------------

def get_roi_summary(
    client_id: UUID | None = None,
    function_id: UUID | None = None,
    practice_group_id: UUID | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
) -> dict:
    """Full ROI summary: cost avoided, AI cost, net ROI, ROI ratio.

    This is the "return on innovation" the JD asks for.
    Breaks down by function and practice group.
    """
    supabase = get_supabase()

    # Query metrics for the period
    query = supabase.table("metrics").select("*")
    if client_id:
        query = query.eq("client_id", str(client_id))
    if function_id:
        query = query.eq("function_id", str(function_id))
    if period_start:
        query = query.gte("started_at", period_start.isoformat())
    if period_end:
        query = query.lte("started_at", period_end.isoformat())

    result = query.execute()
    rows = result.data or []

    # Aggregate
    total_time_saved_ms = sum(r.get("time_saved_ms", 0) for r in rows)
    total_ai_cost_usd = sum(float(r.get("cost_usd", 0)) for r in rows)
    total_invocations = len(rows)

    # Cost avoided — need rates per row. For aggregated view, use client default.
    if client_id:
        rate_result = calculate_cost_avoided(total_time_saved_ms, client_id, practice_group_id)
        total_cost_avoided = rate_result["cost_avoided_usd"]
        hourly_rate = rate_result["hourly_rate_usd"]
        total_hours_saved = rate_result["hours_saved"]
    else:
        total_cost_avoided = 0.0
        hourly_rate = 0.0
        total_hours_saved = total_time_saved_ms / 3_600_000

    net_roi = round(total_cost_avoided - total_ai_cost_usd, 2)
    roi_ratio = round(total_cost_avoided / total_ai_cost_usd, 2) if total_ai_cost_usd > 0 else None

    # Breakdown by function
    by_function: dict = {}
    for row in rows:
        fid = row.get("function_id")
        if not fid:
            continue
        if fid not in by_function:
            by_function[fid] = {
                "function_id": fid,
                "invocations": 0,
                "time_saved_ms": 0,
                "ai_cost_usd": 0.0,
            }
        by_function[fid]["invocations"] += 1
        by_function[fid]["time_saved_ms"] += row.get("time_saved_ms", 0)
        by_function[fid]["ai_cost_usd"] += float(row.get("cost_usd", 0))

    # Enrich function breakdowns with names and cost avoided
    fn_detail = []
    for fid, data in by_function.items():
        fn_result = supabase.table("functions").select("slug, name").eq("id", fid).execute()
        fn_name = fn_result.data[0]["name"] if fn_result.data else "Unknown"
        fn_slug = fn_result.data[0]["slug"] if fn_result.data else "unknown"

        if client_id:
            fn_cost = calculate_cost_avoided(data["time_saved_ms"], client_id, practice_group_id)
            fn_cost_avoided = fn_cost["cost_avoided_usd"]
        else:
            fn_cost_avoided = 0.0

        fn_detail.append({
            "function_id": fid,
            "slug": fn_slug,
            "name": fn_name,
            "invocations": data["invocations"],
            "hours_saved": round(data["time_saved_ms"] / 3_600_000, 2),
            "cost_avoided_usd": fn_cost_avoided,
            "ai_cost_usd": round(data["ai_cost_usd"], 2),
            "net_roi_usd": round(fn_cost_avoided - data["ai_cost_usd"], 2),
        })

    return {
        "period": {
            "start": period_start.isoformat() if period_start else None,
            "end": period_end.isoformat() if period_end else None,
        },
        "summary": {
            "total_invocations": total_invocations,
            "total_hours_saved": round(total_hours_saved, 2),
            "total_cost_avoided_usd": total_cost_avoided,
            "total_ai_cost_usd": round(total_ai_cost_usd, 2),
            "net_roi_usd": net_roi,
            "roi_ratio": roi_ratio,
            "hourly_rate_usd": hourly_rate,
        },
        "by_function": fn_detail,
    }
