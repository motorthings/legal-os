'use client';

import { useState, useEffect, useCallback } from 'react';
import { listPOCs, createPOC, updatePOC, type POCProject } from '@/lib/poc-api';
import { Plus, ChevronRight, CheckCircle, XCircle, AlertCircle, Clock, Beaker, MessageSquare, RefreshCw } from 'lucide-react';

const STATUSES = ['discovery', 'build', 'review', 'graduated', 'cancelled'] as const;
const STATUS_LABELS: Record<string, string> = {
  discovery: 'Discovery',
  build: 'Build',
  review: 'Review',
  graduated: 'Graduated',
  cancelled: 'Cancelled',
};
const STATUS_COLORS: Record<string, string> = {
  discovery: '#3b82f6',
  build: '#f59e0b',
  review: '#8b5cf6',
  graduated: '#22c55e',
  cancelled: '#6b7280',
};

export default function POCPipelinePage() {
  const [projects, setProjects] = useState<POCProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newType, setNewType] = useState('contract_review');
  const [newDesc, setNewDesc] = useState('');
  const [creating, setCreating] = useState(false);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listPOCs();
      setProjects(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await createPOC({
        name: newName.trim(),
        function_type: newType,
        description: newDesc.trim() || undefined,
      });
      setShowCreate(false);
      setNewName('');
      setNewDesc('');
      setNewType('contract_review');
      await fetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed');
    } finally {
      setCreating(false);
    }
  };

  const handleStatusChange = async (pocId: string, newStatus: string) => {
    try {
      await updatePOC(pocId, { status: newStatus });
      await fetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed');
    }
  };

  const projectsByStatus = (status: string) =>
    projects.filter((p) => p.status === status);

  if (loading) {
    return (
      <div>
        <header className="mb-6">
          <h1 className="text-4xl font-bold tracking-tight text-[var(--text)] mt-3 mb-2">POC Pipeline</h1>
          <p className="font-mono text-sm text-[var(--text-dim)]">Loading projects...</p>
        </header>
      </div>
    );
  }

  return (
    <div>
      <header className="mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-4xl font-bold tracking-tight text-[var(--text)] mt-3 mb-2">
              POC Pipeline
            </h1>
            <p className="font-mono text-sm text-[var(--text-dim)] max-w-xl">
              Discovery → Build → Review → Graduated. Track AI proof-of-concepts from idea to production.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetch}
              className="p-2 rounded-lg hover:opacity-80 transition-colors"
              style={{ background: 'var(--surface2)' }}
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4 text-[var(--text-dim)]" />
            </button>
            <button
              onClick={() => setShowCreate(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white bg-[var(--primary)] hover:opacity-90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              New POC
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="card p-4 mb-4 border-l-4 border-l-[var(--rose)]">
          <p className="text-sm text-[var(--rose)]">{error}</p>
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="card p-6 w-full max-w-lg mx-4">
            <h2 className="text-lg font-semibold text-[var(--text)] mb-4">New POC Project</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[var(--text-dim)] mb-1">Project Name</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g., AI Contract Review for Corporate M&A"
                  className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/50"
                  style={{ background: 'var(--surface2)' }}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--text-dim)] mb-1">Function Type</label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                  className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm text-[var(--text)] focus:outline-none"
                  style={{ background: 'var(--surface2)' }}
                >
                  <option value="contract_review">Contract Review</option>
                  <option value="due_diligence">Due Diligence</option>
                  <option value="matter_intake">Matter Intake & Triage</option>
                  <option value="regulatory_monitor">Regulatory Change Monitor</option>
                  <option value="km_search">KM & Precedent Search</option>
                  <option value="employment">Employment Legal Agents</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--text-dim)] mb-1">Description (optional)</label>
                <textarea
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Brief description of what this POC aims to prove..."
                  rows={3}
                  className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/50 resize-y"
                  style={{ background: 'var(--surface2)' }}
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 rounded-lg text-sm font-medium text-[var(--text-dim)] hover:text-[var(--text)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white bg-[var(--primary)] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {creating ? 'Creating...' : 'Create POC'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Kanban Board */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {STATUSES.map((status) => {
          const items = projectsByStatus(status);
          const color = STATUS_COLORS[status];
          return (
            <div key={status}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ background: color }} />
                  <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-dim)]">
                    {STATUS_LABELS[status]}
                  </span>
                </div>
                <span className="text-xs font-mono text-[var(--text-muted)]">{items.length}</span>
              </div>
              <div className="space-y-2">
                {items.map((project) => (
                  <div
                    key={project.id}
                    className="card p-3 cursor-pointer hover:border-[var(--primary)]/30 transition-colors"
                    style={{ borderLeft: `3px solid ${color}` }}
                  >
                    <div className="text-sm font-medium text-[var(--text)] mb-1">{project.name}</div>
                    <div className="text-[10px] text-[var(--text-muted)] font-mono mb-2">
                      {project.function_type.replace(/_/g, ' ')}
                    </div>
                    {project.target_completion && (
                      <div className="flex items-center gap-1 text-[10px] text-[var(--text-muted)] mb-2">
                        <Clock className="w-3 h-3" />
                        {project.target_completion}
                      </div>
                    )}
                    {/* Status advance buttons */}
                    <div className="flex gap-1 mt-2 pt-2 border-t border-[var(--border)]">
                      {status === 'discovery' && (
                        <button
                          onClick={(e) => { e.stopPropagation(); handleStatusChange(project.id, 'build'); }}
                          className="flex-1 text-[10px] px-2 py-1 rounded text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-[var(--surface2)] transition-colors"
                        >
                          Start Build →
                        </button>
                      )}
                      {status === 'build' && (
                        <>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleStatusChange(project.id, 'discovery'); }}
                            className="text-[10px] px-2 py-1 rounded text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
                          >
                            ← Back
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleStatusChange(project.id, 'review'); }}
                            className="flex-1 text-[10px] px-2 py-1 rounded text-[var(--text-dim)] hover:text-[var(--text)] hover:bg-[var(--surface2)] transition-colors"
                          >
                            To Review →
                          </button>
                        </>
                      )}
                      {status === 'review' && (
                        <>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleStatusChange(project.id, 'build'); }}
                            className="text-[10px] px-2 py-1 rounded text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
                          >
                            ← Back
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleStatusChange(project.id, 'graduated'); }}
                            className="flex-1 text-[10px] px-2 py-1 rounded text-[var(--text-dim)] hover:text-[#22c55e] hover:bg-[var(--surface2)] transition-colors"
                          >
                            Graduate ✓
                          </button>
                        </>
                      )}
                      {status === 'graduated' && (
                        <div className="flex items-center gap-1 text-[10px] text-[#22c55e]">
                          <CheckCircle className="w-3 h-3" /> Live
                        </div>
                      )}
                      {status === 'cancelled' && (
                        <div className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
                          <XCircle className="w-3 h-3" /> Cancelled
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {items.length === 0 && (
                  <div className="text-center py-6 text-xs text-[var(--text-muted)]">
                    No projects
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
