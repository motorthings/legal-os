const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export interface DDProject {
  id: string;
  name: string;
  description?: string;
  deal_type?: string;
  counterparty?: string;
  status: string;
  document_count: number;
  deviation_count: number;
  critical_count: number;
  created_at: string;
}

export interface DDDocument {
  id: string;
  filename: string;
  file_type?: string;
  status: string;
  extracted_text?: string;
  analyzed_at?: string;
}

export interface DDDeviation {
  id: string;
  clause_type: string;
  clause_text?: string;
  clause_location?: string;
  severity: "critical" | "high" | "medium" | "low";
  deviation_summary?: string;
  detailed_analysis?: string;
  recommendation?: string;
  review_decision?: string;
  review_notes?: string;
  confidence?: number;
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

// Health
export const getHealth = () => fetchAPI<{ status: string }>("/health");

// DD Projects
export const getProjects = () =>
  fetchAPI<DDProject[]>("/api/due-diligence/projects");

export const getProject = (id: string) =>
  fetchAPI<DDProject & { target_standards: any[]; documents: DDDocument[] }>(
    `/api/due-diligence/projects/${id}`
  );

export const createProject = (data: {
  client_id: string;
  practice_group_id: string;
  name: string;
  description?: string;
  deal_type?: string;
  counterparty?: string;
  created_by: string;
}) => fetchAPI<DDProject>("/api/due-diligence/projects", {
  method: "POST",
  body: JSON.stringify(data),
});

// DD Deviations
export const getDeviations = (projectId: string) =>
  fetchAPI<{ summary: any; deviations: DDDeviation[] }>(
    `/api/due-diligence/projects/${projectId}/report`
  );

export const reviewDeviation = (
  deviationId: string,
  data: { review_decision: string; review_notes?: string; reviewed_by: string }
) =>
  fetchAPI<DDDeviation>(`/api/due-diligence/deviations/${deviationId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
