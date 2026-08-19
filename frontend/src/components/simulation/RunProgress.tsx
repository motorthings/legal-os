'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronRight } from 'lucide-react';
import { SIM_API_BASE } from '@/lib/simulation-api';
import MetricsCharts from './MetricsCharts';

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
  optimizing: 'Running the optimization…',
  complete: 'Complete',
  budget_exhausted: 'Budget hit — showing what completed',
  error: 'Failed',
};

interface Report {
  id: string;
  stage: 'baseline' | 'lever_optimization' | 'scenario_simulation';
  title: string;
  lever_set: string[];
  report_markdown: string;
  created_at: string;
}

// The three named stages, in the order they happen. Badge colors make the stack scannable.
const STAGE_META: Record<Report['stage'], { label: string; color: string }> = {
  baseline: { label: 'Baseline', color: 'var(--text-muted)' },
  lever_optimization: { label: 'Lever Optimization', color: 'var(--primary)' },
  scenario_simulation: { label: 'Scenario Simulation', color: '#10b981' },
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
  const [reportDone, setReportDone] = useState(0);
  const [reportTotal, setReportTotal] = useState(0);
  const [progressLabel, setProgressLabel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [log, setLog] = useState<string[]>([]);
  const [reconnecting, setReconnecting] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [reports, setReports] = useState<Report[]>([]);
  const maxSeqRef = useRef(0);
  const logRef = useRef<HTMLDivElement>(null);
  const reportRef = useRef<HTMLDivElement>(null);

  // Load every saved report for this run (baseline, lever optimization, scenario sims),
  // newest first. This is the source of truth for what's on screen — each stage is its own
  // saved report, so nothing clobbers anything.
  const loadReports = useCallback(() => {
    fetch(`${SIM_API_BASE}/runs/${runId}/reports`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((rs: Report[]) => {
        setReports(rs);
        if (rs.length > 0) setReport(rs[0].report_markdown);
      })
      .catch(() => {});
  }, [runId]);

  // Reconcile against the run's actual state on mount. The report used to be reachable
  // ONLY through a live `report_ready` event, so any missed event — a torn-down
  // EventSource, a remount after a hydration error, or simply opening a run that had
  // already finished — left the page waiting forever on something that had already
  // happened. Asking the server what is true is what a manual refresh was doing by hand.
  useEffect(() => {
    let cancelled = false;
    fetch(`${SIM_API_BASE}/runs/${runId}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((run) => {
        if (cancelled) return;
        setStatus(run.status);
        if (run.total_seeds !== undefined) setTotal(run.total_seeds);
        if (run.seeds_completed !== undefined) setDone(run.seeds_completed);
        if (run.spend !== undefined) setSpend(run.spend);
        if (run.has_report) loadReports();
      })
      .catch(() => {}); // SSE replay is the fallback
    return () => {
      cancelled = true;
    };
  }, [runId, loadReports]);

  useEffect(() => {
    const es = new EventSource(`${SIM_API_BASE}/runs/${runId}/events`);
    es.onmessage = (e) => {
      let ev: any;
      try {
        ev = JSON.parse(e.data);
      } catch {
        return; // keep-alive comment
      }
      if (ev.seq !== undefined) {
        if (ev.seq <= maxSeqRef.current) return; // already seen — replay after a reconnect
        maxSeqRef.current = ev.seq;
      }
      const p = ev.payload ?? {};
      if (ev.kind === 'status') {
        setStatus(p.status);
        if (p.status === 'error') {
          setOptimizing(false);
          setError(p.error || 'run failed');
        }
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
      } else if (ev.kind === 'progress') {
        setLog((l) => [...l, `… ${p.message}`]);
        setProgressLabel(p.message);
        if (typeof p.done === 'number' && typeof p.total === 'number') {
          setReportDone(p.done);
          setReportTotal(p.total);
        }
      } else if (ev.kind === 'report_ready') {
        setLog((l) => [...l, '✓ report ready']);
        setOptimizing(false);
        loadReports();
      }
    };
    es.onerror = () => setReconnecting(true);
    es.onopen = () => setReconnecting(false);
    return () => es.close();
  }, [runId, loadReports]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  useEffect(() => {
    if (report && reportRef.current) reportRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [report]);

  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  const finished = status === 'complete' || status === 'budget_exhausted';
  const active = status === 'queued' || status === 'running' || status === 'generating_report' || status === 'optimizing';

  const hasBaseline = reports.some((r) => r.stage === 'baseline');
  const optimization = reports.find((r) => r.stage === 'lever_optimization');

  async function onOptimize() {
    setOptimizing(true);
    setReportDone(0);
    setReportTotal(0);
    setProgressLabel(null);
    await fetch(`${SIM_API_BASE}/runs/${runId}/optimize`, { method: 'POST' });
  }

  async function onScenario() {
    setOptimizing(true);
    setReportDone(0);
    setReportTotal(0);
    setProgressLabel(null);
    await fetch(`${SIM_API_BASE}/runs/${runId}/scenario`, { method: 'POST' });
  }

  return (
    <div>
      <p className="text-[15px] flex items-center gap-2">
        {active && (
          <span className="inline-block w-3 h-3 rounded-full border-2 border-[var(--primary)] border-t-transparent animate-spin shrink-0" />
        )}
        <strong>{STATUS_TEXT[status] ?? status}</strong>
        {status === 'running' && total > 0 && (
          <span className="text-[var(--text-dim)]"> · {done} of {total} scenarios complete</span>
        )}
        {spend > 0 && <span className="text-[var(--text-dim)]"> · ${spend.toFixed(2)} spent</span>}
      </p>
      {status === 'running' && (
        total > 0 ? (
          <div style={{ height: 8, background: 'var(--border)', borderRadius: 4 }}>
            <div style={{ height: '100%', width: `${pct}%`, background: 'var(--primary)', borderRadius: 4, transition: 'width 0.3s' }} />
          </div>
        ) : (
          <div style={{ height: 8, background: 'var(--border)', borderRadius: 4, overflow: 'hidden' }}>
            <div className="animate-pulse" style={{ height: '100%', width: '100%', background: 'var(--primary)', borderRadius: 4 }} />
          </div>
        )
      )}
      {(status === 'optimizing' || status === 'generating_report') && (
        <div className="mt-2">
          <div style={{ height: 8, background: 'var(--border)', borderRadius: 4, overflow: 'hidden' }}>
            <div
              className={reportTotal > 0 ? undefined : 'animate-pulse'}
              style={{
                height: '100%',
                width: reportTotal > 0 ? `${Math.round((reportDone / reportTotal) * 100)}%` : '100%',
                background: 'var(--primary)', borderRadius: 4, transition: 'width 0.3s',
              }}
            />
          </div>
          {progressLabel && (
            <p className="mt-1.5 text-[12px] font-mono text-[var(--text-dim)]">{progressLabel}</p>
          )}
        </div>
      )}
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
      <MetricsCharts runId={runId} />
      {reconnecting && (
        <p style={{ color: 'var(--amber)', fontSize: '0.8rem' }}>Reconnecting…</p>
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
      {reports.length > 0 ? (
        <div className="mt-6" ref={reportRef}>
          <h2 className="text-xl font-bold text-[var(--text)] mb-3">Reports</h2>
          <div className="space-y-3">
            {reports.map((r, i) => {
              const meta = STAGE_META[r.stage];
              return (
                <details
                  key={r.id}
                  open={i === 0}
                  className="group border border-[var(--border)] rounded-lg overflow-hidden"
                >
                  <summary className="flex items-center gap-3 cursor-pointer select-none px-4 py-3 bg-[var(--surface2)] list-none [&::-webkit-details-marker]:hidden">
                    <span
                      className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full text-white shrink-0"
                      style={{ backgroundColor: meta.color }}
                    >
                      {meta.label}
                    </span>
                    <span className="font-medium text-[var(--text)] truncate">{r.title}</span>
                    <span className="ml-auto text-[11px] font-mono text-[var(--text-muted)] shrink-0">
                      {new Date(r.created_at).toLocaleString()}
                    </span>
                    <ChevronRight className="w-4 h-4 text-[var(--text-dim)] transition-transform group-open:rotate-90 shrink-0" />
                  </summary>
                  <div className="report-body px-4 py-4">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      urlTransform={(url) => {
                        if (/^(metrics\.csv|decisions\.jsonl|trace\.jsonl|state\.json)$/.test(url)) {
                          return `${SIM_API_BASE}/runs/${runId}/files/${url}`;
                        }
                        return url;
                      }}
                    >
                      {r.report_markdown}
                    </ReactMarkdown>
                  </div>
                </details>
              );
            })}
          </div>

          {finished && !optimizing && (
            <div className="flex flex-wrap gap-3 mt-6">
              {hasBaseline && (
                <button onClick={onOptimize} className="btn-primary border-none cursor-pointer">
                  {optimization ? 'Re-run the lever optimization' : 'Find the best lever combination'}
                </button>
              )}
              {optimization && (
                <button
                  onClick={onScenario}
                  className="btn-secondary border border-[var(--border)] cursor-pointer px-4 py-2 rounded-lg font-medium"
                  title={`Run the Monte Carlo against ${optimization.lever_set.join(' + ') || 'no levers'} again`}
                >
                  Run scenario simulation ({optimization.lever_set.join(' + ') || 'no levers'})
                </button>
              )}
            </div>
          )}
        </div>
      ) : finished ? (
        <p style={{ color: 'var(--text-muted)' }}>No report (run did not complete a primary seed).</p>
      ) : (
        <p style={{ color: 'var(--text-muted)' }}>Generating report…</p>
      )}
    </div>
  );
}
