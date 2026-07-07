"""Pydantic request/response models for the Matter Intake Evaluator."""

from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    matter_summary: str = Field(..., min_length=1, max_length=50000)


class PracticeAreaScore(BaseModel):
    practice_area: str
    confidence: int  # 0-100
    reasoning: str


class UrgencyRiskScore(BaseModel):
    urgency_level: str  # "immediate" | "short-term" | "routine"
    risk_level: str  # "high" | "medium" | "low"
    risk_score: int  # 0-100
    reasoning: str


class ConflictEntry(BaseModel):
    entity_name: str | None = None
    conflict_type: str  # "direct_adverse" | "business_conflict" | "none_identified"
    detail: str


class StaffingRecommendation(BaseModel):
    recommended_role: str
    estimated_hours: int
    reasoning: str


class DataIntegrityScore(BaseModel):
    completeness: int  # 0-100
    clarity: int  # 0-100
    issues: list[str]


class DimensionScore(BaseModel):
    dimension_name: str
    score: int  # 0-100
    weight: float  # e.g., 0.25
    reasoning: str


class EvaluateResponse(BaseModel):
    overall_score: int  # 0-100 (programmatic weighted)
    overall_risk_level: str  # "high" | "medium" | "low"

    practice_area: PracticeAreaScore
    urgency_risk: UrgencyRiskScore
    conflict_check: ConflictEntry
    staffing: StaffingRecommendation
    data_integrity: DataIntegrityScore

    dimension_scores: list[DimensionScore]

    processing_time_ms: int
    model_used: str
