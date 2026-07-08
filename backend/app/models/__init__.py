"""
Legal AI OS — Core Pydantic Models

Mirrors the core schema (001_core_schema.sql).
Shared across all 8 functions.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MatterStatus(StrEnum):
    INTAKE = "intake"
    CONFLICT_CHECK = "conflict_check"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    CLOSED = "closed"
    REJECTED = "rejected"


class FunctionStatus(StrEnum):
    BUILT = "built"
    CONFIGURED = "configured"
    ROADMAP = "roadmap"
    DEPRECATED = "deprecated"


class AuditEventType(StrEnum):
    FUNCTION_INVOCATION = "function_invocation"
    ROUTER_CLASSIFICATION = "router_classification"
    EVALUATOR_REASONING = "evaluator_reasoning"
    PROGRAMMATIC_SCORE = "programmatic_score"
    HUMAN_OVERRIDE = "human_override"
    HUMAN_REVIEW = "human_review"
    ESCALATION = "escalation"
    CONFIGURATION_CHANGE = "configuration_change"


class DeviationSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ---------------------------------------------------------------------------
# Client & Organization
# ---------------------------------------------------------------------------

class ClientBase(BaseModel):
    name: str
    slug: str
    industry: str | None = None
    jurisdiction: str | None = None
    config: dict = Field(default_factory=dict)

class ClientCreate(ClientBase):
    pass

class Client(ClientBase):
    id: UUID
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PracticeGroupBase(BaseModel):
    client_id: UUID
    name: str
    slug: str
    description: str | None = None

class PracticeGroup(PracticeGroupBase):
    id: UUID
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# User Profile
# ---------------------------------------------------------------------------

class UserProfileBase(BaseModel):
    client_id: UUID
    display_name: str
    email: str | None = None
    role: str = "attorney"
    practice_group_ids: list[UUID] = Field(default_factory=list)

class UserProfile(UserProfileBase):
    id: UUID
    is_active: bool = True
    preferences: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Matters
# ---------------------------------------------------------------------------

class MatterBase(BaseModel):
    client_id: UUID
    practice_group_id: UUID
    name: str
    description: str | None = None
    matter_number: str | None = None
    jurisdiction: str | None = None
    practice_area: str | None = None
    billing_type: str | None = None
    estimated_hours: int | None = None
    estimated_budget: float | None = None
    client_contact: str | None = None
    adverse_parties: list[str] = Field(default_factory=list)
    key_dates: dict = Field(default_factory=dict)
    assigned_to: UUID | None = None

class MatterCreate(MatterBase):
    created_by: UUID

class Matter(MatterBase):
    id: UUID
    status: MatterStatus = MatterStatus.INTAKE
    intake_evaluation_id: UUID | None = None
    risk_level: str | None = None
    risk_score: int | None = None
    confidence: int | None = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Functions Registry
# ---------------------------------------------------------------------------

class FunctionBase(BaseModel):
    slug: str
    name: str
    description: str | None = None
    status: FunctionStatus = FunctionStatus.ROADMAP
    version: str = "0.1.0"

class Function(FunctionBase):
    id: UUID
    config_schema: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FunctionConfigBase(BaseModel):
    function_id: UUID
    client_id: UUID
    is_enabled: bool = False
    config: dict = Field(default_factory=dict)

class FunctionConfig(FunctionConfigBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TimeSavedBaseline(BaseModel):
    id: UUID
    function_id: UUID
    client_id: UUID | None = None
    baseline_seconds: int
    description: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Audit Trail
# ---------------------------------------------------------------------------

class AuditEntryBase(BaseModel):
    client_id: UUID
    matter_id: UUID | None = None
    function_id: UUID | None = None
    event_type: AuditEventType
    event_summary: str | None = None
    prompt_raw: str | None = None
    response_raw: str | None = None
    reasoning_chain: str | None = None
    dimension_scores: list[dict] | None = None
    overall_score: int | None = None
    rubric_snapshot: dict | None = None
    rubric_version: str | None = None
    model_used: str
    model_version: str | None = None
    provider: str | None = None
    temperature: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None
    processing_time_ms: int | None = None
    correlation_id: UUID | None = None
    initiated_by: UUID

class AuditEntry(AuditEntryBase):
    id: UUID
    overridden_by: UUID | None = None
    override_reason: str | None = None
    original_score: int | None = None
    parent_audit_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class MetricBase(BaseModel):
    client_id: UUID
    matter_id: UUID | None = None
    function_id: UUID
    audit_trail_id: UUID | None = None
    started_at: datetime
    completed_at: datetime
    processing_time_ms: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model_used: str
    human_time_equivalent_ms: int = 0
    time_saved_ms: int = 0
    result_quality: str | None = None
    confidence: int | None = None
    initiated_by: UUID
    practice_group_id: UUID | None = None
    tags: dict = Field(default_factory=dict)

class Metric(MetricBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# API request/response helpers
# ---------------------------------------------------------------------------

class PaginationParams(BaseModel):
    """Common pagination for list endpoints."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class PaginatedResponse(BaseModel):
    """Wrapper for paginated list responses."""
    items: list
    total: int
    page: int
    page_size: int
    pages: int
