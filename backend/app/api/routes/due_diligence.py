"""
Legal AI OS — Due Diligence API Routes

Every endpoint follows the governance contract pattern:
  GET  /health    — is the function running?
  GET  /metrics   — what has it done?
  GET  /targets   — what should it achieve?

CRUD:
  POST   /projects              — create a deal project
  GET    /projects/{id}         — get project details
  GET    /projects/{id}/report  — get consolidated deviation report
  POST   /projects/{id}/upload  — upload documents
  POST   /projects/{id}/analyze — trigger batch analysis
  GET    /deviations/{id}       — get deviation detail
  PATCH  /deviations/{id}       — attorney review decision
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks

from app.database import get_supabase
from app.auth import get_current_user, User
from app.models.due_diligence import (
    DDProject,
    DDProjectCreate,
    DDProjectReport,
    DDAnalyzeRequest,
    DDAnalyzeResponse,
    Deviation,
    DeviationReviewUpdate,
)
from app.services.audit import AuditTrail
from app.services.metrics import MetricsCollector

router = APIRouter()

audit = AuditTrail()


# ---------------------------------------------------------------------------
# Governance contract
# ---------------------------------------------------------------------------

@router.get("/health")
async def dd_health():
    return {
        "function": "due-diligence",
        "status": "healthy",
        "version": "0.1.0",
        "capabilities": [
            "bulk_document_ingestion",
            "target_standards_comparison",
            "deviation_detection",
            "clause_grouping",
            "severity_ranking",
            "consolidated_reporting",
        ],
    }


@router.get("/metrics")
async def dd_metrics():
    """Aggregate metrics for the due diligence function."""
    result = (
        get_supabase()
        .table("metrics")
        .select("count", exact=True)
        .eq("function_id", _get_function_id())
        .execute()
    )
    return {
        "function": "due-diligence",
        "total_invocations": result.count if hasattr(result, "count") else 0,
    }


@router.get("/targets")
async def dd_targets():
    return {
        "function": "due-diligence",
        "targets": {
            "processing_time_per_document_s": "< 30",
            "deviation_recall": "> 0.95",
            "false_positive_rate": "< 0.10",
            "critical_deviation_capture": "1.0 (no misses)",
            "auto_escalation_confidence_threshold": 70,
        },
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_function_id() -> str:
    """Get the due-diligence function UUID from the registry."""
    result = (
        get_supabase()
        .table("functions")
        .select("id")
        .eq("slug", "due-diligence")
        .execute()
    )
    if result.data:
        return result.data[0]["id"]
    raise HTTPException(status_code=500, detail="Function not registered")


# ---------------------------------------------------------------------------
# Projects CRUD
# ---------------------------------------------------------------------------

@router.post("/projects", response_model=DDProject, status_code=201)
async def create_project(project: DDProjectCreate, user: User = Depends(get_current_user)):
    """Create a new due diligence deal project with target standards."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="User has no client association")

    supabase = get_supabase()
    function_id = _get_function_id()

    # Insert project — client_id and practice_group_id from user context
    project_data = {
        "client_id": str(user.client_id),
        "practice_group_id": str(project.practice_group_id),
        "matter_id": str(project.matter_id) if project.matter_id else None,
        "name": project.name,
        "description": project.description,
        "deal_type": project.deal_type,
        "counterparty": project.counterparty,
        "jurisdiction": project.jurisdiction,
        "created_by": str(user.id),
        "assigned_to": str(user.id),
        "status": "draft",
    }
    result = supabase.table("dd_projects").insert(project_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create project")

    project_row = result.data[0]
    project_id = project_row["id"]

    # Insert target standards
    for ts in project.target_standards:
        supabase.table("dd_target_standards").insert({
            "project_id": project_id,
            "category": ts.category,
            "standard_text": ts.standard_text,
            "acceptable_values": ts.acceptable_values,
            "severity": ts.severity,
        }).execute()

    # Audit
    audit.record(
        client_id=user.client_id,
        function_id=UUID(function_id),
        matter_id=project.matter_id,
        event_type="function_invocation",
        event_summary=f"Created DD project: {project.name}",
        initiated_by=user.id,
        model_used="system",
    )

    return project_row


@router.get("/projects/{project_id}")
async def get_project(project_id: UUID):
    """Get a project with its target standards and document list."""
    supabase = get_supabase()

    project = supabase.table("dd_projects").select("*").eq("id", str(project_id)).execute()
    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")

    standards = supabase.table("dd_target_standards").select("*").eq("project_id", str(project_id)).execute()
    documents = supabase.table("dd_documents").select("*").eq("project_id", str(project_id)).execute()

    return {
        **project.data[0],
        "target_standards": standards.data or [],
        "documents": documents.data or [],
    }


@router.get("/projects/{project_id}/report")
async def get_project_report(project_id: UUID):
    """Get the consolidated deviation report for a project."""
    supabase = get_supabase()

    result = (
        supabase.table("dd_project_report")
        .select("*")
        .eq("project_id", str(project_id))
        .execute()
    )

    if not result.data:
        # No deviations yet — return empty report
        project = supabase.table("dd_projects").select("*").eq("id", str(project_id)).execute()
        if not project.data:
            raise HTTPException(status_code=404, detail="Project not found")
        return {
            "project_id": str(project_id),
            "project_name": project.data[0]["name"],
            "total_deviations": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "unreviewed": 0,
        }

    # Also return the deviation list grouped by severity
    deviations = (
        supabase.table("dd_deviations")
        .select("*")
        .eq("project_id", str(project_id))
        .order("severity", desc=True)
        .execute()
    )

    return {
        "summary": result.data[0],
        "deviations": deviations.data or [],
    }


# ---------------------------------------------------------------------------
# Document upload & analysis
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/upload")
async def upload_documents(
    project_id: UUID,
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
):
    """Upload one or more documents to a deal project."""
    if not user.client_id:
        raise HTTPException(status_code=400, detail="User has no client association")

    supabase = get_supabase()
    uploaded = []

    for file in files:
        content = await file.read()
        file_size = len(content)

        # Upload to Supabase Storage
        storage_path = f"due-diligence/{project_id}/{file.filename}"
        supabase.storage.from_("documents").upload(
            storage_path,
            content,
            {"content-type": file.content_type or "application/octet-stream"},
        )

        # Insert document record
        result = (
            supabase.table("dd_documents")
            .insert({
                "project_id": str(project_id),
                "client_id": str(user.client_id),
                "filename": file.filename,
                "file_size_bytes": file_size,
                "file_type": file.filename.split(".")[-1].lower(),
                "storage_path": storage_path,
                "status": "pending",
            })
            .execute()
        )
        if result.data:
            uploaded.append(result.data[0])

    # Update project document count
    supabase.table("dd_projects").update({
        "document_count": supabase.table("dd_documents")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
            .count,
        "status": "uploading",
    }).eq("id", str(project_id)).execute()

    return {"uploaded": len(uploaded), "documents": uploaded}


@router.post("/projects/{project_id}/analyze", response_model=DDAnalyzeResponse)
async def analyze_project(project_id: UUID, user: User = Depends(get_current_user), background_tasks: BackgroundTasks = None):
    """Trigger background analysis of all pending documents in a project."""
    supabase = get_supabase()

    # Get pending documents
    docs = (
        supabase.table("dd_documents")
        .select("id")
        .eq("project_id", str(project_id))
        .eq("status", "pending")
        .execute()
    )

    if not docs.data:
        raise HTTPException(status_code=400, detail="No pending documents to analyze")

    # Update project status
    supabase.table("dd_projects").update({"status": "analyzing"}).eq("id", str(project_id)).execute()

    # Queue each document via FastAPI BackgroundTasks
    from app.workers.tasks.due_diligence import process_dd_document

    for doc in docs.data:
        background_tasks.add_task(
            process_dd_document,
            doc["id"],
            str(user.id),
        )

    return DDAnalyzeResponse(
        project_id=project_id,
        documents_queued=len(docs.data),
        status="analyzing",
    )


# ---------------------------------------------------------------------------
# Deviation review
# ---------------------------------------------------------------------------

@router.get("/deviations/{deviation_id}")
async def get_deviation(deviation_id: UUID):
    """Get full deviation detail including audit trail."""
    supabase = get_supabase()

    deviation = supabase.table("dd_deviations").select("*").eq("id", str(deviation_id)).execute()
    if not deviation.data:
        raise HTTPException(status_code=404, detail="Deviation not found")

    dev = deviation.data[0]

    # Fetch linked audit trail
    audit_entry = None
    if dev.get("audit_trail_id"):
        a = supabase.table("audit_trail").select("*").eq("id", dev["audit_trail_id"]).execute()
        if a.data:
            audit_entry = a.data[0]

    return {**dev, "audit_trail": audit_entry}


@router.patch("/deviations/{deviation_id}")
async def review_deviation(deviation_id: UUID, review: DeviationReviewUpdate, user: User = Depends(get_current_user)):
    """Attorney reviews a deviation and makes a decision."""
    supabase = get_supabase()

    # Get existing deviation
    existing = supabase.table("dd_deviations").select("*").eq("id", str(deviation_id)).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Deviation not found")

    # Update with review decision
    result = (
        supabase.table("dd_deviations")
        .update({
            "review_decision": review.review_decision,
            "review_notes": review.review_notes,
            "reviewed_by": str(user.id),
            "reviewed_at": "now()",
        })
        .eq("id", str(deviation_id))
        .execute()
    )

    # Audit the review
    dev = existing.data[0]
    audit.record(
        client_id=UUID(dev["client_id"]),
        function_id=UUID(_get_function_id()),
        event_type="human_review",
        event_summary=f"Deviation {deviation_id} reviewed: {review.review_decision}",
        initiated_by=user.id,
        model_used="human",
    )

    return result.data[0] if result.data else {}
