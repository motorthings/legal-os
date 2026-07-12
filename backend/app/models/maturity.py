"""
Legal AI OS — AI Maturity Assessment Models

Pydantic models for the maturity assessment pipeline.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Dimension & Gap models
# ---------------------------------------------------------------------------

class MaturityDimension(BaseModel):
    """A single scored dimension (1-5) with rationale."""
    key: str                              # e.g. "knowledge_management"
    name: str                             # e.g. "Knowledge Management & Precedent"
    score: int = Field(ge=1, le=5)
    rationale: str                        # evidence cited from documents


class StageGap(BaseModel):
    """What's missing to reach the next maturity level."""
    from_level: int
    to_level: int
    from_label: str
    to_label: str
    whats_missing: str
    what_it_unlocks: str


# ---------------------------------------------------------------------------
# Assessment models
# ---------------------------------------------------------------------------

class MaturityAssessmentBase(BaseModel):
    """Core assessment fields."""
    overall_level: int = Field(ge=1, le=5)
    overall_level_label: str
    bottleneck_dimension: str
    bottleneck_why: str
    bottleneck_what_this_means: str
    dimensions: list[MaturityDimension]
    stage_gaps: list[StageGap]
    summary: str


class MaturityAssessmentCreate(BaseModel):
    """Request to trigger a new assessment."""
    document_ids: list[UUID] = Field(default_factory=list, min_length=1)


class MaturityAssessment(MaturityAssessmentBase):
    """Full assessment record from the database."""
    id: UUID
    client_id: UUID
    version: int = 1
    document_count: int = 0
    document_ids: list[UUID] = Field(default_factory=list)
    cost_usd: float = 0.0
    created_by: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class MaturityAssessmentSummary(BaseModel):
    """Lightweight listing row."""
    id: UUID
    version: int
    overall_level: int
    overall_level_label: str
    bottleneck_dimension: str
    document_count: int
    cost_usd: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Document upload models
# ---------------------------------------------------------------------------

class MaturityDocumentResponse(BaseModel):
    """Response after uploading a document for maturity assessment."""
    id: UUID
    title: str
    document_type: str
    source_file: str | None = None
    chunk_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Governance contract models
# ---------------------------------------------------------------------------

class MaturityHealthResponse(BaseModel):
    function: str
    status: str
    version: str
    capabilities: list[str]


class MaturityMetricsResponse(BaseModel):
    function: str
    assessments_run: int
    total_documents_analyzed: int
    total_cost_usd: float


class MaturityTargetsResponse(BaseModel):
    function: str
    targets: dict
