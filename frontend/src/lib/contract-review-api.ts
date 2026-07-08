const API_BASE = process.env.NEXT_PUBLIC_MATTER_INTAKE_API_URL || "https://document-matter-intake-eval.fly.dev";

export interface ContractAnalysis {
  overall_score: number;
  overall_risk_level: "high" | "medium" | "low";
  clauses: {
    name: string;
    risk: "high" | "medium" | "low";
    score: number;
    reasoning: string;
  }[];
  obligations: {
    party: string;
    description: string;
    deadline: string;
  }[];
  recommendations: string[];
  processing_time_ms: number;
  model_used: string;
}

export async function analyzeContract(text: string): Promise<ContractAnalysis> {
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

  // Map matter-intake response to contract review shape
  return {
    overall_score: data.overall_score,
    overall_risk_level: data.overall_risk_level || (data.overall_score >= 70 ? "low" : data.overall_score >= 40 ? "medium" : "high"),
    clauses: (data.dimension_scores || []).map((d: any) => ({
      name: d.dimension_name,
      risk: d.score >= 70 ? "low" : d.score >= 40 ? "medium" : "high",
      score: d.score,
      reasoning: d.reasoning,
    })),
    obligations: data.staffing ? [{
      party: data.staffing.recommended_role || "Review required",
      description: data.staffing.reasoning || "",
      deadline: "Per contract terms",
    }] : [],
    recommendations: data.conflict_check?.detail
      ? [data.conflict_check.detail]
      : [],
    processing_time_ms: data.processing_time_ms || 0,
    model_used: data.model_used || "claude",
  };
}

export async function uploadContract(file: File): Promise<{ text: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Upload failed (${response.status}): ${errorText}`);
  }

  return response.json();
}
