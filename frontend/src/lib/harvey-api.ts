const API_BASE = process.env.NEXT_PUBLIC_LEGAL_OS_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface HarveyAgent {
  id: string;
  name: string;
  agent_type: string;
  harvey_agent_id: string | null;
  system_prompt: string | null;
  evaluation_schedule: string;
  status: 'active' | 'paused' | 'retired';
  baseline_snapshot_at: string;
  created_at: string;
  updated_at: string;
}

export interface HarveyEvaluation {
  id: string;
  harvey_agent_id: string;
  user_prompt: string;
  harvey_response: string;
  accuracy_score: number | null;
  safety_score: number | null;
  bias_score: number | null;
  compliance_score: number | null;
  final_score: number | null;
  certification_level: 'Platinum' | 'Gold' | 'Silver' | 'Bronze' | null;
  veto_triggered: boolean;
  is_drift_check: boolean;
  drift_score: number | null;
  status: string;
  created_at: string;
  completed_at: string | null;
}

export interface DriftAlert {
  id: string;
  harvey_agent_id: string;
  severity: 'low' | 'moderate' | 'high' | 'critical';
  summary: string;
  acknowledged: boolean;
  created_at: string;
}

export interface MonitoringSummary {
  agents: {
    total: number;
    active: number;
    by_type: Record<string, number>;
    by_status: Record<string, number>;
  };
  evaluations: {
    total_recent: number;
    non_drift: number;
    average_scores: {
      accuracy: number | null;
      safety: number | null;
      bias: number | null;
      compliance: number | null;
      final: number | null;
    };
  };
  alerts: {
    unacknowledged: number;
    by_severity: Record<string, number>;
  };
}

// ---------------------------------------------------------------------------
// Agents
// ---------------------------------------------------------------------------

export async function getAgents(params?: {
  client_id?: string;
  status?: string;
  agent_type?: string;
}): Promise<{ agents: HarveyAgent[]; count: number }> {
  const searchParams = new URLSearchParams();
  if (params?.client_id) searchParams.set('client_id', params.client_id);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.agent_type) searchParams.set('agent_type', params.agent_type);

  const url = `${API_BASE}/api/harvey-monitor/agents${searchParams.toString() ? '?' + searchParams : ''}`;
  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) throw new Error(`Failed to fetch agents (${response.status})`);
  return response.json();
}

export async function getAgent(agentId: string): Promise<HarveyAgent> {
  const response = await fetch(`${API_BASE}/api/harvey-monitor/agents/${agentId}`, { credentials: 'include' });
  if (!response.ok) throw new Error(`Failed to fetch agent (${response.status})`);
  return response.json();
}

export async function createAgent(data: {
  name: string;
  agent_type: string;
  harvey_agent_id?: string;
  system_prompt?: string;
  evaluation_schedule?: string;
  client_id?: string;
}): Promise<HarveyAgent> {
  const response = await fetch(`${API_BASE}/api/harvey-monitor/agents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(`Failed to create agent (${response.status})`);
  return response.json();
}

export async function updateAgent(agentId: string, data: {
  name?: string;
  system_prompt?: string;
  evaluation_schedule?: string;
  status?: string;
}): Promise<HarveyAgent> {
  const response = await fetch(`${API_BASE}/api/harvey-monitor/agents/${agentId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(`Failed to update agent (${response.status})`);
  return response.json();
}

export async function deleteAgent(agentId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/harvey-monitor/agents/${agentId}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!response.ok) throw new Error(`Failed to delete agent (${response.status})`);
}

// ---------------------------------------------------------------------------
// Evaluations
// ---------------------------------------------------------------------------

export async function runEvaluation(data: {
  harvey_agent_id: string;
  user_prompt: string;
  harvey_response: string;
  context?: string;
  is_drift_check?: boolean;
}): Promise<{ evaluation: HarveyEvaluation; scores: Record<string, any> }> {
  const response = await fetch(`${API_BASE}/api/harvey-monitor/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(`Evaluation failed (${response.status})`);
  return response.json();
}

export async function getEvaluations(params?: {
  harvey_agent_id?: string;
  limit?: number;
}): Promise<{ evaluations: HarveyEvaluation[]; count: number }> {
  const searchParams = new URLSearchParams();
  if (params?.harvey_agent_id) searchParams.set('harvey_agent_id', params.harvey_agent_id);
  if (params?.limit) searchParams.set('limit', String(params.limit));

  const url = `${API_BASE}/api/harvey-monitor/evaluations${searchParams.toString() ? '?' + searchParams : ''}`;
  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) throw new Error(`Failed to fetch evaluations (${response.status})`);
  return response.json();
}

export async function getEvaluation(evaluationId: string): Promise<HarveyEvaluation> {
  const response = await fetch(`${API_BASE}/api/harvey-monitor/evaluations/${evaluationId}`, { credentials: 'include' });
  if (!response.ok) throw new Error(`Failed to fetch evaluation (${response.status})`);
  return response.json();
}

// ---------------------------------------------------------------------------
// Drift Detection
// ---------------------------------------------------------------------------

export async function checkDrift(data: {
  harvey_agent_id: string;
  harvey_response: string;
}): Promise<any> {
  const response = await fetch(`${API_BASE}/api/harvey-monitor/drift-check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(`Drift check failed (${response.status})`);
  return response.json();
}

export async function getDriftAlerts(params?: {
  harvey_agent_id?: string;
  severity?: string;
  acknowledged?: boolean;
  limit?: number;
}): Promise<{ alerts: DriftAlert[]; count: number }> {
  const searchParams = new URLSearchParams();
  if (params?.harvey_agent_id) searchParams.set('harvey_agent_id', params.harvey_agent_id);
  if (params?.severity) searchParams.set('severity', params.severity);
  if (params?.acknowledged !== undefined) searchParams.set('acknowledged', String(params.acknowledged));
  if (params?.limit) searchParams.set('limit', String(params.limit));

  const url = `${API_BASE}/api/harvey-monitor/drift-alerts${searchParams.toString() ? '?' + searchParams : ''}`;
  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) throw new Error(`Failed to fetch drift alerts (${response.status})`);
  return response.json();
}

export async function acknowledgeAlert(alertId: string): Promise<DriftAlert> {
  const response = await fetch(`${API_BASE}/api/harvey-monitor/drift-alerts/${alertId}/acknowledge`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) throw new Error(`Failed to acknowledge alert (${response.status})`);
  return response.json();
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

export async function getMonitoringSummary(): Promise<MonitoringSummary> {
  const response = await fetch(`${API_BASE}/api/harvey-monitor/summary`, { credentials: 'include' });
  if (!response.ok) throw new Error(`Failed to fetch monitoring summary (${response.status})`);
  return response.json();
}
