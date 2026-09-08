'use client';

import { useEffect, useState } from 'react';

/* ------------------------------------------------------------------ types */

interface Evidence {
  date: string;
  source?: string;
  title: string;
  tier: string;
  url?: string;
  weight: number;
  conflict?: boolean;
}
interface FaultLine {
  id: string;
  title: string;
  model_rules: string[];
  horizon: string;
  layer?: string;
  vector: string;
  tech_driver: string;
  build_now: string;
  control: string;
  capability_seed: number;
  capability: number;
  capability_classes: string[];
  capability_evidence: Evidence[];
  pressure_seed: number;
  pressure: number;
  trend: string;
  evidence: Evidence[];
  adoption_seed: number;
  adoption: number;
  market_classes: string[];
  adoption_evidence: Evidence[];
  enable_seed: number;
  enable: number;
  enable_classes: string[];
  n_enable_evidence: number;
  enable_evidence: Evidence[];
  software_seed: number;
  software: number;
  queue: number;
  lead: string;
  seam?: string;
  driver?: string;
}
interface RadarData {
  as_of: string;
  fault_lines: FaultLine[];
  n_items: number;
  tiers: Record<string, { label: string; weight: number; desc: string }>;
}
interface Resolution {
  date: string;
  order: number;
  fault_line: string;
  title: string;
  url?: string;
  meter: string;
  reading_at_lead: number;
  reading_at_event: number;
  called: boolean;
}
interface Calibration {
  resolutions: Resolution[];
  hits: number;
  n_resolutions: number;
  by_order: Record<string, { hit_rate: number; hits: number; n: number }>;
  call_threshold: number;
  lead_days: number;
}

/* -------------------------------------------------------------- constants */

const THRESH = 7;
type Lead = 'now' | 'soon' | 'later';
const LEAD_COLOR: Record<Lead, string> = { now: '#A4093F', soon: '#EFAE42', later: '#8FBFAE' };
const LEAD_LABEL: Record<Lead, string> = { now: 'now', soon: 'soon', later: 'later' };
const ORDER_LABEL: Record<string, string> = { '1': 'L1 capability', '2': 'L2 ruling', '3': 'L3 adoption' };
type Momentum = 'arriving' | 'building' | 'idle';
const S_COLOR: Record<Momentum, string> = { arriving: '#A4093F', building: '#EFAE42', idle: '#8FBFAE' };
const S_LABEL: Record<Momentum, string> = { arriving: 'arriving', building: 'building', idle: 'idle' };
function sBucket(s: number): Momentum {
  if (s >= 6.5) return 'arriving';
  if (s >= 4.5) return 'building';
  return 'idle';
}

/* ---------------------------------------------------------------- helpers */

function leadBucket(raw: string): Lead {
  const s = (raw || '').toLowerCase();
  if (s === 'now') return 'now';
  if (s.includes('later') || s.includes('1-2') || s.includes('far')) return 'later';
  return 'soon';
}
const dec = (n: number) => n.toFixed(1);
const whole = (n: number) => Math.round(n).toString();
const seedQueue = (f: FaultLine) => (f.pressure_seed * f.adoption_seed) / 10;
const queueDelta = (f: FaultLine) => f.queue - seedQueue(f);
const signed = (n: number) => (n >= 0 ? `+${n.toFixed(1)}` : n.toFixed(1));

/* ------------------------------------------------------------------- meter */

function Meter({ label, seed, now }: { label: string; seed: number; now: number }) {
  const pct = (v: number) => `${Math.max(0, Math.min(100, v * 10))}%`;
  const rose = now >= seed;
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-[11px] font-semibold text-[var(--text-muted)]">{label}</span>
        <span className="font-mono text-[11px] text-[var(--text)]">
          {dec(now)} <span className="text-[var(--text-muted)]">({signed(now - seed)})</span>
        </span>
      </div>
      <div className="relative h-2 rounded-full bg-[var(--sunken)] overflow-hidden">
        <div className="absolute inset-y-0 left-0 bg-[var(--border-strong)]" style={{ width: pct(Math.min(seed, now)) }} />
        {rose && (
          <div className="absolute inset-y-0" style={{ left: pct(seed), width: pct(now - seed), background: 'var(--primary)' }} />
        )}
        <div className="absolute inset-y-0 w-px bg-[var(--text-strong)] opacity-50" style={{ left: '70%' }} />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------- chart */

function Chart({
  lines,
  ranks,
  hovered,
  onHover,
  onPick,
}: {
  lines: FaultLine[];
  ranks: Map<string, number>;
  hovered: string | null;
  onHover: (id: string | null) => void;
  onPick: (id: string) => void;
}) {
  const W = 920, H = 520;
  const ML = 52, MR = 20, TP = 20, BP = 48;
  const sx = (v: number) => ML + (v / 10) * (W - ML - MR);
  const sy = (v: number) => TP + (1 - v / 10) * (H - TP - BP);
  const rOf = (q: number) => 7 + Math.max(0, q) * 1.35;
  const ticks = [0, 2, 4, 6, 8, 10];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" style={{ maxHeight: 520 }}>
      <rect x={sx(THRESH)} y={sy(10)} width={sx(10) - sx(THRESH)} height={sy(THRESH) - sy(10)} fill="var(--brand-tint)" />
      {ticks.map((t) => (
        <g key={`g${t}`}>
          <line x1={sx(t)} y1={TP} x2={sx(t)} y2={H - BP} stroke="var(--border)" strokeWidth={1} />
          <line x1={ML} y1={sy(t)} x2={W - MR} y2={sy(t)} stroke="var(--border)" strokeWidth={1} />
          <text x={sx(t)} y={H - BP + 16} textAnchor="middle" fill="var(--text-muted)" style={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}>{t}</text>
          <text x={ML - 8} y={sy(t) + 3} textAnchor="end" fill="var(--text-muted)" style={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}>{t}</text>
        </g>
      ))}
      <line x1={sx(THRESH)} y1={TP} x2={sx(THRESH)} y2={H - BP} stroke="var(--primary)" strokeWidth={1.5} strokeDasharray="5 4" />
      <line x1={ML} y1={sy(THRESH)} x2={W - MR} y2={sy(THRESH)} stroke="var(--primary)" strokeWidth={1.5} strokeDasharray="5 4" />
      <text x={sx(THRESH) + 5} y={TP + 12} fill="var(--primary)" style={{ fontSize: 9, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>threshold 7</text>
      <text x={sx(9.98)} y={sy(9.98) + 2} textAnchor="end" fill="var(--primary)" style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.06em' }}>BUILD NOW</text>

      <text x={(ML + W - MR) / 2} y={H - 6} textAnchor="middle" fill="var(--text-muted)" style={{ fontSize: 11 }}>Right = the law is closer to acting →</text>
      <text x={-((TP + H - BP) / 2)} y={14} transform="rotate(-90)" textAnchor="middle" fill="var(--text-muted)" style={{ fontSize: 11 }}>Up = the market made the fix table stakes →</text>

      {lines.map((f) => (
        <line
          key={`t${f.id}`}
          x1={sx(f.pressure_seed)} y1={sy(f.adoption_seed)}
          x2={sx(f.pressure)} y2={sy(f.adoption)}
          stroke="var(--border-strong)" strokeWidth={1}
          opacity={hovered && hovered !== f.id ? 0.08 : 0.4}
        />
      ))}

      {lines.map((f) => {
        const lead = leadBucket(f.lead);
        const dim = hovered && hovered !== f.id;
        const r = rOf(f.queue);
        return (
          <g
            key={f.id}
            style={{ cursor: 'pointer' }}
            opacity={dim ? 0.2 : 1}
            onMouseEnter={() => onHover(f.id)}
            onMouseLeave={() => onHover(null)}
            onClick={() => onPick(f.id)}
          >
            <circle cx={sx(f.pressure)} cy={sy(f.adoption)} r={r} fill={LEAD_COLOR[lead]} fillOpacity={0.85} stroke="#fff" strokeWidth={1.5} />
            <text x={sx(f.pressure)} y={sy(f.adoption) + 3.5} textAnchor="middle" fill="#fff" style={{ fontSize: 10, fontWeight: 700 }}>{ranks.get(f.id)}</text>
          </g>
        );
      })}

      {hovered && (() => {
        const f = lines.find((x) => x.id === hovered);
        if (!f) return null;
        const tx = Math.min(sx(f.pressure) + 14, W - 250);
        const ty = Math.max(sy(f.adoption) - 46, TP + 4);
        return (
          <g pointerEvents="none">
            <rect x={tx} y={ty} width={238} height={42} rx={6} fill="#1F1A1C" />
            <text x={tx + 10} y={ty + 17} fill="#fff" style={{ fontSize: 11, fontWeight: 700 }}>{f.control}</text>
            <text x={tx + 10} y={ty + 33} fill="#C9C4C2" style={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}>
              L2 {dec(f.pressure)} · L3 {dec(f.adoption)} · queue {dec(f.queue)} ({signed(queueDelta(f))})
            </text>
          </g>
        );
      })()}
    </svg>
  );
}

/* ------------------------------------------------------- build-vs-buy chart */

function GapChart({
  lines,
  ranks,
  hovered,
  onHover,
  onPick,
}: {
  lines: FaultLine[];
  ranks: Map<string, number>;
  hovered: string | null;
  onHover: (id: string | null) => void;
  onPick: (id: string) => void;
}) {
  const W = 920, H = 520;
  const ML = 52, MR = 20, TP = 20, BP = 48;
  const sx = (v: number) => ML + (v / 10) * (W - ML - MR);
  const sy = (v: number) => TP + (1 - v / 10) * (H - TP - BP);
  const rOf = (q: number) => 7 + Math.max(0, q) * 1.35;
  const ticks = [0, 2, 4, 6, 8, 10];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" style={{ maxHeight: 520 }}>
      {/* consulting gap: table-stakes demand, but not yet buyable (bottom-right) */}
      <rect x={sx(THRESH)} y={sy(THRESH)} width={sx(10) - sx(THRESH)} height={sy(0) - sy(THRESH)} fill="var(--brand-tint)" />
      {ticks.map((t) => (
        <g key={`g${t}`}>
          <line x1={sx(t)} y1={TP} x2={sx(t)} y2={H - BP} stroke="var(--border)" strokeWidth={1} />
          <line x1={ML} y1={sy(t)} x2={W - MR} y2={sy(t)} stroke="var(--border)" strokeWidth={1} />
          <text x={sx(t)} y={H - BP + 16} textAnchor="middle" fill="var(--text-muted)" style={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}>{t}</text>
          <text x={ML - 8} y={sy(t) + 3} textAnchor="end" fill="var(--text-muted)" style={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}>{t}</text>
        </g>
      ))}
      <line x1={sx(THRESH)} y1={TP} x2={sx(THRESH)} y2={H - BP} stroke="var(--primary)" strokeWidth={1.5} strokeDasharray="5 4" />
      <line x1={ML} y1={sy(THRESH)} x2={W - MR} y2={sy(THRESH)} stroke="var(--primary)" strokeWidth={1.5} strokeDasharray="5 4" />
      <text x={sx(THRESH) + 5} y={sy(THRESH) - 5} fill="var(--primary)" style={{ fontSize: 9, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>threshold 7</text>

      <text x={sx(10) - 8} y={sy(10) + 14} textAnchor="end" fill="var(--metric)" style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.06em' }}>BUY · integrate</text>
      <text x={sx(10) - 8} y={H - BP - 8} textAnchor="end" fill="var(--primary)" style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.06em' }}>BUILD · the gap</text>
      <text x={sx(0) + 6} y={H - BP - 8} textAnchor="start" fill="var(--slate)" style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.06em' }}>later · optional</text>

      <text x={(ML + W - MR) / 2} y={H - 6} textAnchor="middle" fill="var(--text-muted)" style={{ fontSize: 11 }}>Right = the market made it table stakes (demand) →</text>
      <text x={-((TP + H - BP) / 2)} y={14} transform="rotate(-90)" textAnchor="middle" fill="var(--text-muted)" style={{ fontSize: 11 }}>Up = you can buy the fix today (supply) →</text>

      {lines.map((f) => (
        <line
          key={`t${f.id}`}
          x1={sx(f.adoption_seed)} y1={sy(f.enable_seed ?? 0)}
          x2={sx(f.adoption)} y2={sy(f.enable ?? f.enable_seed ?? 0)}
          stroke="var(--border-strong)" strokeWidth={1}
          opacity={hovered && hovered !== f.id ? 0.08 : 0.4}
        />
      ))}

      {lines.map((f) => {
        const mom = sBucket(f.software ?? f.software_seed ?? 0);
        const dim = hovered && hovered !== f.id;
        const r = rOf(f.queue);
        const cy = sy(f.enable ?? f.enable_seed ?? 0);
        return (
          <g
            key={f.id}
            style={{ cursor: 'pointer' }}
            opacity={dim ? 0.2 : 1}
            onMouseEnter={() => onHover(f.id)}
            onMouseLeave={() => onHover(null)}
            onClick={() => onPick(f.id)}
          >
            <circle cx={sx(f.adoption)} cy={cy} r={r} fill={S_COLOR[mom]} fillOpacity={0.85} stroke="#fff" strokeWidth={1.5} />
            <text x={sx(f.adoption)} y={cy + 3.5} textAnchor="middle" fill="#fff" style={{ fontSize: 10, fontWeight: 700 }}>{ranks.get(f.id)}</text>
          </g>
        );
      })}

      {hovered && (() => {
        const f = lines.find((x) => x.id === hovered);
        if (!f) return null;
        const cy = sy(f.enable ?? f.enable_seed ?? 0);
        const tx = Math.min(sx(f.adoption) + 14, W - 250);
        const ty = Math.max(cy - 46, TP + 4);
        return (
          <g pointerEvents="none">
            <rect x={tx} y={ty} width={238} height={42} rx={6} fill="#1F1A1C" />
            <text x={tx + 10} y={ty + 17} fill="#fff" style={{ fontSize: 11, fontWeight: 700 }}>{f.control}</text>
            <text x={tx + 10} y={ty + 33} fill="#C9C4C2" style={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}>
              L3 {dec(f.adoption)} · E {dec(f.enable ?? f.enable_seed ?? 0)} · S {dec(f.software ?? f.software_seed ?? 0)} · queue {dec(f.queue)}
            </text>
          </g>
        );
      })()}
    </svg>
  );
}

/* --------------------------------------------------------------- evidence */

function EvidenceList({ items, empty }: { items: Evidence[]; empty: string }) {
  if (!items?.length) return <p className="text-[12px] text-[var(--text-muted)] italic">{empty}</p>;
  return (
    <ul className="space-y-1.5">
      {items.slice(0, 6).map((e, i) => (
        <li key={i} className="text-[12px] leading-snug flex gap-2">
          <span className="badge badge-low shrink-0 mt-0.5">{e.tier}</span>
          <span>
            {e.url ? (
              <a href={e.url} target="_blank" rel="noreferrer" className="text-[var(--text)] hover:text-[var(--primary)] underline decoration-[var(--border-strong)] underline-offset-2">{e.title}</a>
            ) : (
              <span className="text-[var(--text)]">{e.title}</span>
            )}
            <span className="text-[var(--text-muted)] font-mono"> · {e.date}{e.source ? ` · ${e.source}` : ''}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

/* ------------------------------------------------------------------- page */

export default function RadarPage() {
  const [data, setData] = useState<RadarData | null>(null);
  const [cal, setCal] = useState<Calibration | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPrimer, setShowPrimer] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [sort, setSort] = useState<'urgency' | 'move'>('urgency');
  const [view, setView] = useState<'urgency' | 'gap'>('urgency');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [d, c] = await Promise.all([
          fetch('/radar/data.json').then((r) => r.json()),
          fetch('/radar/calibration.json').then((r) => r.json()),
        ]);
        if (!cancelled) { setData(d); setCal(c); }
      } catch {
        if (!cancelled) setError('Could not load radar data.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (error) return <div className="p-8 text-[var(--rose)]">{error}</div>;
  if (!data || !cal) return <div className="p-8 text-[var(--text-muted)] font-mono text-sm">Loading radar…</div>;

  const byQueue = [...data.fault_lines].sort((a, b) => b.queue - a.queue);
  const ranks = new Map(byQueue.map((f, i) => [f.id, i + 1]));
  const buildNow = byQueue.slice(0, 3);
  const watch = byQueue.slice(3).filter((f) => leadBucket(f.lead) === 'later');

  const queueRows = [...data.fault_lines].sort((a, b) =>
    sort === 'urgency' ? b.queue - a.queue : queueDelta(b) - queueDelta(a)
  );
  const gapRows = [...data.fault_lines].sort((a, b) => (b.adoption - b.enable) - (a.adoption - a.enable));
  const gapRanks = new Map(gapRows.map((f, i) => [f.id, i + 1]));
  const tableRows = view === 'gap' ? gapRows : queueRows;
  const rowRanks = view === 'gap' ? gapRanks : ranks;

  const pick = (id: string) => setExpanded((cur) => (cur === id ? null : id));

  return (
    <div className="px-4 md:px-8 py-6 max-w-[1400px] mx-auto space-y-8">
      {/* header */}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Fault-Line Radar</p>
          <h1 className="text-2xl font-extrabold tracking-tight text-[var(--text-strong)] leading-tight">
            Where legal-AI rules are heading — and what to build before they land
          </h1>
          <p className="font-mono text-[12px] text-[var(--text-muted)] mt-1.5">
            {data.as_of} · {data.n_items} tracked items · deterministic, replayable
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a href="#calibration" className="card px-3 py-2 flex items-center gap-2 no-underline hover:border-[var(--primary)]">
            <span className="font-mono text-lg font-extrabold text-[var(--primary)]">{cal.hits}/{cal.n_resolutions}</span>
            <span className="text-[11px] leading-tight text-[var(--text-muted)]">events called<br />{cal.lead_days} days early</span>
          </a>
          <button onClick={() => setShowPrimer((s) => !s)} className="btn-secondary">
            {showPrimer ? 'Hide' : 'How this works'}
          </button>
        </div>
      </header>

      {/* primer */}
      {showPrimer && (
        <div className="card p-5 grid md:grid-cols-3 gap-6">
          <div>
            <p className="eyebrow mb-1.5">What a fault line is</p>
            <p className="text-[13px] text-[var(--text)] leading-relaxed">A place where legal-AI capability is outrunning the rules — a rule likely to shift, and the control you should build before it does.</p>
          </div>
          <div>
            <p className="eyebrow mb-1.5">The three stages</p>
            <ul className="text-[13px] text-[var(--text)] leading-relaxed space-y-1">
              <li><b>L1 capability</b> — the tech clears a bar (a benchmark, a study).</li>
              <li><b>L2 ruling</b> — courts and bars start to act.</li>
              <li><b>L3 adoption</b> — insurers and buyers make the fix table stakes.</li>
            </ul>
          </div>
          <div>
            <p className="eyebrow mb-1.5">Reading the scores</p>
            <p className="text-[13px] text-[var(--text)] leading-relaxed">Every meter is 0–10, weighted by source authority not volume. 7 is high. High <b>L2 and L3</b> together is the build-now queue.</p>
          </div>
        </div>
      )}

      {/* chart */}
      <section className="card p-4 md:p-6">
        <div className="inline-flex rounded-lg border border-[var(--border)] overflow-hidden text-left mb-3">
          {(['urgency', 'gap'] as const).map((v) => (
            <button key={v} onClick={() => setView(v)} className={`px-3 py-1.5 ${view === v ? 'bg-[var(--primary)] text-white' : 'text-[var(--text-muted)] hover:text-[var(--text)]'}`}>
              <span className="block text-[12px] font-bold leading-tight">{v === 'urgency' ? 'For firms' : 'For advisors'}</span>
              <span className={`block text-[10px] leading-tight ${view === v ? 'text-white opacity-80' : 'text-[var(--text-muted)]'}`}>{v === 'urgency' ? 'Urgency · what to do first' : 'Build vs buy · where the build is'}</span>
            </button>
          ))}
        </div>
        {view === 'urgency' ? (
          <Chart lines={data.fault_lines} ranks={ranks} hovered={hovered} onHover={setHovered} onPick={pick} />
        ) : (
          <GapChart lines={data.fault_lines} ranks={gapRanks} hovered={hovered} onHover={setHovered} onPick={pick} />
        )}
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 mt-3 text-[11px] text-[var(--text-muted)]">
          {view === 'urgency' ? (
            <>
              <span className="font-semibold text-[var(--text)]">Lead time:</span>
              {(['now', 'soon', 'later'] as Lead[]).map((l) => (
                <span key={l} className="inline-flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: LEAD_COLOR[l] }} /> {LEAD_LABEL[l]}
                </span>
              ))}
            </>
          ) : (
            <>
              <span className="font-semibold text-[var(--text)]">Vendor momentum (S):</span>
              {(['arriving', 'building', 'idle'] as Momentum[]).map((m) => (
                <span key={m} className="inline-flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: S_COLOR[m] }} /> {S_LABEL[m]}
                </span>
              ))}
            </>
          )}
          <span>Dot size = queue score · number = queue rank · hover to inspect, click to expand</span>
        </div>
      </section>

      {/* build now */}
      <section>
        <p className="eyebrow mb-3">Build now — force-ranked</p>
        <div className="grid md:grid-cols-3 gap-4">
          {buildNow.map((f) => {
            const lead = leadBucket(f.lead);
            return (
              <div key={f.id} className="card p-4 flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-lg font-extrabold text-[var(--primary)]">#{ranks.get(f.id)}</span>
                  <span className="pill" style={{ background: LEAD_COLOR[lead], color: lead === 'soon' ? '#1F1A1C' : '#fff' }}>{LEAD_LABEL[lead]}</span>
                </div>
                <h3 className="text-[15px] font-bold text-[var(--text-strong)] leading-snug mb-1.5">{f.control}</h3>
                <p className="text-[12px] text-[var(--text)] leading-relaxed line-clamp-3 flex-1">{f.vector}</p>
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-[var(--border)]">
                  <span className="font-mono text-[12px] text-[var(--text-muted)]">
                    L2 {dec(f.pressure)} <span className="text-[var(--primary)]">{signed(f.pressure - f.pressure_seed)}</span> · L3 {dec(f.adoption)} <span className="text-[var(--primary)]">{signed(f.adoption - f.adoption_seed)}</span>
                  </span>
                  <button onClick={() => { setExpanded(f.id); document.getElementById(`row-${f.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }} className="text-[12px] font-semibold text-[var(--primary)] hover:underline">evidence →</button>
                </div>
              </div>
            );
          })}
        </div>
        {watch.length > 0 && (
          <p className="text-[12px] text-[var(--text-muted)] mt-3">
            <span className="font-semibold text-[var(--text)]">Just watch:</span>{' '}
            {watch.map((f) => f.control).join(', ')} — real but years out.
          </p>
        )}
      </section>

      {/* full queue */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <p className="eyebrow">{view === 'gap' ? 'Build vs buy — force-ranked' : 'The full queue'}</p>
          {view === 'gap' ? (
            <span className="text-[11px] text-[var(--text-muted)]">sorted by gap (demand − supply)</span>
          ) : (
            <div className="inline-flex rounded-full border border-[var(--border)] overflow-hidden text-[11px] font-semibold">
              {(['urgency', 'move'] as const).map((s) => (
                <button key={s} onClick={() => setSort(s)} className={`px-3 py-1.5 ${sort === s ? 'bg-[var(--primary)] text-white' : 'text-[var(--text-muted)] hover:text-[var(--text)]'}`}>
                  {s === 'urgency' ? 'Urgency' : 'Biggest move'}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="card overflow-hidden">
          <div className="grid grid-cols-[2rem_1fr_5rem_9rem_5rem] gap-2 px-4 py-2 border-b border-[var(--border)] text-[9.5px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
            <span>#</span><span>Control · fault line</span><span>Lead</span><span>{view === 'gap' ? 'L3·E·S' : 'L1·L2·L3·E'}</span><span>{view === 'gap' ? 'Gap' : 'Queue'}</span>
          </div>
          {tableRows.map((f) => {
            const lead = leadBucket(f.lead);
            const open = expanded === f.id;
            return (
              <div key={f.id} id={`row-${f.id}`} className={`border-b border-[var(--border)] last:border-0 ${hovered === f.id ? 'bg-[var(--brand-tint)]' : ''}`}>
                <button onClick={() => pick(f.id)} onMouseEnter={() => setHovered(f.id)} onMouseLeave={() => setHovered(null)} className="w-full grid grid-cols-[2rem_1fr_5rem_9rem_5rem] gap-2 px-4 py-2.5 items-center text-left hover:bg-[var(--sunken)]">
                  <span className="font-mono text-[13px] font-bold text-[var(--text-muted)]">{rowRanks.get(f.id)}</span>
                  <span>
                    <span className="text-[13px] font-semibold text-[var(--text-strong)]">{f.control}</span>
                    <span className="block text-[11px] text-[var(--text-muted)]">{f.title}</span>
                  </span>
                  <span className="inline-flex items-center gap-1.5 text-[12px]">
                    <span className="w-2 h-2 rounded-full" style={{ background: LEAD_COLOR[lead] }} />{LEAD_LABEL[lead]}
                  </span>
                  <span className="font-mono text-[13px] text-[var(--text)]">
                    {view === 'gap'
                      ? `${whole(f.adoption)}·${whole(f.enable ?? f.enable_seed ?? 0)}·${whole(f.software ?? f.software_seed ?? 0)}`
                      : `${whole(f.capability)}·${whole(f.pressure)}·${whole(f.adoption)}·${whole(f.enable ?? f.enable_seed ?? 0)}`}
                  </span>
                  <span className="font-mono text-[13px] font-bold text-[var(--text-strong)]">
                    {view === 'gap' ? (
                      <>{signed(f.adoption - (f.enable ?? f.enable_seed ?? 0))} <span className="text-[10px] text-[var(--primary)]">gap</span></>
                    ) : (
                      <>{whole(f.queue)} <span className="text-[10px] text-[var(--primary)]">{signed(queueDelta(f))}</span></>
                    )}
                  </span>
                </button>
                {open && (
                  <div className="px-4 pb-5 pt-1 grid md:grid-cols-2 gap-5 bg-[var(--sunken)]">
                    <div className="space-y-3">
                      <Meter label="L1 capability" seed={f.capability_seed} now={f.capability} />
                      <Meter label="L2 ruling pressure" seed={f.pressure_seed} now={f.pressure} />
                      <Meter label="L3 adoption" seed={f.adoption_seed} now={f.adoption} />
                      <Meter label="E market enablement" seed={f.enable_seed ?? 0} now={f.enable ?? f.enable_seed ?? 0} />
                      <div className="pt-1">
                        <p className="eyebrow mb-1">Why now</p>
                        <p className="text-[12px] text-[var(--text)] leading-relaxed">{f.vector}</p>
                      </div>
                      <div>
                        <p className="eyebrow mb-1">What to put in place</p>
                        <p className="text-[12px] text-[var(--text)] leading-relaxed">{f.build_now}</p>
                        <p className="text-[11px] text-[var(--text-muted)] mt-1">Model rules: {f.model_rules.join(', ')}</p>
                      </div>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <p className="eyebrow mb-1.5">L2 ruling evidence</p>
                        <EvidenceList items={f.evidence} empty="No ruling evidence yet." />
                      </div>
                      <div>
                        <p className="eyebrow mb-1.5">L3 adoption evidence</p>
                        <EvidenceList items={f.adoption_evidence} empty="Not scored yet — no market signal recorded." />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* calibration */}
      <section id="calibration">
        <p className="eyebrow mb-1">Calibration</p>
        <p className="text-[13px] text-[var(--text)] mb-4">The engine grades itself: {cal.lead_days} days before each event, at threshold {cal.call_threshold}. Called {cal.hits} of {cal.n_resolutions} real events before they landed.</p>
        <div className="grid grid-cols-3 gap-3 mb-5">
          {['2', '3', '1'].map((o) => {
            const b = cal.by_order[o];
            return (
              <div key={o} className="card p-4 text-center">
                <p className="font-mono text-2xl font-extrabold text-[var(--text-strong)]">{Math.round(b.hit_rate * 100)}%</p>
                <p className="text-[11px] text-[var(--text-muted)] mt-0.5">{ORDER_LABEL[o]} · {b.hits}/{b.n}</p>
              </div>
            );
          })}
        </div>
        <div className="card overflow-hidden">
          <div className="grid grid-cols-[6rem_5rem_1fr_9rem] gap-2 px-4 py-2 border-b border-[var(--border)] text-[9.5px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
            <span>Landed</span><span>Stage</span><span>Event</span><span>At call → today</span>
          </div>
          {[...cal.resolutions].sort((a, b) => a.date.localeCompare(b.date)).map((r, i) => (
            <div key={i} className="grid grid-cols-[6rem_5rem_1fr_9rem] gap-2 px-4 py-2.5 items-center border-b border-[var(--border)] last:border-0">
              <span className="font-mono text-[12px] text-[var(--text-muted)]">{r.date}</span>
              <span className="font-mono text-[11px] text-[var(--text)]">L{r.order}</span>
              <span className="text-[12px] text-[var(--text)]">
                {r.url ? <a href={r.url} target="_blank" rel="noreferrer" className="hover:text-[var(--primary)] underline decoration-[var(--border-strong)] underline-offset-2">{r.title}</a> : r.title}
              </span>
              <span className="flex items-center gap-2 font-mono text-[12px]">
                <span className={`pill ${r.called ? 'pill-success' : 'pill-warn'}`}>{r.called ? 'CALLED' : 'MISSED'}</span>
                <span className="text-[var(--text-muted)]">{dec(r.reading_at_lead)}→{dec(r.reading_at_event)}</span>
              </span>
            </div>
          ))}
        </div>
        <p className="text-[11px] text-[var(--text-muted)] leading-relaxed mt-3">
          The L1 misses are honest: they were first-of-kind capability jumps with no precursor to call from. The engine reports them as misses rather than tuning them away.
        </p>
      </section>
    </div>
  );
}
