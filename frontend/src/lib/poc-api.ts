const API_BASE = process.env.NEXT_PUBLIC_LEGAL_OS_API_URL || "http://localhost:8000";

export interface POCProject {
  id: string;
  name: string;
  description?: string;
  function_type: string;
  status: "discovery" | "build" | "review" | "graduated" | "cancelled";
  champion_id?: string;
  practice_group_id?: string;
  target_completion?: string;
  started_at?: string;
  completed_at?: string;
  notes?: string;
  feedback?: POCFeedback[];
  created_at: string;
  updated_at: string;
}

export interface POCFeedback {
  id: string;
  poc_project_id: string;
  author_id: string;
  feedback_type: "bug" | "feature_request" | "usability" | "accuracy" | "general";
  body: string;
  resolved: boolean;
  created_at: string;
}

export async function listPOCs(
  status?: string,
  practiceGroupId?: string,
): Promise<POCProject[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (practiceGroupId) params.set("practice_group_id", practiceGroupId);
  const response = await fetch(
    `${API_BASE}/api/poc-pipeline/?${params}`,
    { credentials: "include" },
  );
  if (!response.ok) throw new Error(`List POCs failed (${response.status})`);
  return response.json();
}

export async function getPOC(pocId: string): Promise<POCProject> {
  const response = await fetch(
    `${API_BASE}/api/poc-pipeline/${pocId}`,
    { credentials: "include" },
  );
  if (!response.ok) throw new Error(`Get POC failed (${response.status})`);
  return response.json();
}

export async function createPOC(data: {
  name: string;
  function_type: string;
  description?: string;
  champion_id?: string;
  practice_group_id?: string;
  target_completion?: string;
}): Promise<POCProject> {
  const params = new URLSearchParams();
  params.set("name", data.name);
  params.set("function_type", data.function_type);
  if (data.description) params.set("description", data.description);
  if (data.champion_id) params.set("champion_id", data.champion_id);
  if (data.practice_group_id) params.set("practice_group_id", data.practice_group_id);
  if (data.target_completion) params.set("target_completion", data.target_completion);

  const response = await fetch(
    `${API_BASE}/api/poc-pipeline/?${params}`,
    { method: "POST", credentials: "include" },
  );
  if (!response.ok) throw new Error(`Create POC failed (${response.status})`);
  return response.json();
}

export async function updatePOC(
  pocId: string,
  updates: { status?: string; name?: string; description?: string; notes?: string },
): Promise<POCProject> {
  const params = new URLSearchParams();
  if (updates.status) params.set("status", updates.status);
  if (updates.name) params.set("name", updates.name);
  if (updates.description !== undefined) params.set("description", updates.description);
  if (updates.notes !== undefined) params.set("notes", updates.notes);

  const response = await fetch(
    `${API_BASE}/api/poc-pipeline/${pocId}?${params}`,
    { method: "PATCH", credentials: "include" },
  );
  if (!response.ok) throw new Error(`Update POC failed (${response.status})`);
  return response.json();
}
