/** TypeScript interfaces matching backend Pydantic models. */

export interface PracticeAreaScore {
  practice_area: string;
  confidence: number;
  reasoning: string;
}

export interface UrgencyRiskScore {
  urgency_level: "immediate" | "short-term" | "routine";
  risk_level: "high" | "medium" | "low";
  risk_score: number;
  reasoning: string;
}

export interface ConflictEntry {
  entity_name: string | null;
  conflict_type: "direct_adverse" | "business_conflict" | "none_identified";
  detail: string;
}

export interface StaffingRecommendation {
  recommended_role: string;
  estimated_hours: number;
  reasoning: string;
}

export interface DataIntegrityScore {
  completeness: number;
  clarity: number;
  issues: string[];
}

export interface DimensionScore {
  dimension_name: string;
  score: number;
  weight: number;
  reasoning: string;
}

export interface EvaluateResponse {
  overall_score: number;
  overall_risk_level: "high" | "medium" | "low";
  practice_area: PracticeAreaScore;
  urgency_risk: UrgencyRiskScore;
  conflict_check: ConflictEntry;
  staffing: StaffingRecommendation;
  data_integrity: DataIntegrityScore;
  dimension_scores: DimensionScore[];
  processing_time_ms: number;
  model_used: string;
}

export type AppState =
  | { status: "empty" }
  | { status: "loading" }
  | { status: "error"; error: string }
  | { status: "success"; data: EvaluateResponse };
