const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

// Get Supabase access token from localStorage (set by Supabase SDK)
function getAccessToken(): string | null {
  try {
    const stored = localStorage.getItem("sb-rkiaocarugdbcgtonfuq-auth-token");
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed.access_token || null;
    }
  } catch {}
  return null;
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error: ${res.status} ${res.statusText} — ${body}`);
  }
  return res.json();
}

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
