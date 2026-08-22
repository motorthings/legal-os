'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { SIM_API_BASE } from '@/lib/simulation-api';

interface DivergenceRow {
  prediction_id: string;
  run_id: string | null;
  metric: string;
  predicted_value: number | null;
  band_low: number | null;
  band_high: number | null;
  horizon_sprints: number | null;
  config_hash: string | null;
  predicted_at: string | null;
  actual_value: number | null;
  source: string | null;
  error: number | null;
  pct_error: number | null;
  in_band: boolean;
  recorded_at: string | null;
}

// The honest record: what the model predicted vs what actually happened. A prediction with
// no outcome yet is "awaiting outcome", not a miss — only a recorded actual can say wrong.
function fmtMoney(v: number | null): string {
  return v == null ? '—' : `$${(v / 1_000_000).toFixed(2)}M`;
}

function fmtPct(v: number | null): string {
  return v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`;
}

export default function DivergencePage() {
  const params = useParams<{ id: string }>();
  const firmId = params.id;
  const [rows, setRows] = useState<DivergenceRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recording, setRecording] = useState<string | null>(null);
  const [inputs, setInputs] = useState<Record<string, string>>({});

  const load = useCallback(() => {
    fetch(`${SIM_API_BASE}/firms/${firmId}/divergence`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((data: DivergenceRow[]) => { setRows(data); setError(null); })
      .catch(() => setError('could not load the validation record'))
      .finally(() => setLoading(false));
  }, [firmId]);

  useEffect(() => { load(); }, [load]);

  const validated = rows.filter((r) => r.actual_value != null);
  const inBand = validated.filter((r) => r.in_band).length;
  const coverage = validated.length ? (inBand / validated.length) * 100 : null;

  async function recordOutcome(row: DivergenceRow) {
    const raw = inputs[row.prediction_id];
    const value = Number(raw);
    if (!raw || Number.isNaN(value)) return;
    setRecording(row.prediction_id);
    try {
      const res = await fetch(`${SIM_API_BASE}/runs/${row.run_id}/outcomes`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ metric: row.metric, actual_value: value, source: 'manual' }),
      });
      if (!res.ok) setError('failed to record the outcome');
      load();
    } catch {
      setError('failed to record the outcome');
    } finally {
      setRecording(null);
    }
  }

  return (
    <main style={{ maxWidth: 960, margin: '0 auto', padding: '2rem 1rem' }}>
      <Link href={`/simulation/firms/${firmId}`} style={{ color: '#888', textDecoration: 'none' }}>← Back to firm</Link>
      <h1 className="text-2xl font-bold text-[var(--text)] tracking-tight mt-2">Validation</h1>
      <p className="text-sm text-[var(--text-muted)] mt-1">
        What the model predicted vs what actually happened. Record the real result when it&apos;s known — this page shows, honestly, where the model was right and where it was wrong.
      </p>

      {loading ? (
        <p style={{ color: 'var(--text-muted)', marginTop: '1.5rem' }}>Loading validation record…</p>
      ) : error ? (
        <p style={{ color: 'var(--rose)', marginTop: '1.5rem' }}>{error}</p>
      ) : rows.length === 0 ? (
        <div className="card p-4 mt-4">
          <p className="text-sm text-[var(--text-muted)]">
            No predictions recorded yet. Run a lever optimization — it records the recommendation
            as a falsifiable prediction. Then when the result is known, record the actual here to
            build the validation record.
          </p>
        </div>
      ) : (
        <>
          <div className="card p-4 mt-4 flex flex-wrap gap-6">
            <div>
              <div className="text-[11px] uppercase tracking-wider text-[var(--text-muted)]">Predictions</div>
              <strong className="text-xl text-[var(--text)]">{rows.length}</strong>
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-wider text-[var(--text-muted)]">Validated</div>
              <strong className="text-xl text-[var(--text)]">{validated.length}</strong>
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-wider text-[var(--text-muted)]">Landed in band</div>
              <strong className="text-xl text-[var(--text)]">{coverage == null ? '—' : `${coverage.toFixed(0)}%`}</strong>
            </div>
          </div>

          <div className="mt-4 space-y-3">
            {rows.map((row) => {
              const awaiting = row.actual_value == null;
              const statusColor = awaiting ? 'var(--text-muted)' : row.in_band ? '#10b981' : 'var(--rose)';
              const statusLabel = awaiting ? 'awaiting outcome' : row.in_band ? 'in band' : 'out of band';
              const bigError = row.pct_error != null && Math.abs(row.pct_error) > 20;
              return (
                <div key={row.prediction_id} className="card p-4">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full text-white"
                          style={{ backgroundColor: statusColor }}>
                      {statusLabel}
                    </span>
                    <span className="font-medium text-[var(--text)]">{row.metric.toUpperCase()}</span>
                    <span className="ml-auto text-[11px] font-mono text-[var(--text-muted)]">
                      {row.predicted_at ? new Date(row.predicted_at).toLocaleDateString() : ''}
                      {' · '}{row.horizon_sprints ?? '?'} sprints
                    </span>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-6 text-sm">
                    <div>
                      <div className="text-[11px] text-[var(--text-muted)]">Predicted</div>
                      <strong className="text-[var(--text)]">{fmtMoney(row.predicted_value)}</strong>
                    </div>
                    <div>
                      <div className="text-[11px] text-[var(--text-muted)]">Band</div>
                      <span className="text-[var(--text-dim)]">{fmtMoney(row.band_low)} – {fmtMoney(row.band_high)}</span>
                    </div>
                    <div>
                      <div className="text-[11px] text-[var(--text-muted)]">Actual</div>
                      <strong className="text-[var(--text)]">{fmtMoney(row.actual_value)}</strong>
                    </div>
                    <div>
                      <div className="text-[11px] text-[var(--text-muted)]">Error</div>
                      <span style={{ color: bigError ? 'var(--rose)' : 'inherit' }}>{fmtPct(row.pct_error)}</span>
                    </div>
                  </div>

                  {awaiting && row.run_id && (
                    <form className="mt-3 flex items-center gap-2" onSubmit={(e) => { e.preventDefault(); recordOutcome(row); }}>
                      <input
                        type="number" step="any" placeholder="actual value ($)"
                        value={inputs[row.prediction_id] ?? ''}
                        onChange={(e) => setInputs((s) => ({ ...s, [row.prediction_id]: e.target.value }))}
                        className="w-44 px-2 py-1 text-[13px] rounded-md"
                      />
                      <button type="submit" disabled={recording === row.prediction_id}
                              className="btn-primary border-none cursor-pointer px-3 py-1 text-[13px] disabled:opacity-50">
                        {recording === row.prediction_id ? 'Recording…' : 'Record outcome'}
                      </button>
                    </form>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </main>
  );
}
