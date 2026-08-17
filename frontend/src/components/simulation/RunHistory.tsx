'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Trash2 } from 'lucide-react';
import { SIM_API_BASE } from '@/lib/simulation-api';

interface Run {
  id: string;
  status: string;
  total_seeds: number;
  seeds_completed: number;
  spend: number;
  created_at: string;
}

const STATUS_LABEL: Record<string, string> = {
  queued: 'Queued',
  running: 'Running',
  optimizing: 'Optimizing',
  complete: 'Complete',
  budget_exhausted: 'Budget hit',
  error: 'Failed',
};

export default function RunHistory({ firmId }: { firmId: string }) {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${SIM_API_BASE}/runs?firm_id=${firmId}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => { setRuns(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [firmId]);

  async function onDelete(runId: string) {
    setDeleting(runId);
    try {
      const res = await fetch(`${SIM_API_BASE}/runs/${runId}`, { method: 'DELETE' });
      if (res.ok) setRuns((r) => r.filter((x) => x.id !== runId));
    } catch {
      /* leave the row in place on failure */
    } finally {
      setDeleting(null);
    }
  }

  if (loading) return <p style={{ color: 'var(--text-muted)' }}>Loading runs…</p>;
  if (runs.length === 0) return <p style={{ color: 'var(--text-muted)' }}>No runs yet — save the intake, then Run.</p>;

  return (
    <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {runs.map((run) => (
        <li key={run.id} className="card flex items-center">
          <Link
            href={`/simulation/firms/${firmId}/runs/${run.id}`}
            className="flex-1 p-3 flex items-center justify-between no-underline hover:border-[var(--primary)]"
          >
            <div>
              <div style={{ fontWeight: 600 }}>{new Date(run.created_at).toLocaleString()}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {run.seeds_completed}/{run.total_seeds} seeds · ${(run.spend ?? 0).toFixed(2)}
              </div>
            </div>
            <span className="badge">{STATUS_LABEL[run.status] ?? run.status}</span>
          </Link>
          <button
            onClick={() => onDelete(run.id)}
            disabled={deleting === run.id}
            className="p-3 text-[var(--text-muted)] hover:text-[var(--rose)] transition-colors disabled:opacity-40"
            title="Delete run"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </li>
      ))}
    </ul>
  );
}
