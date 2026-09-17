'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

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
  n_evidence: number;
  n_ruling_evidence: number;
  n_adoption_evidence: number;
  // Presentation enrichment, computed in radar/build.py (not in the frozen scorer).
  action: string;
  stakes: string | null;
  is_duty: boolean;
  watch_kind: string | null;
  watch_reason: string | null;
  strength: {
    appellate: number;
    trial: number;
    primary: number;
    guidance: number;
    total: number;
    label: 'strong' | 'moderate' | 'thin';
    newest: string | null;
    oldest: string | null;
  };
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
  last_evidence_date?: string;
  stale_days?: number | null;
  lanes?: Record<string, number>;
  lanes_populated?: number;
  reviewed_on?: string;
  reviewed_days?: number | null;
  seam?: string;
  driver?: string;
}
interface Milestone {
  fault_line: string;
  status: 'landed' | 'pending' | 'superseded';
  antecedent: string | null;
  antecedent_date: string | null;
  antecedent_tier: string | null;
  binding: string | null;
  binding_date: string | null;
  lead_days: number | null;
  called_before_antecedent: boolean | null;
  note: string;
}
interface Milestones {
  milestones: Milestone[];
  n_milestones: number;
  n_landed: number;
  n_pending: number;
  n_superseded: number;
  lead_time_days: { median: number | null; min: number | null; max: number | null };
  actionable_now: { fault_line: string; precursor: string; precursor_date: string }[];
  engine_grade: { n: number; called: number; hit_rate: number | null; question: string };
  blindside: { n_no_precursor: number; n_standing_events: number; blindside_rate: number | null };
  not_a_forecast: string;
}

interface RadarData {
  as_of: string;
  fault_lines: FaultLine[];
  n_items: number;
  tiers: Record<string, { label: string; weight: number; desc: string }>;
}

/* -------------------------------------------------------------- constants */

const THRESH = 7;
type Lead = 'now' | 'soon' | 'later';
const LEAD_COLOR: Record<Lead, string> = { now: '#A4093F', soon: '#EFAE42', later: '#8FBFAE' };
const LEAD_LABEL: Record<Lead, string> = { now: 'now', soon: 'soon', later: 'later' };
type Momentum = 'arriving' | 'building' | 'idle';
const S_COLOR: Record<Momentum, string> = { arriving: '#A4093F', building: '#EFAE42', idle: '#8FBFAE' };
const S_LABEL: Record<Momentum, string> = { arriving: 'arriving', building: 'building', idle: 'idle' };
function sBucket(s: number): Momentum {
  if (s >= 6.5) return 'arriving';
  if (s >= 4.5) return 'building';
  return 'idle';
}
function staleColor(d: number): string {
  if (d <= 45) return '#8FBFAE';   // fresh (green)
  if (d <= 180) return '#EFAE42';  // aging (amber)
  return '#A4093F';                // stale (rose)
}
function staleLabel(d: number): string {
  return d > 180 ? `stale ${d}d` : `${d}d`;
}
function coverageColor(n: number): string {
  if (n >= 5) return '#8FBFAE';   // full (green)
  if (n >= 3) return '#EFAE42';   // partial (amber)
  return '#A4093F';               // thin (rose)
}
const LANE_KEYS: [string, string][] = [
  ['capability', 'L1'], ['ruling', 'L2'], ['adoption', 'L3'], ['enable', 'E'], ['software', 'S'],
];

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

/* -------------------------------------------------------------- rank chart */

// The overview chart. Where the scatter answers "how far has the law moved versus the
// market", this answers the question the page leads with: what is the order, and how well
// is each one supported. Stacked per control so the bar carries BOTH the amount of
// evidence and what kind of authority it is — a duty resting on seven circuit courts must
// not look like one resting on two trial orders and five bar opinions when the totals match.
const STRENGTH_SEGMENTS: { key: keyof FaultLine['strength']; label: string; color: string }[] = [
  { key: 'appellate', label: 'appellate court', color: 'var(--primary)' },
  { key: 'trial', label: 'trial court', color: 'var(--amber)' },
  { key: 'primary', label: 'statute or rule', color: 'var(--metric)' },
  { key: 'guidance', label: 'bar guidance', color: 'var(--text-muted)' },
];

function RankChart({ duties, watched }: { duties: FaultLine[]; watched: FaultLine[] }) {
  const rows = [...duties, ...watched];
  const max = Math.max(...rows.map((f) => f.strength?.total ?? 0), 1);
  const short = (s: string) => (s.length > 44 ? s.slice(0, 43).trimEnd() + '…' : s);

  return (
    <div>
      <div className="space-y-1.5">
        {rows.map((f, i) => {
          const s = f.strength;
          const total = s?.total ?? 0;
          return (
            <div key={f.id}>
              {i === duties.length && (
                <div className="flex items-center gap-2 my-2.5">
                  <span className="h-px flex-1 border-t border-dashed border-[var(--border-bright)]" />
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                    not required yet
                  </span>
                  <span className="h-px flex-1 border-t border-dashed border-[var(--border-bright)]" />
                </div>
              )}
              <div className="grid grid-cols-[1.3rem_1fr_2rem] gap-2 items-center">
                <span className="font-mono text-[11px] font-bold text-[var(--text-muted)] text-right">
                  {i + 1}
                </span>
                <div className="min-w-0">
                  <div className="text-[11.5px] text-[var(--text)] truncate" title={f.action}>
                    {short(f.action)}
                  </div>
                  <div
                    className="flex h-[7px] mt-1 rounded-sm overflow-hidden bg-[var(--sunken)]"
                    style={{ width: `${(total / max) * 100}%`, minWidth: '4px' }}
                  >
                    {STRENGTH_SEGMENTS.map((seg) => {
                      const v = (s?.[seg.key] as number) ?? 0;
                      if (!v || !total) return null;
                      return (
                        <span
                          key={seg.key}
                          style={{ width: `${(v / total) * 100}%`, background: seg.color }}
                          title={`${v} ${seg.label}`}
                        />
                      );
                    })}
                  </div>
                </div>
                <span className="font-mono text-[11px] text-[var(--text-muted)] text-right">
                  {total}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-4 pt-3 border-t border-[var(--border)]">
        {STRENGTH_SEGMENTS.map((seg) => (
          <span key={seg.key} className="inline-flex items-center gap-1.5 text-[10.5px] text-[var(--text-muted)]">
            <span className="w-2.5 h-2.5 rounded-sm" style={{ background: seg.color }} />
            {seg.label}
          </span>
        ))}
        <span className="text-[10.5px] text-[var(--text-muted)]">
          &middot; bar length = total sources, trailing number = same
        </span>
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
            {/* Numbered to match the action list above, and the stroke separates the two
                tiers that list defines: solid ring = required now, dashed = watching. */}
            <circle
              cx={sx(f.pressure)} cy={sy(f.adoption)} r={r}
              fill={LEAD_COLOR[lead]} fillOpacity={f.is_duty ? 0.9 : 0.45}
              stroke={f.is_duty ? 'var(--text-strong)' : 'var(--text-muted)'}
              strokeWidth={f.is_duty ? 2 : 1.5}
              strokeDasharray={f.is_duty ? undefined : '3 2.5'}
            />
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
        {!f.is_duty && <circle cx={sx(f.adoption)} cy={cy} r={rOf(f.queue) - 3} fill="none" stroke="var(--text-muted)" strokeWidth={1.5} strokeDasharray="3 2.5" />}
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
  const [error, setError] = useState<string | null>(null);
  const [showPrimer, setShowPrimer] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [sort, setSort] = useState<'urgency' | 'move'>('urgency');
  const [view, setView] = useState<'urgency' | 'gap'>('urgency');
  const [ms, setMs] = useState<Milestones | null>(null);
  // Read the flag threshold from the calibration output rather than restating it here. The
  // Python side already shipped one drift bug from a hardcoded threshold whose comment
  // claimed to be this number; there is no reason for the frontend to repeat it.
  const [callThreshold, setCallThreshold] = useState<number | null>(null);
  const [openAction, setOpenAction] = useState<string | null>(null);
  // Both detail sections fold by default: the action list is the answer, and the watch list
  // and the scatter are depth for a reader who wants it.
  const [showWatch, setShowWatch] = useState(false);
  const [showScatter, setShowScatter] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [d, m, c] = await Promise.all([
          fetch('/radar/data.json').then((r) => r.json()),
          // The firm-facing half: what the record already requires, how much warning it gave,
          // and what a forecast would have to add. Failing to load it must not blank the page,
          // since the meters below are still useful on their own.
          fetch('/radar/milestones.json').then((r) => r.json()).catch(() => null),
          fetch('/radar/calibration.json').then((r) => r.json()).catch(() => null),
        ]);
        if (!cancelled) { setData(d); setMs(m); setCallThreshold(c?.call_threshold ?? null); }
      } catch {
        if (!cancelled) setError('Could not load radar data.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (error) return <div className="p-8 text-[var(--rose)]">{error}</div>;
  if (!data) return <div className="p-8 text-[var(--text-muted)] font-mono text-sm">Loading radar…</div>;

  // Duties: the law has moved, which does not depend on who is reading. `mandated` on the
  // advisory side uses the same number, imported from the same place.
  const threshold = callThreshold ?? 8.0;
  // Ordered by how well-supported the duty is, not by how high the meter reads: a duty
  // resting on seven circuit courts is a different claim from one resting on two trial
  // orders, and a single ranking should not present them as equals.
  const duties = [...data.fault_lines]
    .filter((f) => f.pressure >= threshold)
    .sort((a, b) =>
      (b.strength?.appellate ?? 0) - (a.strength?.appellate ?? 0) ||
      (b.strength?.total ?? 0) - (a.strength?.total ?? 0) ||
      b.pressure - a.pressure);

  const leadFor = (id: string): number | null => {
    const ds = (ms?.milestones ?? [])
      .filter((m) => m.fault_line === id && m.status === 'landed' && m.lead_days != null)
      .map((m) => m.lead_days as number);
    if (!ds.length) return null;
    ds.sort((a, b) => a - b);
    return ds[Math.floor(ds.length / 2)];
  };

  const watched = [...data.fault_lines]
    .filter((f) => !f.is_duty && f.watch_reason)
    .sort((a, b) => b.pressure - a.pressure);

  const byQueue = [...data.fault_lines].sort((a, b) => b.queue - a.queue);
  // ONE numbering for the whole page: the action list's order (duties by evidence strength,
  // then the watching list by pressure). This used to be queue rank, so the chart numbered
  // the same eleven things differently from the list above it and taught the reader to
  // distrust both. Keep these two in step.
  const ranks = new Map(
    [...duties, ...watched].map((f, i) => [f.id, i + 1] as const),
  );
  const watch = byQueue.slice(3).filter((f) => leadBucket(f.lead) === 'later');

  const queueRows = [...data.fault_lines].sort((a, b) =>
    sort === 'urgency' ? b.queue - a.queue : queueDelta(b) - queueDelta(a)
  );
  const gapRows = [...data.fault_lines].sort((a, b) => (b.adoption - b.enable) - (a.adoption - a.enable));
  const gapRanks = new Map(gapRows.map((f, i) => [f.id, i + 1]));
  const tableRows = view === 'gap' ? gapRows : queueRows;
  const rowRanks = view === 'gap' ? gapRanks : ranks;

  const pick = (id: string) => setExpanded((cur) => (cur === id ? null : id));

  const needsCurating = data.fault_lines.filter((f) => {
    const stale = (f.stale_days ?? 0) > 180;
    const thin = (f.lanes_populated ?? 0) <= 2;
    const recentlyReviewed = (f.reviewed_days ?? Infinity) <= 30;
    return (stale || thin) && !recentlyReviewed;   // reviewed-but-dormant lines don't need the nudge
  });

  return (
    <div className="px-4 md:px-8 py-6 max-w-[1400px] mx-auto space-y-8">
      {/* header */}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Fault-Line Radar</p>
          <h1 className="text-2xl font-extrabold tracking-tight text-[var(--text-strong)] leading-tight">
            What the record already requires — and how much warning it gave
          </h1>
          <p className="font-mono text-[12px] text-[var(--text-muted)] mt-1.5">
            {data.as_of} · {data.n_items} tracked items · deterministic, replayable
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/radar/advisory" className="btn-secondary no-underline">Sequence for your firm →</Link>
          <Link href="/radar/calibration" className="btn-secondary no-underline">Calibration →</Link>
          <button onClick={() => setShowPrimer((s) => !s)} className="btn-secondary">
            {showPrimer ? 'Hide' : 'How this works'}
          </button>
        </div>
      </header>

      {/* re-curation prompt: surface thin/stale lines and point at the fix */}
      {needsCurating.length > 0 && (
        <div className="card p-4 border-l-4" style={{ borderLeftColor: 'var(--rose)' }}>
          <p className="text-[13px] font-semibold text-[var(--text-strong)]">
            {needsCurating.length} {needsCurating.length === 1 ? 'fault line needs' : 'fault lines need'} re-curation
          </p>
          <p className="text-[12px] text-[var(--text)] mt-1 leading-relaxed">
            {needsCurating.map((f) => f.control).join(' · ')} — thin or stale. In Claude Code, run{' '}
            <span className="font-mono text-[var(--primary)]">/refresh-radar</span> to re-curate them with Descrybe.
          </p>
        </div>
      )}

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

      {/* THE WHOLE BOARD — the shape of the list above, before the detail */}
      <section className="card p-4 md:p-6">
        <p className="eyebrow mb-2">The whole board</p>
        <p className="text-[12.5px] text-[var(--text)] leading-relaxed max-w-[880px] mb-4">
          The same eleven in the same order, one bar each. Bar length is how many sources stand
          behind the duty; the colours are what kind of authority they are, because seven
          circuit courts and seven bar opinions are not the same claim.
        </p>
        <RankChart duties={duties} watched={watched} />
      </section>

      {/* WHAT TO DO — the answer, first, with the evidence attached to each item */}
      <section className="card p-4 md:p-6">
        <p className="eyebrow mb-2">What to do</p>
        <p className="text-[13px] text-[var(--text)] leading-relaxed max-w-[880px] mb-4">
          {duties.length} controls are already required of any firm, whichever jurisdiction you
          practise in. Ordered by how well the record supports each one, strongest first. Follow
          the authority link on any of them to check the sources yourself.
        </p>

        <ol className="space-y-3">
          {duties.map((d, i) => {
            const open = openAction === d.id;
            const s = d.strength;
            return (
              <li key={d.id} className="border border-[var(--border)] rounded-lg overflow-hidden">
                <div className="p-3.5">
                  <div className="flex items-start gap-3">
                    <span className="font-mono text-[13px] font-bold text-[var(--text-muted)] pt-0.5">
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline gap-2 flex-wrap">
                        <span className="text-[15px] font-bold text-[var(--text-strong)]">
                          {d.action}
                        </span>
                        <span
                          className="pill text-[9px]"
                          style={{
                            background: `var(--${s.label === 'strong' ? 'metric-dim' : s.label === 'moderate' ? 'amber-dim' : 'brand-tint'})`,
                            color: `var(--${s.label === 'strong' ? 'metric' : s.label === 'moderate' ? 'amber' : 'primary'})`,
                          }}
                          title="How well the record supports this duty"
                        >
                          {s.label}
                        </span>
                      </div>

                      {d.stakes && (
                        <p className="text-[12.5px] text-[var(--text)] leading-relaxed mt-1.5">
                          {d.stakes}
                        </p>
                      )}

                      {/* HOW WE KNOW — the strength, stated at the claim, not one click away */}
                      <p className="font-mono text-[10.5px] text-[var(--text-muted)] mt-2">
                        {s.total} sources
                        {s.appellate > 0 && ` · ${s.appellate} appellate`}
                        {s.trial > 0 && ` · ${s.trial} trial court`}
                        {s.primary > 0 && ` · ${s.primary} statute/rule`}
                        {s.guidance > 0 && ` · ${s.guidance} bar guidance`}
                        {leadFor(d.id) != null && ` · first signal ${leadFor(d.id)}d before it bound`}
                      </p>

                      <button
                        onClick={() => setOpenAction(open ? null : d.id)}
                        className="mt-2 text-[11px] font-semibold text-[var(--primary)] hover:underline"
                      >
                        {open ? 'Hide the sources' : `See the ${s.total} sources`}
                      </button>
                    </div>
                  </div>

                  {open && (
                    <div className="mt-3 pl-7 space-y-2">
                      <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
                        Model Rules: {d.model_rules.join(' · ')} · our shorthand for this line is
                        &ldquo;{d.control}&rdquo;
                      </p>
                      {d.evidence.slice(0, 12).map((e, k) => (
                        <div key={k} className="text-[11.5px] leading-snug">
                          <span className="font-mono text-[10.5px] text-[var(--text-muted)]">{e.date}</span>{' '}
                          <span className="text-[var(--text)]">{e.title}</span>
                          <span className="block text-[10.5px] text-[var(--text-muted)] pl-1">
                            {e.source} · {e.tier}
                          </span>
                        </div>
                      ))}
                      {d.evidence.length > 12 && (
                        <p className="text-[10.5px] text-[var(--text-muted)]">
                          + {d.evidence.length - 12} more, shown in full further down the page
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ol>



        {/* NOT REQUIRED YET — suppressing these made the page read as if agentic supervision
            did not exist, when it is the one line with a live bill in Congress. */}
        {watched.length > 0 && (
          <>
            <button
              onClick={() => setShowWatch((v) => !v)}
              className="w-full text-left mt-6 pt-4 border-t-2 border-dashed border-[var(--border-bright)]"
            >
              <h3 className="text-[15px] font-bold text-[var(--text-strong)]">
                {showWatch ? '▾ hide' : '▸ show'} {duties.length + 1} to{' '}
                {duties.length + watched.length} &mdash; not required yet
              </h3>
            </button>
            {showWatch && (
              <p className="text-[12px] text-[var(--text-muted)] leading-relaxed max-w-[880px] mt-1.5 mb-3">
                The same single ranking continues below the line. These sit under the threshold, so
                nothing yet obliges you to act, but they are on the same list because a control can
                be worth building before it is required. The reason differs per line: a bill in
                Congress is a fact, while a reading near the line is only our own dial moving.
              </p>
            )}
            <ul className="space-y-2" style={{ display: showWatch ? undefined : 'none' }}>
              {watched.map((w, i) => (
                <li key={w.id} className="border border-[var(--border)] rounded-lg p-3 opacity-90">
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="font-mono text-[13px] font-bold text-[var(--text-muted)]">
                      {duties.length + i + 1}
                    </span>
                    <span className="text-[13.5px] font-bold text-[var(--text-strong)]">
                      {w.action}
                    </span>
                    <span className="pill text-[9px]" style={{ background: 'var(--brand-tint)', color: 'var(--primary)' }}>
                      {w.strength?.label}
                    </span>
                  </div>
                  {w.stakes && (
                    <p className="text-[12px] text-[var(--text)] leading-relaxed mt-1">{w.stakes}</p>
                  )}
                  <p className="font-mono text-[10.5px] text-[var(--text-muted)] mt-1.5">
                    {w.watch_reason}
                  </p>
                </li>
              ))}
            </ul>
          </>
        )}

        <div className="mt-5 pt-3 border-t border-[var(--border)]">
          <Link
            href="/radar/advisory"
            className="inline-flex items-center gap-2 text-[13px] font-bold text-[var(--primary)] hover:underline"
          >
            Now sequence these for your firm — name your pricing model, your carriers, and your
            readiness, and we&apos;ll order them and tell you which to defer →
          </Link>
        </div>
      </section>

      {/* WHAT THIS DOES NOT CLAIM — the only part of the old milestone block worth keeping.
          The lead-time prose went because every item now carries its own "first signal Nd
          before it bound" on the board, and the actionable-now list repeated two entries that
          are already on the list above. */}
      {ms && (
        <section className="card p-4 md:p-6">
          <p className="eyebrow mb-2">What this list does not claim</p>
          <p className="text-[12.5px] text-[var(--text-muted)] leading-relaxed max-w-[880px]">
            The order is a sort for attention, not a view about which ruling lands next, and the
            numbers are positions in that sort rather than a confidence score. On its own record
            the engine flagged <b>{ms.engine_grade.called} of {ms.engine_grade.n}</b> lines, read
            as retrodiction rather than as a track record, since the feed was curated by people
            who knew how those events turned out. The blindside rate,{' '}
            {Math.round((ms.blindside.blindside_rate ?? 0) * 100)}% ({ms.blindside.n_no_precursor}
            /{ms.blindside.n_standing_events}), is a floor rather than an exact figure: that scan
            runs over a hindsight-curated feed and so reads low by construction.
          </p>
        </section>
      )}

      {/* chart — scoring provenance, below the fold */}
      <section className="card p-4 md:p-6">
        {/* The whole block is the toggle. Previously only the heading was a button and the
            description sat outside it, so clicking the sentence that said "expand" did
            nothing — which is exactly what it looked like you should click. */}
        <button
          onClick={() => setShowScatter((v) => !v)}
          className="w-full text-left hover:bg-[var(--sunken)] rounded-md transition-colors -m-1 p-1"
        >
          <p className="eyebrow mb-2">
            {showScatter ? '\u25be hide' : '\u25b8 show'} &mdash; where each reading sits
            <span className="font-normal normal-case tracking-normal text-[var(--text-muted)]">
              {' '}· law against market, and how the numbers above were computed
            </span>
          </p>
          {!showScatter && (
            <p className="text-[12px] text-[var(--text-muted)] leading-relaxed max-w-[880px]">
              The eleven plotted against each other: right is how far the law has moved, up is how
              far the market has. Same numbers as the list, so you can find any duty on the board.
            </p>
          )}
        </button>
        <div style={{ display: showScatter ? undefined : 'none' }}>
        {/* The chart and the list above use ONE numbering now, so say it, and say which
            mark means which tier — otherwise the reader has to infer the encoding twice. */}
        <p className="text-[11.5px] text-[var(--text-muted)] leading-relaxed mb-3 max-w-[880px]">
          Each dot is numbered to match its place in the list above. A <b>solid ring</b> means
          required now; a <b>dashed ring</b> means on watch. Position is the two readings:
          right is how far the law has moved, up is how far the market has moved. A dot high and
          right is a control that is both required and being made table stakes; a dot far right
          and low is one the law has moved on that the market has not. Dot size is the
          intersection of the two.
        </p>
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
          <span>Dot size = queue score · number = its position in the list above · hover to inspect, click to expand</span>
        </div>
        </div>
      </section>

      {/* full queue */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <p className="eyebrow">{view === 'gap' ? 'Build vs buy — a different question, ranked by supply against demand'
            : 'The same eleven, in detail — click any row to open its evidence'}</p>
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
          <div className="grid grid-cols-[2rem_1fr_5rem_6rem_9rem_5rem] gap-2 px-4 py-2 border-b border-[var(--border)] text-[9.5px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
            <span>#</span><span>Control · fault line</span><span>Lead</span><span>Coverage</span><span>{view === 'gap' ? 'L3·E·S' : 'L1·L2·L3·E'}</span><span>{view === 'gap' ? 'Gap' : 'Queue'}</span>
          </div>
          {tableRows.map((f) => {
            const lead = leadBucket(f.lead);
            const open = expanded === f.id;
            return (
              <div key={f.id} id={`row-${f.id}`} className={`border-b border-[var(--border)] last:border-0 ${hovered === f.id ? 'bg-[var(--brand-tint)]' : ''}`}>
                <button onClick={() => pick(f.id)} onMouseEnter={() => setHovered(f.id)} onMouseLeave={() => setHovered(null)} className="w-full grid grid-cols-[2rem_1fr_5rem_6rem_9rem_5rem_1.5rem] gap-2 px-4 py-2.5 items-center text-left hover:bg-[var(--sunken)]">
                  <span className="font-mono text-[13px] font-bold text-[var(--text-muted)]">{rowRanks.get(f.id)}</span>
                  <span>
                    <span className="text-[13px] font-semibold text-[var(--text-strong)]">{f.control}</span>
                    <span className="block text-[11px] text-[var(--text-muted)]">{f.title}</span>
                  </span>
                  <span className="inline-flex items-center gap-1.5 text-[12px]">
                    <span className="w-2 h-2 rounded-full" style={{ background: LEAD_COLOR[lead] }} />{LEAD_LABEL[lead]}
                  </span>
                  <span className="flex flex-col items-start leading-tight">
                    <span className="text-[11px] font-semibold" style={{ color: coverageColor(f.lanes_populated ?? 0) }}>
                      {f.lanes_populated ?? 0}/5 lanes
                    </span>
                    {f.stale_days != null ? (
                      <span className="text-[10px] font-mono" style={{ color: staleColor(f.stale_days) }}>{staleLabel(f.stale_days)}</span>
                    ) : (
                      <span className="text-[10px] text-[var(--text-muted)] font-mono">—</span>
                    )}
                  </span>
                  <span className="font-mono text-[13px] text-[var(--text)]">
                    {view === 'gap'
                      ? `${whole(f.adoption)}·${whole(f.enable ?? f.enable_seed ?? 0)}·${whole(f.software ?? f.software_seed ?? 0)}`
                      : `${whole(f.capability)}·${whole(f.pressure)}·${whole(f.adoption)}·${whole(f.enable ?? f.enable_seed ?? 0)}`}
                  </span>
                  <span className="text-[13px] text-[var(--text-muted)] text-center">{open ? '\u25be' : '\u25b8'}</span>
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
                        {f.lanes && (
                          <p className="text-[11px] text-[var(--text-muted)] mt-1 font-mono">
                            Evidence per lane: {LANE_KEYS.map(([k, label]) => `${label}:${f.lanes![k] ?? 0}`).join(' · ')}
                          </p>
                        )}
                        {f.last_evidence_date && f.stale_days != null && (
                          <p className="text-[11px] text-[var(--text-muted)] mt-1">
                            Last evidence {f.last_evidence_date} ·{' '}
                            <span className="font-semibold" style={{ color: staleColor(f.stale_days) }}>{staleLabel(f.stale_days)}</span>
                          </p>
                        )}
                        {f.reviewed_days != null && (
                          <p className="text-[11px] text-[var(--text-muted)] mt-1">
                            Reviewed {f.reviewed_on} · <span className="font-semibold" style={{ color: '#8FBFAE' }}>{f.reviewed_days}d ago</span> — checked, dormant
                          </p>
                        )}
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
    </div>
  );
}
