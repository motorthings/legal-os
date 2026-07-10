"""
Legal AI OS — POC Pipeline API Routes

Tracks AI proof-of-concept projects: discovery → build → review → graduated.
Maps to JD: "Lead end-to-end delivery of AI-enabled client projects
from concept through implementation" and "Capture feedback for continuous improvement."
"""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, User
from app.database import get_supabase

router = APIRouter()


# ---------------------------------------------------------------------------
# Governance contract
# ---------------------------------------------------------------------------

@router.get("/health")
async def poc_health():
    return {
        "function": "poc-pipeline",
        "status": "healthy",
        "version": "0.1.0",
    }


@router.get("/metrics")
async def poc_metrics():
    supabase = get_supabase()
    result = supabase.table("poc_projects").select("status").execute()
    statuses = {}
    for row in (result.data or []):
        s = row["status"]
        statuses[s] = statuses.get(s, 0) + 1
    return {
        "function": "poc-pipeline",
        "total_projects": len(result.data) if result.data else 0,
        "by_status": statuses,
    }


@router.get("/targets")
async def poc_targets():
    return {
        "function": "poc-pipeline",
        "targets": {
            "active_pocs": "3-5 at any time",
            "graduation_rate": "> 50% of POCs reach graduated status",
            "avg_discovery_to_graduated_days": "< 90",
        },
    }


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("/")
async def list_pocs(
    user: User = Depends(get_current_user),
    status: Optional[str] = None,
    practice_group_id: Optional[str] = None,
    limit: int = Query(default=50, le=200),
):
    """List POC projects, optionally filtered by status or practice group."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()
    query = (
        supabase.table("poc_projects")
        .select("*")
        .eq("client_id", str(user.client_id))
        .order("updated_at", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if practice_group_id:
        query = query.eq("practice_group_id", practice_group_id)

    result = query.execute()
    return result.data or []


@router.post("/")
async def create_poc(
    name: str = Query(...),
    function_type: str = Query(...),
    description: Optional[str] = None,
    champion_id: Optional[str] = None,
    practice_group_id: Optional[str] = None,
    target_completion: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """Create a new POC project."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()
    row = {
        "client_id": str(user.client_id),
        "practice_group_id": practice_group_id,
        "name": name,
        "description": description,
        "function_type": function_type,
        "status": "discovery",
        "champion_id": champion_id,
        "target_completion": target_completion,
        "started_at": date.today().isoformat(),
        "created_by": str(user.id),
    }
    result = supabase.table("poc_projects").insert(row).execute()
    return result.data[0] if result.data else {}


@router.patch("/{poc_id}")
async def update_poc(
    poc_id: str,
    status: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    notes: Optional[str] = None,
    target_completion: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """Update a POC project — typically to move it between statuses."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()

    # Verify ownership
    existing = (
        supabase.table("poc_projects")
        .select("id, client_id, status")
        .eq("id", poc_id)
        .eq("client_id", str(user.client_id))
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="POC project not found")

    current_status = existing.data[0]["status"]
    patch = {"updated_at": "now"}

    if status:
        patch["status"] = status
        # Auto-set completed_at when graduating or cancelling
        if status in ("graduated", "cancelled") and current_status not in ("graduated", "cancelled"):
            patch["completed_at"] = date.today().isoformat()
        # Clear completed_at if re-opening
        if status not in ("graduated", "cancelled"):
            patch["completed_at"] = None

    if name:
        patch["name"] = name
    if description is not None:
        patch["description"] = description
    if notes is not None:
        patch["notes"] = notes
    if target_completion:
        patch["target_completion"] = target_completion

    result = (
        supabase.table("poc_projects")
        .update(patch)
        .eq("id", poc_id)
        .execute()
    )
    return result.data[0] if result.data else {}


@router.get("/{poc_id}")
async def get_poc(
    poc_id: str,
    user: User = Depends(get_current_user),
):
    """Get a single POC project with its feedback."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()
    poc = (
        supabase.table("poc_projects")
        .select("*")
        .eq("id", poc_id)
        .eq("client_id", str(user.client_id))
        .limit(1)
        .execute()
    )
    if not poc.data:
        raise HTTPException(status_code=404, detail="POC project not found")

    feedback = (
        supabase.table("poc_feedback")
        .select("*")
        .eq("poc_project_id", poc_id)
        .order("created_at", desc=True)
        .execute()
    )

    return {
        **poc.data[0],
        "feedback": feedback.data or [],
    }


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

@router.post("/{poc_id}/feedback")
async def add_feedback(
    poc_id: str,
    body: str = Query(...),
    feedback_type: str = Query(default="general"),
    user: User = Depends(get_current_user),
):
    """Add feedback to a POC project."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()

    # Verify project exists and belongs to client
    existing = (
        supabase.table("poc_projects")
        .select("id")
        .eq("id", poc_id)
        .eq("client_id", str(user.client_id))
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="POC project not found")

    row = {
        "poc_project_id": poc_id,
        "author_id": str(user.id),
        "feedback_type": feedback_type,
        "body": body,
    }
    result = supabase.table("poc_feedback").insert(row).execute()
    return result.data[0] if result.data else {}


@router.patch("/{poc_id}/feedback/{feedback_id}")
async def resolve_feedback(
    poc_id: str,
    feedback_id: str,
    resolved: bool = Query(default=True),
    user: User = Depends(get_current_user),
):
    """Mark a feedback item as resolved."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="No client association")

    supabase = get_supabase()
    result = (
        supabase.table("poc_feedback")
        .update({"resolved": resolved})
        .eq("id", feedback_id)
        .eq("poc_project_id", poc_id)
        .execute()
    )
    return result.data[0] if result.data else {"status": "updated"}
