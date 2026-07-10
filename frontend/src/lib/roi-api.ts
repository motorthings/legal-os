const API_BASE = process.env.NEXT_PUBLIC_LEGAL_OS_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ROISummary {
  period: { start: string | null; end: string | null };
  summary: {
    total_invocations: number;
    total_hours_saved: number;
    total_cost_avoided_usd: number;
    total_ai_cost_usd: number;
    net_roi_usd: number;
    roi_ratio: number | null;
    hourly_rate_usd: number;
  };
  by_function: FunctionROI[];
}

export interface FunctionROI {
  function_id: string;
  slug: string;
  name: string;
  invocations: number;
  hours_saved: number;
  cost_avoided_usd: number;
  ai_cost_usd: number;
  net_roi_usd: number;
}

export interface QualitySummary {
  total_reviews: number;
  accuracy_rate: number | null;
  override_rate: number | null;
  false_positive_rate: number | null;
  false_negative_rate: number | null;
  avg_agreement_score: number | null;
  correct_count?: number;
  minor_issues_count?: number;
  major_issues_count?: number;
  incorrect_count?: number;
}

export interface AdoptionRate {
  eligible_count: number;
  active_count: number;
  adoption_pct: number;
  period_days: number;
}

export interface Baseline {
  function_id: string;
  client_id: string | null;
  baseline_seconds: number;
  methodology: string | null;
  calibrated_by: string | null;
  calibrated_at: string | null;
  sample_size: number | null;
  confidence_level: string;
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

export async function getROISummary(
  periodDays: number = 90,
): Promise<ROISummary> {
  const response = await fetch(
    `${API_BASE}/api/roi/summary?period_days=${periodDays}`,
    { credentials: "include" },
  );
  if (!response.ok) {
    throw new Error(`ROI summary failed (${response.status})`);
  }
  return response.json();
}

export async function getQualitySummary(
  periodDays: number = 90,
): Promise<QualitySummary> {
  const response = await fetch(
    `${API_BASE}/api/roi/quality/summary?period_days=${periodDays}`,
    { credentials: "include" },
  );
  if (!response.ok) {
    throw new Error(`Quality summary failed (${response.status})`);
  }
  return response.json();
}

export async function getAdoptionRate(
  practiceGroupId?: string,
  periodDays: number = 30,
): Promise<AdoptionRate> {
  const params = new URLSearchParams({ period_days: String(periodDays) });
  if (practiceGroupId) params.set("practice_group_id", practiceGroupId);
  const response = await fetch(
    `${API_BASE}/api/roi/adoption?${params}`,
    { credentials: "include" },
  );
  if (!response.ok) {
    throw new Error(`Adoption rate failed (${response.status})`);
  }
  return response.json();
}

export async function getBaselines(): Promise<Baseline[]> {
  const response = await fetch(
    `${API_BASE}/api/roi/baselines`,
    { credentials: "include" },
  );
  if (!response.ok) {
    throw new Error(`Baselines failed (${response.status})`);
  }
  return response.json();
}

export async function updateBaseline(
  functionId: string,
  baselineSeconds: number,
  methodology?: string,
  sampleSize?: number,
  confidenceLevel?: string,
): Promise<any> {
  const params = new URLSearchParams({
    baseline_seconds: String(baselineSeconds),
  });
  if (methodology) params.set("methodology", methodology);
  if (sampleSize) params.set("sample_size", String(sampleSize));
  if (confidenceLevel) params.set("confidence_level", confidenceLevel);
  params.set("reason", "Manual calibration");

  const response = await fetch(
    `${API_BASE}/api/roi/baselines/${functionId}?${params}`,
    { method: "PUT", credentials: "include" },
  );
  if (!response.ok) {
    throw new Error(`Update baseline failed (${response.status})`);
  }
  return response.json();
}
