'use client';

import { useEffect, useState } from 'react';
import {
  Radar, RefreshCw, AlertTriangle, ChevronDown, ChevronRight,
  TrendingUp, ArrowRight, Minus, Zap,
} from 'lucide-react';

// --- Shapes emitted by radar/build.py (deterministic score) + calibration.report() ---
interface Evidence {
  date: string; title: string; tier: string; source?: string;
  weight: number; empirical?: boolean; conflict?: boolean;
}
interface CapEvidence { date: string; title: string; capability: string; weight: number; empirical?: boolean; }
interface AdoptEvidence { date: string; title: string; market: string; weight: number; }
interface FaultLine {
  id: string; title: string; model_rules: string[]; horizon: string; layer: string;
  vector: string; tech_driver: string; build_now: string; control: string;
  capability_seed: number; capability: number; n_capability_evidence: number; capability_evidence: CapEvidence[];
  pressure_seed: number; pressure: number; trend: string; n_evidence: number; evidence: Evidence[];
  adoption_seed: number; adoption: number; n_adoption_evidence: number; adoption_evidence: AdoptEvidence[];
  queue: number; lead: string;
}
interface RadarData { as_of: string; n_items: number; fault_lines: FaultLine[]; }
interface OrderRate { n: number; hits: number; hit_rate: number | null; }
interface Conditional {
  prior: string; post: string; n_eligible: number; n_backed: number;
  rate: number | null; prior_called_without_post_event: string[];
}
interface Resolution {
  date: string; order: number; fault_line: string; title: string;
  reading_at_lead: number | null; reading_at_event: number | null; called: boolean;
}
interface Calibration {
  hit_rate: number | null; hits: number; n_resolutions: number;
  by_order: Record<string, OrderRate>;
  conditionals: { L1_to_L2: Conditional; L2_to_L3: Conditional };
  resolutions: Resolution[]; snapshots_recorded: number;
  call_threshold: number; lead_days: number;
}

const ORDER_NAME: Record<string, string> = { '1': 'Capability', '2': 'Ruling', '3': 'Adoption' };

function meterColor(v: number): string {
  if (v >= 8) return '#e0603a';
  if (v >= 6.5) return 'var(--amber)';
  if (v >= 5) return '#c9a227';
  return 'var(--slate)';
}

function pct(v: number | null): string {
  return v === null ? 'n/a' : `${Math.round(v * 100)}%`;
}

function rateColor(v: number | null): string {
  if (v === null) return 'var(--text-muted)';
  if (v >= 0.8) return 'var(--metric)';
  if (v >= 0.5) return 'var(--amber)';
  return 'var(--rose)';
}

function leadColor(lead: string): string {
  if (lead === 'now') return 'var(--primary)';
  if (lead.includes('later')) return 'var(--slate)';
  return 'var(--amber)';
}

function leadLabel(lead: string): string {
  if (lead === 'now') return 'start now';
  if (lead.includes('later')) return 'watch';
  return `stand up in ${lead}`;
}


function Meter({ label, value, seed, hint }: { label: string; value: number; seed: number; hint: string }) {
  return (
    <div className="flex-1 min-w-[110px]">
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]" title={hint}>{label}</span>
        <span className="text-sm font-bold tabular-nums" style={{ color: meterColor(value), fontFamily: "'Fraunces', serif" }}>{value.toFixed(1)}</span>
      </div>
      <div className="h-1.5 rounded-full bg-[var(--surface2)] overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${value * 10}%`, backgroundColor: meterColor(value) }} />
      </div>
      <span className="text-[9px] text-[var(--text-muted)] font-mono">seed {seed}</span>
    </div>
  );
}

function trendGlyph(t: string) {
  if (t === 'rising') return <span className="inline-flex items-center gap-1 text-[var(--metric)]"><TrendingUp className="w-3 h-3" />rising</span>;
  if (t === 'steady') return <span className="inline-flex items-center gap-1 text-[var(--text-muted)]"><ArrowRight className="w-3 h-3" />steady</span>;
  return <span className="inline-flex items-center gap-1 text-[var(--text-muted)]"><Minus className="w-3 h-3" />quiet</span>;
}

export default function RadarPage() {
  const [data, setData] = useState<RadarData | null>(null);
  const [cal, setCal] = useState<Calibration | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch('/radar/data.json').then((r) => { if (!r.ok) throw new Error('data.json ' + r.status); return r.json(); }),
      fetch('/radar/calibration.json').then((r) => (r.ok ? r.json() : null)).catch(() => null),
    ])
      .then(([d, c]) => { if (!cancelled) { setData(d); setCal(c); } })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load radar'); });
    return () => { cancelled = true; };
  }, []);

  if (error) {
    return (
      <div className="p-8 max-w-2xl">
        <div className="flex items-center gap-3 p-4 rounded-lg border border-[var(--rose)]/30 bg-[var(--rose)]/5">
          <AlertTriangle className="w-5 h-5 text-[var(--rose)]" />
          <div>
            <p className="text-sm font-medium text-[var(--text)]">Couldn&apos;t load the radar</p>
            <p className="text-xs text-[var(--text-muted)] font-mono">{error}</p>
            <p className="text-xs text-[var(--text-muted)] mt-1">Run <code>python3 radar/build.py</code> to regenerate the feed.</p>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-8 flex items-center gap-3 text-[var(--text-muted)]">
        <RefreshCw className="w-4 h-4 animate-spin" /> Loading radar…
      </div>
    );
  }

  const queue = [...data.fault_lines].sort((a, b) => b.queue - a.queue);
  const threshold = cal?.call_threshold ?? 7;

  const openAndScroll = (id: string) => {
    setOpen(id);
    requestAnimationFrame(() =>
      document.getElementById(`fl-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    );
  };

  return (
    <div className="px-4 md:px-6 py-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-start gap-3 mb-2">
        <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0" style={{ backgroundColor: 'var(--primary)' }}>
          <Radar className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[var(--text)]" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>
            Fault-Line Radar
          </h1>
          <p className="text-sm text-[var(--text-dim)]">
            Where legal-AI rules are heading — capability (L1) → ruling (L2) → control adoption (L3), weighted by authority.
          </p>
        </div>
      </div>
      <p className="text-xs text-[var(--text-muted)] font-mono mb-6">
        As of {data.as_of} · {data.n_items} tracked items · deterministic, replayable scores
      </p>

      <ExecSummary queue={queue} cal={cal} threshold={threshold} onPick={openAndScroll} />

      <RadarMap fls={data.fault_lines} threshold={threshold} onPick={openAndScroll} />

      {/* Calibration strip */}
      {cal && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 mb-6">
          <p className="text-sm text-[var(--text-dim)] mb-2">The engine grades itself, {cal.lead_days}d before each event, at threshold {cal.call_threshold}:</p>
          <div className="flex flex-wrap items-center gap-2">
            {Object.entries(cal.by_order).map(([o, s]) => (
              <span key={o} className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[var(--border)] bg-[var(--surface2)] text-xs font-mono whitespace-nowrap">
                <span className="text-[var(--text-dim)]">L{o} {ORDER_NAME[o]}</span>
                <b style={{ color: rateColor(s.hit_rate) }}>{pct(s.hit_rate)}</b>
                <span className="text-[var(--text-muted)]">({s.hits}/{s.n})</span>
              </span>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-xs mt-2 text-[var(--text-muted)] font-mono">
            <span>P(L2|L1) <b className="text-[var(--text-dim)]">{pct(cal.conditionals.L1_to_L2.rate)}</b> ({cal.conditionals.L1_to_L2.n_backed}/{cal.conditionals.L1_to_L2.n_eligible})</span>
            <span>P(L3|L2) <b className="text-[var(--text-dim)]">{pct(cal.conditionals.L2_to_L3.rate)}</b> ({cal.conditionals.L2_to_L3.n_backed}/{cal.conditionals.L2_to_L3.n_eligible})</span>
            {cal.conditionals.L1_to_L2.prior_called_without_post_event.length > 0 && (
              <span>capability outran the law: {cal.conditionals.L1_to_L2.prior_called_without_post_event.join(', ')}</span>
            )}
          </div>
        </div>
      )}

      {/* Operating-model queue */}
      <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-1 mt-8">
        Dig deeper — every fault line
      </h2>
      <p className="text-xs text-[var(--text-muted)] mb-3">The queue, sorted by urgency. Click any row for its three meters and the evidence behind each.</p>
      <div className="space-y-2">
        {queue.map((fl) => {
          const isOpen = open === fl.id;
          return (
            <div key={fl.id} id={`fl-${fl.id}`} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden scroll-mt-4">
              <button
                onClick={() => setOpen(isOpen ? null : fl.id)}
                className="w-full text-left p-4 flex flex-col md:flex-row md:items-center gap-4 hover:bg-[var(--surface2)] transition-colors"
              >
                <div className="flex items-start gap-2 md:w-64 flex-shrink-0">
                  {isOpen ? <ChevronDown className="w-4 h-4 mt-0.5 text-[var(--text-muted)]" /> : <ChevronRight className="w-4 h-4 mt-0.5 text-[var(--text-muted)]" />}
                  <div>
                    <p className="text-sm font-semibold text-[var(--text)] leading-tight" style={{ fontFamily: "'Fraunces', serif" }}>{fl.title}</p>
                    <p className="text-[11px] text-[var(--text-muted)] mt-0.5">{fl.control}</p>
                    <p className="text-[10px] text-[var(--text-muted)] mt-1 flex items-center gap-2">{trendGlyph(fl.trend)} · {fl.horizon}</p>
                  </div>
                </div>
                <div className="flex gap-4 flex-1">
                  <Meter label="L1 cap" value={fl.capability} seed={fl.capability_seed} hint="Can AI already do the thing that creates the fault line?" />
                  <Meter label="L2 rule" value={fl.pressure} seed={fl.pressure_seed} hint="Will a court, bar, or statute move on it?" />
                  <Meter label="L3 adopt" value={fl.adoption} seed={fl.adoption_seed} hint="Is the control becoming table stakes?" />
                </div>
                <div className="flex md:flex-col items-center md:items-end gap-2 md:gap-0.5 md:w-24 flex-shrink-0">
                  <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">Queue</span>
                  <span className="text-2xl font-bold tabular-nums" style={{ color: meterColor(fl.queue), fontFamily: "'Fraunces', serif" }}>{fl.queue.toFixed(1)}</span>
                  <span className="text-[10px] text-[var(--text-muted)] font-mono">lead: {fl.lead}</span>
                </div>
              </button>

              {isOpen && (
                <div className="px-4 pb-4 border-t border-[var(--border)] text-sm">
                  <p className="mt-3 text-[var(--text-dim)]"><b className="text-[var(--text)]">Fault line:</b> {fl.vector}</p>
                  <p className="mt-1 text-[var(--text-dim)]"><b className="text-[var(--text)]">Driver:</b> {fl.tech_driver}</p>
                  <p className="mt-1 text-[var(--metric)]"><b>Build now:</b> {fl.build_now}</p>
                  <p className="mt-1 text-[11px] text-[var(--text-muted)] font-mono">Model Rules: {fl.model_rules.join(' · ')}</p>

                  <EvidenceBlock title={`L1 capability evidence — weighted low, labeled (not a ruling) · ${fl.n_capability_evidence}`}
                    rows={fl.capability_evidence.map((e) => ({ date: e.date, tag: e.capability, title: e.title, weight: e.weight, empirical: e.empirical }))}
                    empty="No capability demonstration on record — seed only." />
                  <EvidenceBlock title={`L2 ruling evidence (provenance) · ${fl.n_evidence}`}
                    rows={fl.evidence.map((e) => ({ date: e.date, tag: e.tier, title: e.title, weight: e.weight, empirical: e.empirical, conflict: e.conflict, source: e.source }))}
                    empty="No evidence yet — seed thesis only." />
                  <EvidenceBlock title={`L3 adoption signals · ${fl.n_adoption_evidence}`}
                    rows={fl.adoption_evidence.map((e) => ({ date: e.date, tag: e.market, title: e.title, weight: e.weight }))}
                    empty="No market-adoption signal yet — seed only." />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Calibration log */}
      {cal && (
        <div className="mt-8">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
            Calibration — called before they landed
          </h2>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[var(--text-muted)] border-b border-[var(--border)]">
                  <th className="text-left font-semibold px-3 py-2">Landed</th>
                  <th className="text-left font-semibold px-3 py-2">Order</th>
                  <th className="text-left font-semibold px-3 py-2">Result</th>
                  <th className="text-left font-semibold px-3 py-2">Fault line</th>
                  <th className="text-left font-semibold px-3 py-2">Lead → event</th>
                  <th className="text-left font-semibold px-3 py-2">Resolution</th>
                </tr>
              </thead>
              <tbody>
                {cal.resolutions.map((r, i) => (
                  <tr key={i} className="border-b border-[var(--border)]/50">
                    <td className="px-3 py-2 font-mono text-[var(--text-muted)] whitespace-nowrap">{r.date}</td>
                    <td className="px-3 py-2 font-mono text-[var(--text-dim)]">L{r.order}</td>
                    <td className="px-3 py-2">
                      <span className="font-semibold" style={{ color: r.called ? 'var(--metric)' : 'var(--rose)' }}>
                        {r.called ? '● called' : '○ missed'}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-[var(--text-dim)]">{r.fault_line}</td>
                    <td className="px-3 py-2 font-mono text-[var(--text-muted)] whitespace-nowrap">{r.reading_at_lead} → {r.reading_at_event}</td>
                    <td className="px-3 py-2 text-[var(--text-dim)]">{r.title}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-[var(--text-muted)] mt-2">
            Point-in-time backtest: the engine replays itself {cal.lead_days} days before each event on the evidence available then. Misses are kept honest, not tuned away — the two L1 misses are first-of-kind capabilities with no precursor to call from.
          </p>
        </div>
      )}
    </div>
  );
}

function FlChip({ fl, onPick }: { fl: FaultLine; onPick: (id: string) => void }) {
  return (
    <button onClick={() => onPick(fl.id)}
      className="underline decoration-dotted underline-offset-2 hover:text-[var(--primary)] transition-colors">
      {fl.title}
    </button>
  );
}

// --- Executive summary: the biggest things going on, at a glance ---
function ExecSummary({ queue, cal, threshold, onPick }: {
  queue: FaultLine[]; cal: Calibration | null; threshold: number; onPick: (id: string) => void;
}) {
  const buildNow = queue.filter((f) => f.pressure >= threshold && f.adoption >= threshold);
  const rising = queue.filter((f) => f.trend === 'rising');
  const prepare = rising.filter((f) => !buildNow.includes(f));
  const byId = (id: string) => queue.find((f) => f.id === id);
  const watch = (cal?.conditionals.L1_to_L2.prior_called_without_post_event ?? [])
    .map(byId).filter(Boolean) as FaultLine[];

  const list = (fls: FaultLine[]) =>
    fls.map((f, i) => (
      <span key={f.id}>{i > 0 && ', '}<FlChip fl={f} onPick={onPick} /></span>
    ));

  return (
    <div className="rounded-xl border p-5 mb-6"
      style={{ borderColor: 'var(--primary)', backgroundColor: 'var(--primary-dim)' }}>
      <div className="flex items-center gap-2 mb-2">
        <Zap className="w-4 h-4" style={{ color: 'var(--primary)' }} />
        <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--text)]">Executive summary — what to do</h2>
      </div>

      {buildNow.length > 0 ? (
        <p className="text-sm text-[var(--text-dim)] mb-4 leading-relaxed">
          <b className="text-[var(--text)]">What&apos;s happening.</b>{' '}
          {buildNow.slice(0, 3).map((f) => (<span key={f.id}>{f.vector} </span>))}
          {buildNow.length > 3 && `Another ${buildNow.length - 3} control${buildNow.length - 3 > 1 ? 's are' : ' is'} crossing the same line. `}
          The pattern repeats: an AI capability is outrunning a duty you already owe, and the market is standardizing the fix before the rule is written. The measures below are what it takes to be ready — build them ahead of the ruling, in this order:
        </p>
      ) : (
        <p className="text-sm text-[var(--text-dim)] mb-4">
          Nothing has hit the build-now corner yet. Watch the rising lines below and get ahead of them.
        </p>
      )}

      {buildNow.length > 0 && (
        <ol className="space-y-3 mb-4">
          {buildNow.slice(0, 5).map((f, i) => (
            <li key={f.id} className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[var(--primary)] text-white text-xs font-bold flex items-center justify-center mt-0.5">{i + 1}</span>
              <div className="min-w-0 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-base font-semibold text-[var(--text)]" style={{ fontFamily: "'Fraunces', serif" }}>{f.control}</span>
                  <span className="text-[10px] font-mono uppercase tracking-wide px-2 py-0.5 rounded-full" style={{ backgroundColor: leadColor(f.lead), color: '#fff' }}>{leadLabel(f.lead)}</span>
                </div>
                <p className="text-xs text-[var(--text-dim)]"><b className="text-[var(--text)]">What to put in place:</b> {f.build_now}</p>
                <p className="text-xs text-[var(--text-dim)]"><b className="text-[var(--text)]">Why now:</b> {f.vector} {f.tech_driver}</p>
                <button onClick={() => onPick(f.id)}
                  className="text-[11px] underline decoration-dotted underline-offset-2 text-[var(--text-muted)] hover:text-[var(--primary)] transition-colors">
                  see the evidence →
                </button>
              </div>
            </li>
          ))}
        </ol>
      )}

      <div className="space-y-1.5 text-xs text-[var(--text-dim)] border-t border-[var(--primary)]/20 pt-3">
        {prepare.length > 0 && (
          <p><b className="text-[var(--text)]">Prepare next:</b> {list(prepare.slice(0, 4))} — pressure is rising but not mandatory yet. Scope the work now so you&apos;re not caught flat.</p>
        )}
        {watch.length > 0 && (
          <p><b className="text-[var(--text)]">Just watch:</b> {list(watch)} — the capability is proven but no rule has landed. Don&apos;t build yet; don&apos;t be surprised when it moves.</p>
        )}
        {cal && (
          <p className="text-[var(--text-muted)]">Why trust this: the engine called {cal.hits} of {cal.n_resolutions} real events {cal.lead_days} days before they landed. Its record is in the calibration log below.</p>
        )}
      </div>
    </div>
  );
}

// --- The radar map: the clear picture. Every fault line placed by the two pressures
//     that make a control mandatory; top-right corner = build now. Dig deeper by click. ---
function RadarMap({ fls, threshold, onPick }: {
  fls: FaultLine[]; threshold: number; onPick: (id: string) => void;
}) {
  // Wide aspect so it fills page width without towering. Coordinates map value 0-10.
  const W = 1040, H = 500, mL = 70, mB = 56, mT = 28, mR = 28;
  const pw = W - mL - mR, ph = H - mT - mB;
  const X = (v: number) => mL + (v / 10) * pw;
  const Y = (v: number) => mT + ph - (v / 10) * ph;

  // Number dots by queue rank (1 = most urgent). Nudge near-identical coordinates apart.
  const ranked = [...fls].sort((a, b) => b.queue - a.queue);
  const placed: { fl: FaultLine; x: number; y: number; n: number }[] = [];
  ranked.forEach((fl, i) => {
    let x = X(fl.pressure), y = Y(fl.adoption);
    let guard = 0;
    while (placed.some((p) => Math.abs(p.x - x) < 22 && Math.abs(p.y - y) < 20) && guard < 8) {
      x += 22; y -= 3; guard++;
    }
    placed.push({ fl, x, y, n: i + 1 });
  });
  const rank = new Map(placed.map((p) => [p.fl.id, p.n]));

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 mb-6">
      <p className="text-xs text-[var(--text-dim)] mb-3">
        <b className="text-[var(--text)]">How to read it.</b> Each dot is a fault line. It moves <b>right</b> as the law
        gets closer to acting, and <b>up</b> as the market makes the fix table stakes. The <b style={{ color: 'var(--primary)' }}>top-right corner</b> is
        where you build now — urgent and about to be required. Bigger dot = higher queue; color = lead time
        (<span style={{ color: 'var(--primary)' }}>now</span>, <span style={{ color: 'var(--amber)' }}>soon</span>, <span style={{ color: 'var(--slate)' }}>later</span>). Click any dot or row to dig in.
      </p>

      {/* Full-width plot */}
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img"
        aria-label="Quadrant map of legal-AI fault lines by ruling pressure and adoption pressure">
        <rect x={X(threshold)} y={Y(10)} width={X(10) - X(threshold)} height={Y(threshold) - Y(10)}
          fill="var(--primary)" opacity="0.09" />
        <text x={X(10) - 8} y={Y(10) + 18} textAnchor="end" fontSize="13" fontWeight="700"
          fill="var(--primary)" fontFamily="monospace">BUILD NOW</text>
        <line x1={X(threshold)} y1={Y(10)} x2={X(threshold)} y2={Y(0)} stroke="var(--border-bright)" strokeDasharray="4 3" />
        <line x1={X(0)} y1={Y(threshold)} x2={X(10)} y2={Y(threshold)} stroke="var(--border-bright)" strokeDasharray="4 3" />
        <line x1={X(0)} y1={Y(0)} x2={X(10)} y2={Y(0)} stroke="var(--border)" />
        <line x1={X(0)} y1={Y(0)} x2={X(0)} y2={Y(10)} stroke="var(--border)" />
        <text x={mL + pw / 2} y={H - 12} textAnchor="middle" fontSize="13" fill="var(--text-dim)" fontFamily="monospace">
          L2 ruling pressure →  will the law move
        </text>
        <text x={20} y={mT + ph / 2} textAnchor="middle" fontSize="13" fill="var(--text-dim)" fontFamily="monospace"
          transform={`rotate(-90 20 ${mT + ph / 2})`}>
          L3 adoption →  becoming table stakes
        </text>
        {placed.map(({ fl, x, y, n }) => {
          const r = 9 + fl.queue * 1.1;
          const c = leadColor(fl.lead);
          return (
            <g key={fl.id} className="cursor-pointer" onClick={() => onPick(fl.id)}>
              <circle cx={x} cy={y} r={r} fill={c} opacity="0.22" />
              <circle cx={x} cy={y} r={r} fill="none" stroke={c} strokeWidth="1.5" />
              <text x={x} y={y + 4} textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--text)" fontFamily="monospace">{n}</text>
            </g>
          );
        })}
      </svg>

      {/* One row per item, below the plot, with a short explanation */}
      <div className="mt-4 border-t border-[var(--border)]">
        {ranked.map((fl) => (
          <button key={fl.id} onClick={() => onPick(fl.id)}
            className="w-full flex items-center gap-3 text-left py-2.5 px-1 border-b border-[var(--border)]/50 hover:bg-[var(--surface2)] transition-colors">
            <span className="inline-flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold flex-shrink-0"
              style={{ backgroundColor: leadColor(fl.lead), color: '#fff' }}>{rank.get(fl.id)}</span>
            <span className="text-sm font-semibold text-[var(--text)] w-48 flex-shrink-0 truncate" style={{ fontFamily: "'Fraunces', serif" }}>{fl.title}</span>
            <span className="text-xs text-[var(--text-dim)] flex-1 min-w-0">{fl.vector}</span>
            <span className="hidden md:inline font-mono text-[10px] text-[var(--text-muted)] flex-shrink-0 whitespace-nowrap">
              cap {fl.capability.toFixed(1)} · rule {fl.pressure.toFixed(1)} · adopt {fl.adoption.toFixed(1)}
            </span>
            <span className="font-mono text-xs font-bold flex-shrink-0 w-16 text-right" style={{ color: meterColor(fl.queue) }}>Q {fl.queue.toFixed(1)}</span>
            <span className="hidden sm:inline text-[10px] font-mono uppercase px-2 py-0.5 rounded-full flex-shrink-0" style={{ backgroundColor: leadColor(fl.lead), color: '#fff' }}>{leadLabel(fl.lead)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

interface Row { date: string; tag: string; title: string; weight: number; empirical?: boolean; conflict?: boolean; source?: string; }

function EvidenceBlock({ title, rows, empty }: { title: string; rows: Row[]; empty: string }) {
  return (
    <div className="mt-4">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-1">{title}</p>
      <div className="rounded-lg border border-[var(--border)] overflow-hidden">
        {rows.length === 0 ? (
          <p className="px-3 py-2 text-[11px] text-[var(--text-muted)] italic">{empty}</p>
        ) : (
          rows.map((r, i) => (
            <div key={i} className="flex items-start gap-3 px-3 py-2 border-b border-[var(--border)]/40 last:border-0">
              <span className="font-mono text-[10px] text-[var(--text-muted)] whitespace-nowrap w-20 flex-shrink-0">{r.date}</span>
              <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-[var(--surface2)] text-[var(--text-dim)] whitespace-nowrap flex-shrink-0">{r.tag}</span>
              <span className="text-[11px] text-[var(--text-dim)] flex-1">
                {r.title}
                {r.empirical && <span className="ml-1 text-[9px] text-[var(--metric)]">data</span>}
                {r.conflict && <span className="ml-1 text-[9px] text-[var(--rose)]">conflict</span>}
                {r.source && <span className="block text-[9px] text-[var(--text-muted)]">{r.source} · w={r.weight}</span>}
                {!r.source && <span className="ml-1 text-[9px] text-[var(--text-muted)]">w={r.weight}</span>}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
