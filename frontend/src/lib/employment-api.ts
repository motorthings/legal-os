const API_BASE = process.env.NEXT_PUBLIC_MATTER_INTAKE_API_URL || "https://document-matter-intake-eval.fly.dev";

export interface EmploymentAnalysis {
  overall_score: number;
  overall_risk_level: "high" | "medium" | "low";
  classification: {
    contractor_risk: number;
    exempt_risk: number;
    reasoning: string;
  };
  compliance: {
    dimension: string;
    score: number;
    risk: "high" | "medium" | "low";
    reasoning: string;
  }[];
  recommendations: string[];
  processing_time_ms: number;
  model_used: string;
}

export async function analyzeEmployment(text: string): Promise<EmploymentAnalysis> {
  const response = await fetch(`${API_BASE}/api/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ matter_summary: text }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Analysis failed (${response.status}): ${errorText}`);
  }

  const data = await response.json();

  return {
    overall_score: data.overall_score,
    overall_risk_level: data.overall_risk_level || (data.overall_score >= 70 ? "low" : data.overall_score >= 40 ? "medium" : "high"),
    classification: {
      contractor_risk: data.urgency_risk?.risk_score || 50,
      exempt_risk: data.overall_score ? 100 - data.overall_score : 50,
      reasoning: data.urgency_risk?.reasoning || "Classification analysis based on provided text.",
    },
    compliance: (data.dimension_scores || []).map((d: any) => ({
      dimension: d.dimension_name,
      score: d.score,
      risk: d.score >= 70 ? "low" : d.score >= 40 ? "medium" : "high",
      reasoning: d.reasoning,
    })),
    recommendations: data.conflict_check?.detail
      ? [data.conflict_check.detail]
      : [],
    processing_time_ms: data.processing_time_ms || 0,
    model_used: data.model_used || "claude",
  };
}
