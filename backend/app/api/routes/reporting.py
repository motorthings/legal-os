"""
Legal AI OS — Client Value Reporting API

Powers the "prove it" story: per-client quarterly reports showing
exactly what AI saved — with the math to back it up.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import get_supabase
from app.auth import get_current_user, User
from app.services.metrics import get_client_summary, get_client_monthly_rollup

router = APIRouter()


# ---------------------------------------------------------------------------
# Governance contract
# ---------------------------------------------------------------------------

@router.get("/health")
async def reporting_health():
    return {
        "function": "client-value-reporting",
        "status": "healthy",
        "version": "0.1.0",
        "capabilities": [
            "per_client_quarterly_reports",
            "time_saved_aggregation",
            "cost_tracking",
            "function_adoption_metrics",
            "risk_distribution",
            "governance_artifacts",
        ],
    }


@router.get("/metrics")
async def reporting_metrics():
    supabase = get_supabase()
    result = (
        supabase.table("metrics")
        .select("function_id, cost_usd, time_saved_ms, created_at")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    total_saved_ms = sum(r.get("time_saved_ms", 0) for r in (result.data or []))
    return {
        "function": "client-value-reporting",
        "total_invocations": len(result.data) if result.data else 0,
        "total_hours_saved": round(total_saved_ms / 3_600_000, 1),
    }


@router.get("/targets")
async def reporting_targets():
    return {
        "function": "client-value-reporting",
        "targets": {
            "report_generation_time_s": "< 5",
            "data_freshness": "< 1 hour",
            "report_completeness": "100% (all functions covered)",
            "export_formats": ["json", "pdf", "csv"],
        },
    }


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@router.get("/summary")
async def client_summary(user: User = Depends(get_current_user)):
    """Get summary stats for the authenticated user's client."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    summary = get_client_summary(user.client_id)
    if not summary:
        return {
            "client_id": str(user.client_id),
            "total_matters": 0,
            "active_matters": 0,
            "functions_used": 0,
            "total_ai_cost_usd": 0,
            "total_hours_saved": 0,
            "first_invocation": None,
            "last_invocation": None,
        }
    return summary


@router.get("/monthly")
async def monthly_rollup(
    user: User = Depends(get_current_user),
    months: int = Query(default=12, le=24),
):
    """Get monthly metrics rollup for the authenticated user's client."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    result = (
        get_supabase()
        .table("metrics_monthly_rollup")
        .select("*")
        .eq("client_id", str(user.client_id))
        .order("month", desc=True)
        .limit(months)
        .execute()
    )
    return result.data or []


@router.get("/by-function")
async def by_function(user: User = Depends(get_current_user)):
    """Breakdown of metrics by function for the current client."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    result = (
        get_supabase()
        .table("metrics")
        .select("function_id, total_tokens, cost_usd, time_saved_ms, processing_time_ms")
        .eq("client_id", str(user.client_id))
        .execute()
    )

    # Aggregate by function
    functions = (
        get_supabase()
        .table("functions")
        .select("id, slug, name, status")
        .execute()
    )
    fn_map = {f["id"]: f for f in (functions.data or [])}

    by_fn: dict = {}
    for row in (result.data or []):
        fid = row["function_id"]
        if fid not in by_fn:
            by_fn[fid] = {
                "function_id": fid,
                "slug": fn_map.get(fid, {}).get("slug", "unknown"),
                "name": fn_map.get(fid, {}).get("name", "Unknown"),
                "status": fn_map.get(fid, {}).get("status", "unknown"),
                "invocations": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "total_time_saved_hours": 0.0,
                "avg_processing_ms": 0,
            }
        by_fn[fid]["invocations"] += 1
        by_fn[fid]["total_tokens"] += row.get("total_tokens", 0)
        by_fn[fid]["total_cost_usd"] += float(row.get("cost_usd", 0))
        by_fn[fid]["total_time_saved_hours"] += row.get("time_saved_ms", 0) / 3_600_000

    # Add zero-entry functions
    for fid, fn in fn_map.items():
        if fid not in by_fn:
            by_fn[fid] = {
                "function_id": fid,
                "slug": fn.get("slug", "unknown"),
                "name": fn.get("name", "Unknown"),
                "status": fn.get("status", "unknown"),
                "invocations": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "total_time_saved_hours": 0.0,
                "avg_processing_ms": 0,
            }

    return list(by_fn.values())


@router.get("/quarterly-report")
async def quarterly_report(user: User = Depends(get_current_user)):
    """Generate a full quarterly report for the current client."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()

    # Client summary
    summary = get_client_summary(user.client_id)

    # Last 3 months of monthly rollup
    rollup = (
        supabase.table("metrics_monthly_rollup")
        .select("*")
        .eq("client_id", str(user.client_id))
        .order("month", desc=True)
        .limit(3)
        .execute()
    )

    # Functions used
    fn_breakdown = await by_function(user=user)

    # Recent audit trail for governance artifacts
    audit = (
        supabase.table("audit_trail")
        .select("id, event_type, event_summary, model_used, created_at")
        .eq("client_id", str(user.client_id))
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    # Baselines
    baselines = (
        supabase.table("time_saved_baselines")
        .select("function_id, baseline_seconds, description")
        .or_(f"client_id.eq.{user.client_id},client_id.is.null")
        .execute()
    )

    return {
        "report_type": "Client Value Report",
        "client_id": str(user.client_id),
        "generated_at": "now",
        "summary": summary,
        "monthly_trend": rollup.data or [],
        "by_function": fn_breakdown,
        "governance_artifacts": {
            "total_audit_entries": len(audit.data) if audit.data else 0,
            "audit_sample": (audit.data or [])[:10],
        },
        "baselines": baselines.data or [],
    }
