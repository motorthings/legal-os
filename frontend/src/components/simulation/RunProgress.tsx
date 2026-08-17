'use client';

import { useEffect, useRef, useState } from 'react';
import { SIM_API_BASE } from '@/lib/simulation-api';

interface Props {
  runId: string;
}

const HEADLINE: { key: string; label: string; fmt: (v: number) => string }[] = [
  { key: 'ppp', label: 'Profit per partner', fmt: (v) => `$${(v / 1_000_000).toFixed(2)}M` },
  { key: 'matter_profit_margin', label: 'Matter margin', fmt: (v) => `${v.toFixed(1)}%` },
  { key: 'realization_rate', label: 'Realization rate', fmt: (v) => `${v.toFixed(1)}%` },
  { key: 'associate_attrition', label: 'Associate attrition', fmt: (v) => `${v.toFixed(1)}%` },
];

const STATUS_TEXT: Record<string, string> = {
  queued: 'Queued',
  running: 'Running the simulation…',
  generating_report: 'Generating your report…',
  complete: 'Complete',
  budget_exhausted: 'Budget hit — showing what completed',
  error: 'Failed',
};

function describeSprint(p: any): string {
  const m = p.metrics ?? {};
  const ai = m.ai_assisted_matter_pct;
  const rework = m.redline_rework_rate;
  const ppp = m.ppp;
  const margin = m.matter_profit_margin;
  const scenario = (p.seed_index ?? 0) + 1;
  const parts: string[] = [];
  if (ai != null) parts.push(`AI drafting ${Math.round(ai)}% of matters`);
  if (rework != null) parts.push(`partners rewriting ${Math.round(rework)}% of drafts`);
  if (ppp != null) parts.push(`profit per partner $${(ppp / 1e6).toFixed(2)}M`);
  if (margin != null) parts.push(`margin ${margin.toFixed(1)}%`);
  return `scenario ${scenario} · month ${p.sprint}: ${parts.join(' · ') || 'working…'}`;
}

export default function RunProgress({ runId }: Props) {
  const [status, setStatus] = useState('queued');
  const [done, setDone] = useState(0);
  const [total, setTotal] = useState(0);
  const [spend, setSpend] = useState(0);
  const [latest, setLatest] = useState<Record<string, number>>({});
  const [report, setReport] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [log, setLog] = useState<string[]>([]);
  const reportFetched = useRef(false);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const es = new EventSource(`${SIM_API_BASE}/runs/${runId}/events`);
    es.onmessage = (e) => {
      let ev: any;
      try {
        ev = JSON.parse(e.data);
      } catch {
        return; // keep-alive comment
      }
      const p = ev.payload ?? {};
      if (ev.kind === 'status') {
        setStatus(p.status);
        if (p.seeds_completed !== undefined) setDone(p.seeds_completed);
        if (p.total_seeds !== undefined) setTotal(p.total_seeds);
        if (p.spend !== undefined) setSpend(p.spend);
        setLog((l) => [...l, `→ ${STATUS_TEXT[p.status] ?? p.status}${p.total_seeds ? ` (${p.total_seeds} scenarios)` : ''}`]);
      } else if (ev.kind === 'sprint') {
        setLatest(p.metrics ?? {});
        setLog((l) => [...l, describeSprint(p)]);
      } else if (ev.kind === 'seed') {
        if (p.spend !== undefined) setSpend(p.spend);
        if (p.seed_index !== undefined) setDone(p.seed_index + 1);
        setLog((l) => [...l, `✓ scenario ${(p.seed_index ?? 0) + 1} complete`]);
      } else if (ev.kind === 'report_ready' && !reportFetched.current) {
        reportFetched.current = true;
        setLog((l) => [...l, '✓ report ready']);
        fetch(`${SIM_API_BASE}/runs/${runId}/report`)
          .then((r) => (r.ok ? r.text() : Promise.reject()))
          .then(setReport)
          .catch(() => setError('report unavailable'));
      }
    };
    es.onerror = () => setError('connection to runner lost — reconnecting');
    return () => es.close();
  }, [runId]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  const finished = status === 'complete' || status === 'budget_exhausted';

  return (
    <div>
      <p className="text-[15px]">
        <strong>{STATUS_TEXT[status] ?? status}</strong>
        {status === 'running' && total > 0 && (
          <span className="text-[var(--text-dim)]"> · {done} of {total} scenarios complete</span>
        )}
        {spend > 0 && <span className="text-[var(--text-dim)]"> · ${spend.toFixed(2)} spent</span>}
      </p>
      <div style={{ height: 8, background: '#eee', borderRadius: 4 }}>
        <div style={{ height: '100%', width: `${pct}%`, background: '#4c9aff', borderRadius: 4 }} />
      </div>
      {Object.keys(latest).length > 0 && (
        <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', margin: '1rem 0' }}>
          {HEADLINE.filter((m) => latest[m.key] !== undefined).map((m) => (
            <div key={m.key}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{m.label}</div>
              <strong style={{ fontSize: '1.15rem' }}>{m.fmt(latest[m.key])}</strong>
            </div>
          ))}
        </div>
      )}
      {error && <p style={{ color: '#b8860b' }}>{error}</p>}
      {log.length > 0 && (
        <div className="mt-4 border border-[var(--border)] rounded-lg overflow-hidden">
          <div className="px-3 py-2 border-b border-[var(--border)] font-mono text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            Live trace
          </div>
          <div ref={logRef} className="p-3 font-mono text-[11px] leading-relaxed text-[var(--text-dim)] bg-[var(--surface2)] overflow-auto max-h-72 whitespace-pre-wrap">
            {log.join('\n')}
          </div>
        </div>
      )}
      {report ? (
        <pre style={{ whiteSpace: 'pre-wrap', border: '1px solid #eee', padding: '1rem', background: '#fafafa' }}>
          {report}
        </pre>
      ) : finished && !report ? (
        <p style={{ color: '#888' }}>No report (run did not complete a primary seed).</p>
      ) : (
        <p style={{ color: '#888' }}>Running…</p>
      )}
    </div>
  );
}
