'use client';

import { useEffect, useState } from 'react';

/* ------------------------------------------------------------------ types */

interface OrderVals {
  '1_capability': number;
  '2_enablement': number;
  '2_market_enable': number;
  '3_pressure': number;
  '3_adoption': number;
  '4_gate_full': number;
  '4_gate_eff': number;
}
interface Row {
  fault_line: string;
  title: string;
  control: string;
  horizon: string;
  seam: string;
  driver: string;
  required: boolean;
  opportunistic: boolean;
  govern: string;
  govern_note: string;
  deploy: string | null;
  deploy_note: string;
  orders: OrderVals;
}
interface Advisory {
  as_of: string;
  firm: { name: string; pricing: string; refill: number; enablement: number };
  economic_gate: { delta_per_lawyer: number; mode: string };
  verdict_counts: { govern: Record<string, number>; deploy: Record<string, number> };
  rows: Row[];
}

const SLUGS = ['hourly', 'fixed-fee', 'fixed-fee-building'] as const;
const SLUG_LABEL: Record<string, string> = {
  'hourly': 'Hourly firm',
  'fixed-fee': 'Fixed-fee firm',
  'fixed-fee-building': 'Fixed-fee, building capacity',
};

const GOV_ACCENT: Record<string, string> = {
  'stand-up-now': 'var(--emerald)',
  'build-capacity-first': 'var(--indigo)',
  'no-mandate': 'var(--slate)',
};
const DEP_ACCENT: Record<string, string> = {
  'deploy-now': 'var(--emerald)',
  'fix-pricing-first': 'var(--rose)',
  'defer': 'var(--amber)',
  'watch': 'var(--slate)',
};

const money = (n: number) =>
  n < 0 ? `-$${Math.abs(n).toLocaleString()}` : `+$${n.toLocaleString()}`;

/* ---------------------------------------------------------------- page */

export default function RadarAdvisoryPage() {
  const [data, setData] = useState<Record<string, Advisory> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [slug, setSlug] = useState<string>('fixed-fee');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const map: Record<string, Advisory> = {};
        for (const s of SLUGS) {
          const r = await fetch(`/radar/advisory/${s}.json`);
          map[s] = (await r.json()) as Advisory;
        }
        if (!cancelled) setData(map);
      } catch {
        if (!cancelled) setError('Could not load advisory data.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (error) return <div className="p-8 text-[var(--rose)]">{error}</div>;
  if (!data) return <div className="p-8 text-[var(--text-muted)] font-mono text-sm">Loading advisory…</div>;

  const a = data[slug];
  const gc = a.verdict_counts.govern;
  const dc = a.verdict_counts.deploy;

  const lane = (v: string | null, map: Record<string, string>) =>
    v === null ? '—' : (
      <span className="pill" style={{ background: map[v] ?? 'var(--border)', color: '#fff' }}>{v}</span>
    );

  return (
    <div className="px-4 md:px-8 py-6 max-w-[1400px] mx-auto space-y-6">
      <header>
        <p className="eyebrow">Fault-Line Radar · advisory</p>
        <h1 className="text-2xl font-extrabold tracking-tight text-[var(--text-strong)] leading-tight">
          Two decisions per issue: stand up the control, put AI on the work
        </h1>
        <p className="text-[13px] text-[var(--text)] max-w-[820px] mt-1.5 leading-relaxed">
          A required control is never deferred because the AI economics are poor; deploying AI is
          never forced by a rule. Each fault line gets a <b>GOVERN</b> answer (compliance calendar)
          and a <b>DEPLOY</b> answer (build &amp; buy budget), kept apart.
        </p>
      </header>

      {/* posture selector */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mr-1">Firm posture:</span>
        {SLUGS.map((s) => (
          <button
            key={s}
            onClick={() => setSlug(s)}
            className={`px-3 py-1.5 rounded-full border text-[12px] font-semibold transition-colors ${
              slug === s ? 'bg-[var(--primary)] text-white border-[var(--primary)]' : 'border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text)]'
            }`}
          >
            {SLUG_LABEL[s]}
          </button>
        ))}
      </div>

      {/* headline economics */}
      <div className="card p-4 flex flex-wrap items-center gap-x-6 gap-y-2">
        <div>
          <p className="text-[11px] text-[var(--text-muted)] uppercase tracking-wider font-semibold">Economic gate</p>
          <p className="font-mono text-lg font-extrabold text-[var(--text-strong)]">
            {money(a.economic_gate.delta_per_lawyer)}<span className="text-[11px] font-normal text-[var(--text-muted)]"> / lawyer / yr under {a.firm.pricing}</span>
          </p>
        </div>
        <div>
          <p className="text-[11px] text-[var(--text-muted)] uppercase tracking-wider font-semibold">Govern</p>
          <p className="font-mono text-[13px] text-[var(--text-strong)]">{gc['stand-up-now'] ?? 0} stand up · {gc['build-capacity-first'] ?? 0} build capacity · {gc['no-mandate'] ?? 0} no mandate</p>
        </div>
        <div>
          <p className="text-[11px] text-[var(--text-muted)] uppercase tracking-wider font-semibold">Deploy</p>
          <p className="font-mono text-[13px] text-[var(--text-strong)]">{dc['deploy-now'] ?? 0} deploy · {dc['fix-pricing-first'] ?? 0} fix pricing · {dc['defer'] ?? 0} defer</p>
        </div>
      </div>

      {/* rows */}
      <div className="card overflow-hidden">
        <div className="grid grid-cols-[1fr_9rem_9rem_7rem] gap-2 px-4 py-2 border-b border-[var(--border)] text-[9.5px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
          <span>Control · fault line</span><span>GOVERN · stand up?</span><span>DEPLOY · put AI on it?</span><span>L2 · L3 · E</span>
        </div>
        {[...a.rows].sort((x, y) => (y.required ? 1 : 0) - (x.required ? 1 : 0)).map((r) => (
          <div key={r.fault_line} className="grid grid-cols-[1fr_9rem_9rem_7rem] gap-2 px-4 py-2.5 items-center border-b border-[var(--border)] last:border-0 hover:bg-[var(--sunken)]">
            <span>
              <span className="text-[13px] font-semibold text-[var(--text-strong)]">
                {r.control}
                {r.required && <span className="ml-2 text-[9px] font-bold uppercase tracking-wider text-[var(--rose)]">required</span>}
              </span>
              <span className="block text-[11px] text-[var(--text-muted)]">{r.title}</span>
            </span>
            <span className="flex flex-col items-start gap-0.5">
              {lane(r.govern, GOV_ACCENT)}
              <span className="text-[9.5px] text-[var(--text-muted)] leading-tight">{r.govern_note}</span>
            </span>
            <span className="flex flex-col items-start gap-0.5">
              {lane(r.deploy, DEP_ACCENT)}
              {r.deploy && <span className="text-[9.5px] text-[var(--text-muted)] leading-tight">{r.deploy_note}</span>}
            </span>
            <span className="font-mono text-[12px] text-[var(--text)]">
              {r.orders['3_pressure']}·{r.orders['3_adoption']}·{r.orders['2_market_enable']}
            </span>
          </div>
        ))}
      </div>

      <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
        GOVERN is driven by whether the control is required and the firm can meet it. DEPLOY is driven
        by pricing and whether the AI can capture the work — it is only asked where AI does the billable
        work. Advisory is guidance under uncertainty, never a forecast.
      </p>
    </div>
  );
}
