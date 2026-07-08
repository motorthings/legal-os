"""
Legal AI OS — Regulatory Change Monitor API

Poll regulatory sources, extract structured changes, map to active matters.
"""

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query

from app.database import get_supabase
from app.auth import get_current_user, User

router = APIRouter()

# ---------------------------------------------------------------------------
# Governance contract
# ---------------------------------------------------------------------------

@router.get("/health")
async def regulatory_health():
    return {
        "function": "regulatory-monitor",
        "status": "healthy",
        "version": "0.1.0",
        "capabilities": [
            "source_polling",
            "change_extraction",
            "matter_matching",
            "jurisdiction_filtering",
            "impact_assessment",
            "notification",
        ],
    }


@router.get("/metrics")
async def regulatory_metrics():
    supabase = get_supabase()
    sources = supabase.table("regulatory_sources").select("id", count="exact").execute()
    updates = supabase.table("regulatory_updates").select("id", count="exact").execute()
    flags = supabase.table("matter_regulatory_flags").select("id, impact_severity", count="exact").execute()

    return {
        "function": "regulatory-monitor",
        "sources_tracked": sources.count if hasattr(sources, "count") else 0,
        "updates_extracted": updates.count if hasattr(updates, "count") else 0,
        "open_flags": flags.count if hasattr(flags, "count") else 0,
    }


@router.get("/targets")
async def regulatory_targets():
    return {
        "function": "regulatory-monitor",
        "targets": {
            "sources_monitored": 10,
            "extraction_recall": "> 0.95",
            "matter_match_precision": "> 0.90",
            "poll_latency": "< 5 min per source",
            "notification_delivery": "< 30 seconds",
        },
    }


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

@router.get("/sources")
async def list_sources():
    result = get_supabase().table("regulatory_sources").select("*").order("agency").execute()
    return result.data or []


@router.get("/sources/{source_id}/updates")
async def source_updates(source_id: UUID, limit: int = 50):
    result = (
        get_supabase()
        .table("regulatory_updates")
        .select("*")
        .eq("source_id", str(source_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


# ---------------------------------------------------------------------------
# Updates
# ---------------------------------------------------------------------------

@router.get("/updates")
async def list_updates(
    jurisdiction: str | None = None,
    agency: str | None = None,
    change_type: str | None = None,
    days: int = 30,
    limit: int = 50,
):
    """List regulatory updates with optional filters."""
    query = (
        get_supabase()
        .table("regulatory_updates")
        .select("*")
        .gte("created_at", datetime.now(timezone.utc).isoformat())
        .order("created_at", desc=True)
        .limit(limit)
    )
    # Use a simpler approach — filter in Python since supabase-py query chaining is limited
    result = query.execute()
    updates = result.data or []

    cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    cutoff = cutoff - timedelta(days=days)

    if jurisdiction:
        updates = [u for u in updates if u.get("jurisdiction") == jurisdiction]
    if agency:
        updates = [u for u in updates if u.get("agency") == agency]
    if change_type:
        updates = [u for u in updates if u.get("change_type") == change_type]

    # Filter by date
    filtered = []
    for u in updates:
        created = u.get("created_at", "")
        if created:
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if dt >= cutoff:
                    filtered.append(u)
            except Exception:
                filtered.append(u)
        else:
            filtered.append(u)

    return filtered[:limit]


@router.get("/updates/{update_id}")
async def get_update(update_id: UUID):
    """Get a single regulatory update with full detail and linked flags."""
    supabase = get_supabase()

    update = supabase.table("regulatory_updates").select("*").eq("id", str(update_id)).execute()
    if not update.data:
        raise HTTPException(status_code=404, detail="Update not found")

    flags = (
        supabase.table("matter_regulatory_flags")
        .select("*, matters(name, matter_number)")
        .eq("update_id", str(update_id))
        .execute()
    )

    return {
        **update.data[0],
        "flagged_matters": flags.data or [],
    }


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

@router.get("/flags")
async def list_flags(
    user: User = Depends(get_current_user),
    status: str | None = None,
    severity: str | None = None,
):
    """List matter regulatory flags for the user's client."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    query = (
        get_supabase()
        .table("matter_regulatory_flags")
        .select("*, matters(name, matter_number, jurisdiction, practice_area), regulatory_updates(regulation_name, change_type, change_summary, effective_date, compliance_deadline)")
        .eq("client_id", str(user.client_id))
        .order("created_at", desc=True)
        .limit(100)
    )

    if status:
        query = query.eq("status", status)
    if severity:
        query = query.eq("impact_severity", severity)

    result = query.execute()
    return result.data or []


@router.patch("/flags/{flag_id}")
async def update_flag(
    flag_id: UUID,
    data: dict,
    user: User = Depends(get_current_user),
):
    """Update a flag's status and review notes."""
    supabase = get_supabase()

    update_data = {
        "status": data.get("status"),
        "review_notes": data.get("review_notes"),
        "reviewed_by": str(user.id),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    update_data = {k: v for k, v in update_data.items() if v is not None}

    result = (
        supabase.table("matter_regulatory_flags")
        .update(update_data)
        .eq("id", str(flag_id))
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Flag not found")
    return result.data[0]


# ---------------------------------------------------------------------------
# Polling trigger
# ---------------------------------------------------------------------------

@router.post("/poll")
async def trigger_poll(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    """Trigger a poll of all active regulatory sources."""
    from app.workers.tasks.regulatory_monitor import poll_all_sources

    background_tasks.add_task(poll_all_sources)
    return {"status": "polling started", "message": "Polling all active regulatory sources"}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def regulatory_dashboard(user: User = Depends(get_current_user)):
    """Dashboard view: recent updates + open flags + source status."""
    supabase = get_supabase()

    # Recent updates
    updates = (
        supabase.table("regulatory_updates")
        .select("*")
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    # Open flags (client-scoped)
    flags = []
    if user.client_id:
        flags_result = (
            supabase.table("matter_regulatory_flags")
            .select("id, impact_severity, status, matter_id, update_id, created_at")
            .eq("client_id", str(user.client_id))
            .in_("status", ["unreviewed", "action_required"])
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        flags = flags_result.data or []

    # Source health
    sources = supabase.table("regulatory_sources").select("*").order("agency").execute()

    return {
        "recent_updates": updates.data or [],
        "open_flags": flags,
        "sources": sources.data or [],
        "summary": {
            "total_sources": len(sources.data) if sources.data else 0,
            "active_sources": sum(1 for s in (sources.data or []) if s.get("status") == "active"),
            "open_flags_count": len(flags),
            "critical_flags": sum(1 for f in flags if f.get("impact_severity") == "critical"),
        },
    }
