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
  const reportFetched = useRef(false);

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
      } else if (ev.kind === 'sprint') {
        setLatest(p.metrics ?? {});
        setDone(p.seed_index !== undefined ? p.seed_index + 1 : done);
      } else if (ev.kind === 'seed') {
        if (p.spend !== undefined) setSpend(p.spend);
      } else if (ev.kind === 'report_ready' && !reportFetched.current) {
        reportFetched.current = true;
        fetch(`${SIM_API_BASE}/runs/${runId}/report`)
          .then((r) => (r.ok ? r.text() : Promise.reject()))
          .then(setReport)
          .catch(() => setError('report unavailable'));
      }
    };
    es.onerror = () => setError('connection to runner lost — reconnecting');
    return () => es.close();
  }, [runId, done]);

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
