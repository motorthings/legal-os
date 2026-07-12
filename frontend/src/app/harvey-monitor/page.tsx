'use client';

import { useState, useEffect } from 'react';
import {
  getAgents, getEvaluations, getDriftAlerts, getMonitoringSummary,
  runEvaluation, checkDrift, acknowledgeAlert, createAgent,
  type HarveyAgent, type HarveyEvaluation, type DriftAlert, type MonitoringSummary,
} from '@/lib/harvey-api';
import {
  Shield, Activity, AlertTriangle, CheckCircle, XCircle,
  BarChart3, Plus, RefreshCw, Brain, Eye, Clock,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreColor(score: number | null): string {
  if (score === null) return 'var(--text-muted)';
  if (score >= 90) return '#22c55e';
  if (score >= 80) return '#f59e0b';
  if (score >= 75) return '#f97316';
  return '#ef4444';
}

function certBadge(level: string | null): { bg: string; text: string } {
  switch (level) {
    case 'Platinum': return { bg: 'rgba(168,85,247,0.15)', text: '#c084fc' };
    case 'Gold': return { bg: 'rgba(250,204,21,0.15)', text: '#facc15' };
    case 'Silver': return { bg: 'rgba(148,163,184,0.15)', text: '#94a3b8' };
    case 'Bronze': return { bg: 'rgba(251,146,60,0.15)', text: '#fb923c' };
    default: return { bg: 'rgba(100,116,139,0.1)', text: 'var(--text-muted)' };
  }
}

function driftColor(score: number | null): string {
  if (score === null) return 'var(--text-muted)';
  if (score <= 10) return '#22c55e';
  if (score <= 25) return '#a3e635';
  if (score <= 50) return '#f59e0b';
  if (score <= 75) return '#f97316';
  return '#ef4444';
}

function severityColor(severity: string): string {
  switch (severity) {
    case 'critical': return '#ef4444';
    case 'high': return '#f97316';
    case 'moderate': return '#f59e0b';
    case 'low': return '#22c55e';
    default: return 'var(--text-muted)';
  }
}

const AGENT_TYPE_LABELS: Record<string, string> = {
  contract_review: 'Contract Review',
  due_diligence: 'Due Diligence',
  legal_research: 'Legal Research',
  document_drafting: 'Document Drafting',
  regulatory_monitor: 'Regulatory Monitor',
  litigation_support: 'Litigation Support',
  knowledge_management: 'Knowledge Management',
  general_assistant: 'General Assistant',
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function HarveyMonitorPage() {
  const [summary, setSummary] = useState<MonitoringSummary | null>(null);
  const [agents, setAgents] = useState<HarveyAgent[]>([]);
  const [evaluations, setEvaluations] = useState<HarveyEvaluation[]>([]);
  const [alerts, setAlerts] = useState<DriftAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Eval modal state
  const [showEval, setShowEval] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [evalPrompt, setEvalPrompt] = useState('');
  const [evalResponse, setEvalResponse] = useState('');
  const [evalRunning, setEvalRunning] = useState(false);
  const [evalResult, setEvalResult] = useState<any>(null);

  // Create agent modal
  const [showCreate, setShowCreate] = useState(false);
  const [newAgent, setNewAgent] = useState({ name: '', agent_type: 'general_assistant', system_prompt: '', evaluation_schedule: 'weekly' });
  const [creating, setCreating] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, agentsData, evalsData, alertsData] = await Promise.all([
        getMonitoringSummary(),
        getAgents(),
        getEvaluations({ limit: 20 }),
        getDriftAlerts({ acknowledged: false }),
      ]);
      setSummary(summaryData);
      setAgents(agentsData.agents);
      setEvaluations(evalsData.evaluations);
      setAlerts(alertsData.alerts);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load monitoring data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleRunEvaluation = async () => {
    if (!selectedAgent || !evalPrompt || !evalResponse) return;
    setEvalRunning(true);
    try {
      const result = await runEvaluation({
        harvey_agent_id: selectedAgent,
        user_prompt: evalPrompt,
        harvey_response: evalResponse,
      });
      setEvalResult(result);
      fetchData(); // refresh
    } catch (err) {
      setEvalResult({ error: err instanceof Error ? err.message : 'Evaluation failed' });
    } finally {
      setEvalRunning(false);
    }
  };

  const handleDriftCheck = async (agentId: string) => {
    const agent = agents.find(a => a.id === agentId);
    if (!agent) return;
    const response = prompt('Paste Harvey response to check for drift:', '');
    if (!response) return;
    try {
      await checkDrift({ harvey_agent_id: agentId, harvey_response: response });
      fetchData();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Drift check failed');
    }
  };

  const handleCreateAgent = async () => {
    if (!newAgent.name) return;
    setCreating(true);
    try {
      await createAgent(newAgent);
      setShowCreate(false);
      setNewAgent({ name: '', agent_type: 'general_assistant', system_prompt: '', evaluation_schedule: 'weekly' });
      fetchData();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Create failed');
    } finally {
      setCreating(false);
    }
  };

  const handleAcknowledge = async (alertId: string) => {
    await acknowledgeAlert(alertId);
    fetchData();
  };

  // ------------------------------------------------------------------
  // Loading / Error states
  // ------------------------------------------------------------------

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-[var(--text-muted)]" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
          <h1 className="text-2xl font-bold text-[var(--text)]" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>
            Harvey Agent Monitoring
          </h1>
        </header>
        <div className="p-6 rounded-xl border border-[var(--rose-dim)] bg-[rgba(239,68,68,0.05)]">
          <div className="flex items-center gap-3 mb-2">
            <XCircle className="w-5 h-5 text-[var(--rose)]" />
            <span className="font-semibold text-[var(--rose)]">Connection Error</span>
          </div>
          <p className="text-sm text-[var(--text-dim)]">{error}</p>
          <p className="text-xs text-[var(--text-muted)] mt-2">
            Make sure the backend is running at {process.env.NEXT_PUBLIC_LEGAL_OS_API_URL || 'http://localhost:8080'} and the harvey_monitoring tables have been migrated.
          </p>
          <button
            onClick={fetchData}
            className="mt-4 px-4 py-2 rounded-lg text-sm font-medium bg-[var(--surface2)] text-[var(--text)] hover:bg-[var(--border)] transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  const avgScores = summary?.evaluations.average_scores;

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text)]" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>
            Harvey Agent Monitoring
          </h1>
          <p className="text-sm text-[var(--text-dim)] mt-1">
            Independent evaluation layer — accuracy, safety, bias, compliance scoring with drift detection
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-[var(--primary)] text-white hover:opacity-90 transition-opacity"
          >
            <Plus className="w-4 h-4" />
            Register Agent
          </button>
          <button
            onClick={() => setShowEval(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-[var(--border)] text-[var(--text)] hover:bg-[var(--surface2)] transition-colors"
          >
            <Brain className="w-4 h-4" />
            Run Evaluation
          </button>
        </div>
      </header>

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="rounded-xl border border-[var(--border)] p-4 bg-[var(--surface)]">
          <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider mb-2">
            <Shield className="w-3.5 h-3.5" />
            Agents
          </div>
          <div className="text-2xl font-bold text-[var(--text)]">{summary?.agents.active ?? 0}</div>
          <div className="text-xs text-[var(--text-dim)] mt-1">of {summary?.agents.total ?? 0} registered</div>
        </div>

        <div className="rounded-xl border border-[var(--border)] p-4 bg-[var(--surface)]">
          <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider mb-2">
            <Activity className="w-3.5 h-3.5" />
            Avg Score
          </div>
          <div className="text-2xl font-bold" style={{ color: scoreColor(avgScores?.final ?? null) }}>
            {avgScores?.final?.toFixed(1) ?? '—'}
          </div>
          <div className="text-xs text-[var(--text-dim)] mt-1">
            {summary?.evaluations.non_drift ?? 0} evaluations
          </div>
        </div>

        <div className="rounded-xl border border-[var(--border)] p-4 bg-[var(--surface)]">
          <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider mb-2">
            <AlertTriangle className="w-3.5 h-3.5" />
            Drift Alerts
          </div>
          <div className="text-2xl font-bold" style={{ color: (summary?.alerts.unacknowledged ?? 0) > 0 ? '#ef4444' : '#22c55e' }}>
            {summary?.alerts.unacknowledged ?? 0}
          </div>
          <div className="text-xs text-[var(--text-dim)] mt-1">unacknowledged</div>
        </div>

        <div className="rounded-xl border border-[var(--border)] p-4 bg-[var(--surface)]">
          <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider mb-2">
            <BarChart3 className="w-3.5 h-3.5" />
            Score Range
          </div>
          <div className="flex gap-2 text-xs">
            {['Platinum', 'Gold', 'Silver', 'Bronze'].map(level => {
              const badge = certBadge(level);
              return (
                <span key={level} className="px-1.5 py-0.5 rounded font-mono" style={{ background: badge.bg, color: badge.text }}>
                  {level[0]}
                </span>
              );
            })}
          </div>
          <div className="text-xs text-[var(--text-dim)] mt-1">certification tiers</div>
        </div>
      </div>

      {/* Score Breakdown */}
      {avgScores && (
        <div className="grid grid-cols-4 gap-3 mb-8">
          {(['accuracy', 'safety', 'bias', 'compliance'] as const).map(dim => (
            <div key={dim} className="rounded-lg border border-[var(--border)] p-3 text-center bg-[var(--surface)]">
              <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--text-muted)] mb-1">{dim}</div>
              <div className="text-lg font-bold" style={{ color: scoreColor(avgScores[dim] ?? null) }}>
                {avgScores[dim]?.toFixed(1) ?? '—'}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Main grid: Agents + Alerts */}
      <div className="grid gap-6" style={{ gridTemplateColumns: '1fr 1fr' }}>
        {/* Agent List */}
        <div>
          <h2 className="text-sm font-semibold text-[var(--text)] mb-3 flex items-center gap-2">
            <Eye className="w-4 h-4 text-[var(--text-muted)]" />
            Registered Agents
          </h2>
          {agents.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[var(--border)] p-8 text-center text-sm text-[var(--text-muted)]">
              <Brain className="w-8 h-8 mx-auto mb-3 opacity-30" />
              No Harvey agents registered yet.<br />
              <button onClick={() => setShowCreate(true)} className="text-[var(--primary)] hover:underline mt-1 inline-block">
                Register your first agent
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {agents.map(agent => (
                <div key={agent.id} className="rounded-lg border border-[var(--border)] p-3 bg-[var(--surface)]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-[var(--text)]">{agent.name}</span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                      agent.status === 'active' ? 'text-green-400 bg-green-400/10' :
                      agent.status === 'paused' ? 'text-amber-400 bg-amber-400/10' :
                      'text-slate-400 bg-slate-400/10'
                    }`}>{agent.status}</span>
                  </div>
                  <div className="text-xs text-[var(--text-dim)] mb-2">
                    {AGENT_TYPE_LABELS[agent.agent_type] || agent.agent_type} · {agent.evaluation_schedule}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => { setSelectedAgent(agent.id); setShowEval(true); }}
                      className="text-[10px] font-mono px-2 py-1 rounded bg-[var(--surface2)] text-[var(--text-dim)] hover:text-[var(--text)] transition-colors"
                    >
                      Evaluate
                    </button>
                    <button
                      onClick={() => handleDriftCheck(agent.id)}
                      className="text-[10px] font-mono px-2 py-1 rounded bg-[var(--surface2)] text-[var(--text-dim)] hover:text-[var(--text)] transition-colors"
                      disabled={!agent.system_prompt}
                      title={!agent.system_prompt ? 'No baseline prompt to compare against' : 'Check for behavioral drift'}
                    >
                      Drift Check
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Drift Alerts */}
        <div>
          <h2 className="text-sm font-semibold text-[var(--text)] mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-[var(--text-muted)]" />
            Active Drift Alerts
          </h2>
          {alerts.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[var(--border)] p-8 text-center text-sm text-[var(--text-muted)]">
              <CheckCircle className="w-8 h-8 mx-auto mb-3 opacity-30" style={{ color: '#22c55e' }} />
              No active drift alerts.<br />
              <span className="text-xs">Agents are operating within baseline parameters.</span>
            </div>
          ) : (
            <div className="space-y-2">
              {alerts.map(alert => (
                <div key={alert.id} className="rounded-lg border border-[var(--border)] p-3 bg-[var(--surface)]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono font-semibold" style={{ color: severityColor(alert.severity) }}>
                      {alert.severity.toUpperCase()}
                    </span>
                    <span className="text-[10px] text-[var(--text-muted)]">
                      {new Date(alert.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="text-sm text-[var(--text)] mb-2">{alert.summary}</div>
                  <button
                    onClick={() => handleAcknowledge(alert.id)}
                    className="text-[10px] font-mono px-2 py-1 rounded bg-[var(--surface2)] text-[var(--text-dim)] hover:text-[var(--text)] transition-colors"
                  >
                    Acknowledge
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Evaluations */}
      {evaluations.length > 0 && (
        <div className="mt-8">
          <h2 className="text-sm font-semibold text-[var(--text)] mb-3 flex items-center gap-2">
            <Clock className="w-4 h-4 text-[var(--text-muted)]" />
            Recent Evaluations
          </h2>
          <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--surface)]">
                  <th className="text-left p-3 text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider">Agent</th>
                  <th className="text-left p-3 text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider">Accuracy</th>
                  <th className="text-left p-3 text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider">Safety</th>
                  <th className="text-left p-3 text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider">Bias</th>
                  <th className="text-left p-3 text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider">Compliance</th>
                  <th className="text-left p-3 text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider">Certification</th>
                  <th className="text-left p-3 text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider">Date</th>
                </tr>
              </thead>
              <tbody>
                {evaluations.filter(e => !e.is_drift_check).slice(0, 10).map(e => {
                  const agentName = agents.find(a => a.id === e.harvey_agent_id)?.name || e.harvey_agent_id.slice(0, 8);
                  const badge = certBadge(e.certification_level);
                  return (
                    <tr key={e.id} className="border-b border-[var(--border)] hover:bg-[var(--surface)] transition-colors">
                      <td className="p-3 text-[var(--text)] font-mono text-xs">{agentName}</td>
                      <td className="p-3 font-mono" style={{ color: scoreColor(e.accuracy_score) }}>{e.accuracy_score ?? '—'}</td>
                      <td className="p-3 font-mono" style={{ color: scoreColor(e.safety_score) }}>{e.safety_score ?? '—'}</td>
                      <td className="p-3 font-mono" style={{ color: scoreColor(e.bias_score) }}>{e.bias_score ?? '—'}</td>
                      <td className="p-3 font-mono" style={{ color: scoreColor(e.compliance_score) }}>{e.compliance_score ?? '—'}</td>
                      <td className="p-3">
                        {e.certification_level ? (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded" style={{ background: badge.bg, color: badge.text }}>
                            {e.certification_level}
                          </span>
                        ) : '—'}
                      </td>
                      <td className="p-3 text-xs text-[var(--text-muted)]">
                        {new Date(e.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ================================================================ */}
      {/* Run Evaluation Modal */}
      {/* ================================================================ */}
      {showEval && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setShowEval(false)}>
          <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-[var(--text)] mb-4">Run Harvey Evaluation</h2>

            <div className="space-y-4">
              {/* Agent selector */}
              <div>
                <label className="block text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider mb-1">Agent</label>
                <select
                  value={selectedAgent}
                  onChange={e => setSelectedAgent(e.target.value)}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] px-3 py-2 text-sm"
                >
                  <option value="">Select agent...</option>
                  {agents.filter(a => a.status === 'active').map(a => (
                    <option key={a.id} value={a.id}>{a.name} ({AGENT_TYPE_LABELS[a.agent_type] || a.agent_type})</option>
                  ))}
                </select>
              </div>

              {/* User prompt */}
              <div>
                <label className="block text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider mb-1">Original User Prompt</label>
                <textarea
                  value={evalPrompt}
                  onChange={e => setEvalPrompt(e.target.value)}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] px-3 py-2 text-sm h-24 resize-none"
                  placeholder="Paste the original prompt sent to Harvey..."
                />
              </div>

              {/* Harvey response */}
              <div>
                <label className="block text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider mb-1">Harvey Response</label>
                <textarea
                  value={evalResponse}
                  onChange={e => setEvalResponse(e.target.value)}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] px-3 py-2 text-sm h-32 resize-none"
                  placeholder="Paste Harvey's response to evaluate..."
                />
              </div>

              {/* Action */}
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => { setShowEval(false); setEvalResult(null); }}
                  className="px-4 py-2 rounded-lg text-sm text-[var(--text-dim)] hover:text-[var(--text)] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRunEvaluation}
                  disabled={evalRunning || !selectedAgent || !evalPrompt || !evalResponse}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-[var(--primary)] text-white hover:opacity-90 disabled:opacity-40 transition-opacity"
                >
                  {evalRunning ? (
                    <><RefreshCw className="w-4 h-4 animate-spin" /> Evaluating...</>
                  ) : (
                    <><Brain className="w-4 h-4" /> Run Evaluation</>
                  )}
                </button>
              </div>
            </div>

            {/* Results */}
            {evalResult && !evalResult.error && (
              <div className="mt-6 p-4 rounded-lg border border-[var(--border)] bg-[var(--bg)]">
                <h3 className="text-sm font-semibold text-[var(--text)] mb-3">Evaluation Results</h3>
                <div className="grid grid-cols-5 gap-3 text-center">
                  {(['accuracy', 'safety', 'bias', 'compliance'] as const).map(dim => (
                    <div key={dim}>
                      <div className="text-[10px] font-mono uppercase text-[var(--text-muted)] mb-1">{dim}</div>
                      <div className="text-lg font-bold" style={{ color: scoreColor(evalResult.scores?.[dim]) }}>
                        {evalResult.scores?.[dim] ?? '—'}
                      </div>
                    </div>
                  ))}
                  <div>
                    <div className="text-[10px] font-mono uppercase text-[var(--text-muted)] mb-1">Final</div>
                    <div className="text-lg font-bold" style={{ color: scoreColor(evalResult.scores?.final) }}>
                      {evalResult.scores?.final ?? '—'}
                    </div>
                  </div>
                </div>
                {evalResult.scores?.certification && (
                  <div className="mt-3 text-center">
                    <span className="text-xs font-mono px-2 py-1 rounded" style={{
                      background: certBadge(evalResult.scores.certification).bg,
                      color: certBadge(evalResult.scores.certification).text,
                    }}>
                      {evalResult.scores.certification}
                    </span>
                    {evalResult.scores?.veto_triggered && (
                      <span className="ml-2 text-[10px] font-mono text-[var(--rose)]">VETO TRIGGERED</span>
                    )}
                  </div>
                )}
              </div>
            )}
            {evalResult?.error && (
              <div className="mt-4 p-3 rounded-lg bg-[rgba(239,68,68,0.1)] text-sm text-[var(--rose)]">
                {evalResult.error}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ================================================================ */}
      {/* Create Agent Modal */}
      {/* ================================================================ */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setShowCreate(false)}>
          <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-6 w-full max-w-lg" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-[var(--text)] mb-4">Register Harvey Agent</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider mb-1">Name</label>
                <input
                  type="text"
                  value={newAgent.name}
                  onChange={e => setNewAgent(p => ({ ...p, name: e.target.value }))}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] px-3 py-2 text-sm"
                  placeholder="e.g., Contract Review Agent v2"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider mb-1">Type</label>
                <select
                  value={newAgent.agent_type}
                  onChange={e => setNewAgent(p => ({ ...p, agent_type: e.target.value }))}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] px-3 py-2 text-sm"
                >
                  {Object.entries(AGENT_TYPE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider mb-1">Evaluation Schedule</label>
                <select
                  value={newAgent.evaluation_schedule}
                  onChange={e => setNewAgent(p => ({ ...p, evaluation_schedule: e.target.value }))}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] px-3 py-2 text-sm"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="biweekly">Biweekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="per_invocation">Per Invocation</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider mb-1">
                  Baseline System Prompt <span className="text-[var(--text-muted)]">(for drift detection)</span>
                </label>
                <textarea
                  value={newAgent.system_prompt}
                  onChange={e => setNewAgent(p => ({ ...p, system_prompt: e.target.value }))}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--text)] px-3 py-2 text-sm h-24 resize-none font-mono"
                  placeholder="Paste Harvey agent's system prompt to establish a baseline..."
                />
              </div>

              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setShowCreate(false)}
                  className="px-4 py-2 rounded-lg text-sm text-[var(--text-dim)] hover:text-[var(--text)] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateAgent}
                  disabled={creating || !newAgent.name}
                  className="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--primary)] text-white hover:opacity-90 disabled:opacity-40 transition-opacity"
                >
                  {creating ? 'Creating...' : 'Register Agent'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
