"""
Legal AI OS — Due Diligence Models
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import DeviationSeverity


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DDProjectStatus(StrEnum):
    DRAFT = "draft"
    UPLOADING = "uploading"
    ANALYZING = "analyzing"
    REVIEW = "review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class DDDocumentStatus(StrEnum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    REVIEWED = "reviewed"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Deal Projects
# ---------------------------------------------------------------------------

class DDProjectBase(BaseModel):
    client_id: UUID
    practice_group_id: UUID
    matter_id: UUID | None = None
    name: str
    description: str | None = None
    deal_type: str | None = None
    counterparty: str | None = None
    jurisdiction: str | None = None

class DDProjectCreate(DDProjectBase):
    created_by: UUID
    target_standards: list["TargetStandardCreate"] = Field(default_factory=list)

class DDProject(DDProjectBase):
    id: UUID
    status: DDProjectStatus = DDProjectStatus.DRAFT
    document_count: int = 0
    deviation_count: int = 0
    critical_count: int = 0
    created_by: UUID
    assigned_to: UUID | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Target Standards
# ---------------------------------------------------------------------------

class TargetStandardBase(BaseModel):
    category: str
    standard_text: str | None = None
    acceptable_values: list[str] = Field(default_factory=list)
    severity: str = "medium"

class TargetStandardCreate(TargetStandardBase):
    pass

class TargetStandard(TargetStandardBase):
    id: UUID
    project_id: UUID
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class DDDocumentBase(BaseModel):
    project_id: UUID
    client_id: UUID
    filename: str
    file_size_bytes: int | None = None
    file_type: str | None = None

class DDDocument(DDDocumentBase):
    id: UUID
    status: DDDocumentStatus = DDDocumentStatus.PENDING
    storage_path: str | None = None
    extracted_text: str | None = None
    extracted_at: datetime | None = None
    analyzed_at: datetime | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Deviations
# ---------------------------------------------------------------------------

class DeviationBase(BaseModel):
    document_id: UUID
    project_id: UUID
    client_id: UUID
    clause_type: str
    clause_text: str | None = None
    clause_location: str | None = None
    target_standard_id: UUID | None = None
    expected_text: str | None = None
    severity: DeviationSeverity
    deviation_summary: str | None = None
    detailed_analysis: str | None = None
    recommendation: str | None = None
    clause_group_key: str | None = None
    confidence: int | None = None

class DeviationReviewUpdate(BaseModel):
    """Attorney reviews a deviation and makes a decision."""
    review_decision: str        # 'accept_risk' | 'must_fix' | 'noted' | 'false_positive'
    review_notes: str | None = None
    reviewed_by: UUID

class Deviation(DeviationBase):
    id: UUID
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    review_decision: str | None = None
    review_notes: str | None = None
    audit_trail_id: UUID | None = None
    model_used: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Batch analysis request
# ---------------------------------------------------------------------------

class DDAnalyzeRequest(BaseModel):
    """Trigger batch analysis of all pending documents in a project."""
    project_id: UUID
    initiated_by: UUID

class DDAnalyzeResponse(BaseModel):
    project_id: UUID
    documents_queued: int
    status: str


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

class DDProjectReport(BaseModel):
    project_id: UUID
    project_name: str
    deal_type: str | None
    project_status: str
    document_count: int
    total_deviations: int
    critical: int
    high: int
    medium: int
    low: int
    unreviewed: int
    unique_clause_issues: int
    first_deviation_at: datetime | None
    last_deviation_at: datetime | None

    model_config = {"from_attributes": True}
