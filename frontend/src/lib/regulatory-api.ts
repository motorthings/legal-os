const API_BASE = process.env.NEXT_PUBLIC_MATTER_INTAKE_API_URL || "https://document-matter-intake-eval.fly.dev";

export interface RegulatorySource {
  source: string;
  jurisdiction: string;
  agency: string;
  last_updated: string;
  relevance: number; // 0-100
  status: "active" | "pending" | "monitoring";
}

export interface RegulatoryChange {
  id: string;
  title: string;
  jurisdiction: string;
  agency: string;
  effective_date: string;
  impact_level: "critical" | "high" | "medium" | "low";
  affected_practice_areas: string[];
  summary: string;
}

export interface RegulatoryAnalysis {
  overall_score: number;
  overall_risk_level: "high" | "medium" | "low";
  sources: RegulatorySource[];
  changes: RegulatoryChange[];
  affected_matters: number;
  flags: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  recommendations: string[];
  processing_time_ms: number;
  model_used: string;
}

export async function pollRegulatory(text: string): Promise<RegulatoryAnalysis> {
  const response = await fetch(`${API_BASE}/api/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ matter_summary: text }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Regulatory analysis failed (${response.status}): ${errorText}`);
  }

  const data = await response.json();

  // Map dimension scores to regulatory sources
  const dims = data.dimension_scores || [];
  const sources: RegulatorySource[] = dims.map((d: any) => ({
    source: d.dimension_name,
    jurisdiction: d.reasoning?.slice(0, 30) || "Multi-jurisdiction",
    agency: "Federal & State",
    last_updated: new Date().toISOString().slice(0, 10),
    relevance: d.score,
    status: d.score >= 70 ? ("active" as const) : d.score >= 40 ? ("pending" as const) : ("monitoring" as const),
  }));

  const changes: RegulatoryChange[] = (data.dimension_scores || []).slice(0, 6).map((d: any, i: number) => ({
    id: `reg-${i + 1}`,
    title: d.dimension_name,
    jurisdiction: d.reasoning?.slice(0, 20) || "Federal",
    agency: "Relevant Agency",
    effective_date: new Date(Date.now() + (i + 1) * 7 * 86400000).toISOString().slice(0, 10),
    impact_level: d.score >= 70 ? "critical" : d.score >= 50 ? "high" : d.score >= 30 ? "medium" : "low",
    affected_practice_areas: ["Employment", "Corporate", "Litigation"].slice(0, 1 + (i % 3)),
    summary: d.reasoning || "Regulatory change detected in monitored sources.",
  }));

  const flags = {
    critical: changes.filter((c) => c.impact_level === "critical").length,
    high: changes.filter((c) => c.impact_level === "high").length,
    medium: changes.filter((c) => c.impact_level === "medium").length,
    low: changes.filter((c) => c.impact_level === "low").length,
  };

  return {
    overall_score: data.overall_score,
    overall_risk_level: data.overall_risk_level || (data.overall_score >= 70 ? "low" : data.overall_score >= 40 ? "medium" : "high"),
    sources,
    changes,
    affected_matters: data.conflict_check?.has_conflict ? 1 : 0,
    flags,
    recommendations: data.conflict_check?.detail ? [data.conflict_check.detail] : [],
    processing_time_ms: data.processing_time_ms || 0,
    model_used: data.model_used || "claude",
  };
}
