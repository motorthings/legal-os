'use client';

import { useEffect, useRef, useState } from 'react';
import { SIM_API_BASE } from '@/lib/simulation-api';

interface Props {
  runId: string;
}

const HEADLINE = ['ppp', 'matter_profit_margin', 'realization_rate', 'associate_attrition'];

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
        setLog((l) => [...l, `[status] ${p.status} · seeds ${p.seeds_completed ?? 0}/${p.total_seeds ?? 0} · $${(p.spend ?? 0).toFixed(2)}`]);
      } else if (ev.kind === 'sprint') {
        setLatest(p.metrics ?? {});
        setDone((d) => (p.seed_index !== undefined ? p.seed_index + 1 : d));
        const m = p.metrics ?? {};
        const ppp = m.ppp != null ? Math.round(m.ppp).toLocaleString() : '—';
        const margin = m.matter_profit_margin != null ? `${m.matter_profit_margin.toFixed(1)}%` : '—';
        const real = m.realization_rate != null ? `${m.realization_rate.toFixed(1)}%` : '—';
        setLog((l) => [...l, `seed ${p.seed} · sprint ${p.sprint} · ppp=${ppp} · margin=${margin} · realization=${real}`]);
      } else if (ev.kind === 'seed') {
        if (p.spend !== undefined) setSpend(p.spend);
        setLog((l) => [...l, `✓ seed ${p.seed} complete · $${(p.spend ?? 0).toFixed(2)}`]);
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
      <p>
        Status: <strong>{status}</strong> · seeds {done}/{total} ({pct}%) · spend ${spend.toFixed(2)}
      </p>
      <div style={{ height: 8, background: '#eee', borderRadius: 4 }}>
        <div style={{ height: '100%', width: `${pct}%`, background: '#4c9aff', borderRadius: 4 }} />
      </div>
      {Object.keys(latest).length > 0 && (
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', margin: '1rem 0' }}>
          {HEADLINE.filter((k) => latest[k] !== undefined).map((k) => (
            <div key={k}>
              <div style={{ color: '#888', fontSize: '0.8rem' }}>{k}</div>
              <strong>{Number(latest[k]).toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong>
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
