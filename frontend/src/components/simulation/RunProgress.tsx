'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronRight, HelpCircle, Download, RotateCcw } from 'lucide-react';
import { SIM_API_BASE } from '@/lib/simulation-api';
import MetricsCharts from './MetricsCharts';
import SimulationHero from './SimulationHero';
import LeverImpactChart from './LeverImpactChart';
import HowItWorks from './HowItWorks';

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
  payload?: {
    baseline_ppp?: number;
    best_ppp?: number;
    best_delta?: number;
    best_combo?: string[];
    main_effects?: Record<string, { delta_ppp?: number }>;
    ppp_trajectory?: number[];
    baseline_trajectory?: number[];
  } | null;
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

// Split a report into its lead (title + bottom line), its story, and its appendices, so
// the money chart can sit between the answer and the narrative — title → answer → chart →
// story → evidence — instead of charts-first. The report writes "## Your firm" as the seam
// between the answer and the story, and "## Appendix X" as the seam into the evidence.
function splitReport(md: string): { lead: string; story: string; appendix: string | null } {
  const appendixMarker = '## Appendix ';
  const aIdx = md.indexOf(appendixMarker);
  const body = aIdx === -1 ? md : md.slice(0, aIdx);
  const appendix = aIdx === -1 ? null : md.slice(aIdx);

  const firmMarker = '## Your firm';
  const fIdx = body.indexOf(firmMarker);
  const lead = fIdx === -1 ? body : body.slice(0, fIdx).trimEnd();
  const story = fIdx === -1 ? '' : body.slice(fIdx);

  return { lead, story, appendix };
}

export default function RunProgress({ runId }: Props) {
  const router = useRouter();
  const pathname = usePathname();
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
  const [reportedPPP, setReportedPPP] = useState<number | null>(null);
  const [provider, setProvider] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [replayHash, setReplayHash] = useState<string | null>(null);
  const [replaying, setReplaying] = useState(false);
  const [modelVariance, setModelVariance] = useState<{ mode: string; low?: number; high?: number; count?: number } | null>(null);
  const [howOpen, setHowOpen] = useState(false);
  const [printId, setPrintId] = useState<string | null>(null);
  const np = printId ? 'no-print' : '';

  // Save-as-PDF for a single report. We isolate that card + the charts with print CSS,
  // force it open, let React paint, then open the browser's print dialog. The user picks
  // "Save as PDF" — no library, and the SVG charts render crisply.
  const printReport = useCallback((id: string) => {
    setPrintId(id);
    document.body.classList.add('printing');
    const cleanup = () => {
      document.body.classList.remove('printing');
      setPrintId(null);
      window.removeEventListener('afterprint', cleanup);
    };
    window.addEventListener('afterprint', cleanup);
    // Let the forced-open state and no-print classes paint before the dialog opens.
    setTimeout(() => window.print(), 250);
  }, []);
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
        if (run.provider !== undefined) setProvider(run.provider);
        if (run.replay_hash !== undefined) setReplayHash(run.replay_hash);
        if (run.model_variance !== undefined) setModelVariance(run.model_variance);
        if (run.has_report) loadReports();
      })
      .catch(() => {}); // SSE replay is the fallback
    return () => {
      cancelled = true;
    };
  }, [runId, loadReports]);

  useEffect(() => {
    fetch(`${SIM_API_BASE}/runs/${runId}/config`)
      .then((r) => (r.ok ? r.json() : null))
      .then((cfg) => {
        setReportedPPP(cfg?.firm?.baseline_ppp ?? null);
        if (cfg?.run?.model) setModel(cfg.run.model);
      })
      .catch(() => {});
  }, [runId]);

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
  const scenario = reports.find((r) => r.stage === 'scenario_simulation') ?? optimization;
  const scenarioPayload = scenario?.payload;
  const recovered = scenarioPayload?.best_ppp ?? null;
  const baseline = scenarioPayload?.baseline_ppp ?? null;
  // lever_set is stored alphabetically; the recommendation has its own order (flat fees
  // first). Re-order to match the report so the hero's "the move" line isn't misleading.
  const LEVER_ORDER = ['pricing', 'seams', 'comp', 'latency', 'leverage'];
  const heroLevers = LEVER_ORDER.filter((l) => (scenario?.lever_set ?? []).includes(l));

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

  async function onReplay() {
    setReplaying(true);
    setError(null);
    try {
      const res = await fetch(`${SIM_API_BASE}/runs/${runId}/replay`, { method: 'POST' });
      if (!res.ok) throw new Error('replay failed');
      const { run_id } = await res.json();
      // Swap the trailing run id in the current path, keep the firm.
      const base = pathname.substring(0, pathname.lastIndexOf('/'));
      router.push(`${base}/${run_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'replay failed');
    } finally {
      setReplaying(false);
    }
  }

  return (
    <div className="print-root">
      <div className={np}>
      <p className="text-[15px] flex items-center gap-2">
        {active && (
          <span className="inline-block w-3 h-3 rounded-full border-2 border-[var(--primary)] border-t-transparent animate-spin shrink-0" />
        )}
        <strong>{STATUS_TEXT[status] ?? status}</strong>
        {status === 'running' && total > 0 && (
          <span className="text-[var(--text-dim)]"> · {done} of {total} scenarios complete</span>
        )}
        {spend > 0 && <span className="text-[var(--text-dim)]"> · ${spend.toFixed(2)} spent</span>}
        {provider && (
          <span
            className="ml-auto text-[11px] font-mono px-2 py-0.5 rounded-full border"
            style={{
              color: provider === 'mock' ? 'var(--text-muted)' : 'var(--primary)',
              borderColor: 'var(--border)',
            }}
          >
            {provider === 'mock' ? 'mock · deterministic' : `${provider} · ${model ?? 'llm'}`}
          </span>
        )}
        {modelVariance && modelVariance.mode === 'llm' && (modelVariance.count ?? 0) >= 2 && (
          <span
            className="text-[11px] font-mono px-2 py-0.5 rounded-full border"
            title={`Model's own uncertainty: re-running the reasoning at different temperatures moved the headline from $${(modelVariance.low ?? 0).toLocaleString()} to $${(modelVariance.high ?? 0).toLocaleString()}`}
            style={{ color: 'var(--amber)', borderColor: 'var(--border)' }}
          >
            ±${((modelVariance.high ?? 0) - (modelVariance.low ?? 0)).toLocaleString()} model uncertainty
          </span>
        )}
        {finished && replayHash && (
          <button
            onClick={onReplay}
            disabled={replaying}
            title={`Replay hash ${replayHash} — re-run this exact config, provider, and seed count`}
            className="flex items-center gap-1.5 text-[11px] font-mono px-2 py-0.5 rounded-full border cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed no-print"
            style={{ borderColor: 'var(--border)', color: 'var(--text-dim)' }}
          >
            <RotateCcw className="w-3 h-3" />
            {replaying ? 'Re-running…' : `↻ replay ${replayHash}`}
          </button>
        )}
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
      </div>
      <div className={np}>
        <SimulationHero
          reportedPPP={reportedPPP}
          baseline={baseline}
          recovered={recovered}
          levers={heroLevers}
        />
      </div>
      <div className={np}>
      {reconnecting && (
        <p style={{ color: 'var(--amber)', fontSize: '0.8rem' }}>Reconnecting…</p>
      )}
      {error && <p style={{ color: '#b8860b' }}>{error}</p>}
      {log.length > 0 && (
        <details
          className="group mt-4 border border-[var(--border)] rounded-lg overflow-hidden"
          onToggle={(e) => {
            if ((e.target as HTMLDetailsElement).open && logRef.current) {
              logRef.current.scrollTop = logRef.current.scrollHeight;
            }
          }}
        >
          <summary className="cursor-pointer select-none px-3 py-2 bg-[var(--surface2)] font-mono text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)] list-none [&::-webkit-details-marker]:hidden flex items-center gap-2">
            <ChevronRight className="w-4 h-4 text-[var(--text-dim)] transition-transform group-open:rotate-90 shrink-0" />
            Live trace
            <span className="ml-auto font-normal normal-case text-[var(--text-dim)]">{log.length} events</span>
          </summary>
          <div ref={logRef} className="p-3 font-mono text-[11px] leading-relaxed text-[var(--text-dim)] bg-[var(--surface2)] overflow-auto max-h-72 whitespace-pre-wrap">
            {log.join('\n')}
          </div>
        </details>
      )}
      </div>
      {reports.length > 0 ? (
        <div className="mt-6" ref={reportRef}>
          <div className={`flex items-center justify-between mb-3 ${np}`}>
            <h2 className="text-xl font-bold text-[var(--text)]">Reports</h2>
            <button
              onClick={() => setHowOpen(true)}
              className="flex items-center gap-1.5 text-[13px] text-[var(--text-dim)] hover:text-[var(--text)] cursor-pointer"
            >
              <HelpCircle className="w-4 h-4" />
              How this works
            </button>
          </div>
          <div className="space-y-3">
            {reports.map((r, i) => {
              const meta = STAGE_META[r.stage];
              const { lead, story, appendix } = splitReport(r.report_markdown);
              const ref = r.payload?.best_ppp;
              return (
                <details
                  key={r.id}
                  data-report-card
                  open={printId ? printId === r.id : i === 0}
                  className={`group border border-[var(--border)] rounded-lg overflow-hidden ${printId && printId !== r.id ? 'no-print' : ''}`}
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
                      {lead}
                    </ReactMarkdown>
                    <MetricsCharts
                      runId={runId}
                      baseline={r.payload?.baseline_trajectory}
                      recommended={r.payload?.ppp_trajectory}
                      reference={ref != null ? { value: ref, label: 'Recommended' } : undefined}
                    />
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      urlTransform={(url) => {
                        if (/^(metrics\.csv|decisions\.jsonl|trace\.jsonl|state\.json)$/.test(url)) {
                          return `${SIM_API_BASE}/runs/${runId}/files/${url}`;
                        }
                        return url;
                      }}
                    >
                      {story}
                    </ReactMarkdown>
                    <LeverImpactChart effects={r.payload?.main_effects} />
                    {appendix && (
                      <details className="appendix-toggle group mt-6 border border-[var(--border)] rounded-lg overflow-hidden" open={printId === r.id}>
                        <summary className="cursor-pointer select-none px-4 py-3 bg-[var(--surface2)] text-[13px] font-medium text-[var(--text)] list-none [&::-webkit-details-marker]:hidden flex items-center gap-2">
                          <ChevronRight className="w-4 h-4 text-[var(--text-dim)] transition-transform group-open:rotate-90 shrink-0" />
                          See the evidence — assumptions, measured changes, and the full record
                        </summary>
                        <div className="px-4 py-4">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            urlTransform={(url) => {
                              if (/^(metrics\.csv|decisions\.jsonl|trace\.jsonl|state\.json)$/.test(url)) {
                                return `${SIM_API_BASE}/runs/${runId}/files/${url}`;
                              }
                              return url;
                            }}
                          >
                            {appendix}
                          </ReactMarkdown>
                        </div>
                      </details>
                    )}
                    <div className="no-print mt-6 pt-4 border-t border-[var(--border)] flex flex-wrap items-center gap-4 text-[13px]">
                      <button
                        onClick={() => printReport(r.id)}
                        className="flex items-center gap-1.5 text-[var(--primary)] hover:underline cursor-pointer"
                      >
                        <Download className="w-4 h-4" />
                        Download report (PDF)
                      </button>
                      <span className="text-[var(--text-muted)]">·</span>
                      <button
                        onClick={() => setHowOpen(true)}
                        className="flex items-center gap-1.5 text-[var(--text-dim)] hover:text-[var(--text)] cursor-pointer"
                      >
                        <HelpCircle className="w-4 h-4" />
                        How this works
                      </button>
                      <a
                        href="/how-the-simulation-works.html"
                        download="How-the-Simulation-Works.html"
                        className="flex items-center gap-1.5 text-[var(--text-dim)] hover:text-[var(--text)] no-underline"
                      >
                        <Download className="w-4 h-4" />
                        Explainer one-pager
                      </a>
                    </div>
                  </div>
                </details>
              );
            })}
          </div>

          {finished && !optimizing && (
            <div className="no-print flex flex-wrap gap-3 mt-6">
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
      {howOpen && <HowItWorks onClose={() => setHowOpen(false)} />}
    </div>
  );
}
