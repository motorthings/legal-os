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
  mandated: boolean;
  expected: boolean;
  leverage_actors: string[];
  leverage_is_yours: boolean;
  leverage_requirements: string[];
  opportunistic: boolean;
  confidence: string | null;
  govern: string;
  govern_note: string;
  deploy: string | null;
  deploy_note: string;
  orders: OrderVals;
  sequence: number;
  tier: string;
  tier_note: string;
  lead_days: number | null;
  precursor: { date: string; title: string } | null;
}
interface PlanItem {
  sequence: number;
  fault_line: string;
  control: string;
  tier: string;
  govern: string;
  confidence: string | null;
  lead_days: number | null;
  why: string;
}
interface Advisory {
  as_of: string;
  firm: { name: string; pricing: string; refill: number; enablement: number };
  economic_gate: { delta_per_lawyer: number; mode: string };
  verdict_counts: { govern: Record<string, number>; deploy: Record<string, number> };
  plan: PlanItem[];
  rows: Row[];
}

const SLUGS = ['hourly', 'fixed-fee', 'fixed-fee-building'] as const;
const SLUG_LABEL: Record<string, string> = {
  'hourly': 'Hourly firm',
  'fixed-fee': 'Fixed-fee firm',
  'fixed-fee-building': 'Fixed-fee, building capacity',
};

// NOTE: these maps previously referenced --emerald, --indigo, and --sky, none of which
// are defined in globals.css — so every verdict pill had been rendering with no accent.
// Mapped onto tokens that actually exist; keep new entries to this list.
const GOV_ACCENT: Record<string, string> = {
  'stand-up-now': 'var(--metric)',       // a duty, and the firm is ready
  'build-capacity-first': 'var(--amber)', // a duty or norm the firm can't meet yet
  'match-the-market': 'var(--secondary)', // table stakes, not a duty
  'no-mandate': 'var(--slate)',
};
const DEP_ACCENT: Record<string, string> = {
  'deploy-now': 'var(--metric)',
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
  // Only the work. A row whose GOVERN verdict is 'no-mandate' has nothing for the firm to
  // do, and a list that includes it is a list of eleven things when the answer is seven.
  const actionRows = a.rows.filter((r) => r.govern !== 'no-mandate');

  const gc = a.verdict_counts.govern;
  const dc = a.verdict_counts.deploy;

  const lane = (v: string | null, map: Record<string, string>) =>
    v === null ? '—' : (
      <span className="pill whitespace-nowrap" style={{ background: map[v] ?? 'var(--border)', color: '#fff' }}>{v}</span>
    );

  return (
    <div className="px-4 md:px-8 py-6 max-w-[1400px] mx-auto space-y-6">
      <header>
        <p className="eyebrow">Fault-Line Radar · advisory</p>
        <h1 className="text-2xl font-extrabold tracking-tight text-[var(--text-strong)] leading-tight">
          Do you have to do this, and does it pay to put AI on it
        </h1>
        <p className="text-[13px] text-[var(--text)] max-w-[820px] mt-1.5 leading-relaxed">
          The first is whether you have to do it. If the answer is yes, bad economics are not a
          reason to skip it. The second is whether it pays to put AI on the work. A rule requiring
          something is not a reason to put AI on it.
        </p>
        <p className="text-[13px] text-[var(--text)] max-w-[820px] mt-1.5 leading-relaxed">
          &ldquo;You have to&rdquo; comes in two kinds, and they need different responses. A{' '}
          <b>duty</b> is something the law already requires, so the choice is comply or risk being
          sanctioned. A <b>market norm</b> is something your peers have started doing, so the choice
          is match it or lose work. The two are never blended into one answer.
        </p>
        <p className="text-[13px] text-[var(--text)] max-w-[820px] mt-1.5 leading-relaxed">
          A market norm only counts if someone with something to withhold actually requires it. An
          insurer who can drop your coverage. A client who can take the engagement elsewhere. A high
          adoption score on its own is not enough.
        </p>
        <p className="text-[13px] text-[var(--text)] max-w-[820px] mt-1.5 leading-relaxed">
          Where the evidence behind a call is thin, the page says so. A requirement from a carrier
          you named yourself clears that bar, because one carrier requiring something of you is a
          stronger signal than several requiring it of the market in general.
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
      <div className="card p-4 space-y-3">
        <div>
          <p className="text-[11px] text-[var(--text-muted)] uppercase tracking-wider font-semibold">Economic gate</p>
          <p className="font-mono text-lg font-extrabold text-[var(--text-strong)]">
            {money(a.economic_gate.delta_per_lawyer)}<span className="text-[11px] font-normal text-[var(--text-muted)]"> / lawyer / yr under {a.firm.pricing}</span>
          </p>
        </div>
        <div>
          <p className="text-[11px] text-[var(--text-muted)] uppercase tracking-wider font-semibold">Govern</p>
          <p className="font-mono text-[13px] text-[var(--text-strong)]">{gc['stand-up-now'] ?? 0} stand up · {gc['build-capacity-first'] ?? 0} build capacity · {gc['match-the-market'] ?? 0} match market{gc['no-mandate'] ? ` · ${gc['no-mandate']} with nothing to do, not shown` : ''}</p>
        </div>
        <div>
          <p className="text-[11px] text-[var(--text-muted)] uppercase tracking-wider font-semibold">Deploy</p>
          <p className="font-mono text-[13px] text-[var(--text-strong)]">{dc['deploy-now'] ?? 0} deploy · {dc['fix-pricing-first'] ?? 0} fix pricing · {dc['defer'] ?? 0} defer</p>
        </div>
      </div>

      {/* rows */}
      <div className="card overflow-hidden">
        <p className="px-4 pt-3 pb-1 text-[11.5px] text-[var(--text-muted)]">
          Ordered for you: duties before market norms, and within each, the shortest
          measured lead first — a control whose antecedents historically bound in 192
          days gives less warning than one that bound in 907, so it is nearer the top.
          That rule reads only the record and no firm input, which is why the radar
          board carries the same order.
        </p>
        <div className="grid grid-cols-[1fr_13rem_12rem_7rem] gap-2 px-4 py-2 border-b border-[var(--border)] text-[9.5px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
          <span># · Control · fault line</span><span>GOVERN · stand up?</span><span>DEPLOY · put AI on it?</span><span>L2 · L3 · E</span>
        </div>
        {[...actionRows].sort((x, y) => x.sequence - y.sequence).map((r) => (
          <div key={r.fault_line} className="grid grid-cols-[1fr_13rem_12rem_7rem] gap-2 px-4 py-2.5 items-center border-b border-[var(--border)] last:border-0 hover:bg-[var(--sunken)]">
            <span>
              <span className="font-mono text-[11px] text-[var(--text-muted)] mr-2">{r.sequence}</span>
              <span className="text-[13px] font-semibold text-[var(--text-strong)]">
                {r.control}
                {r.mandated && <span className="ml-2 text-[9px] font-bold uppercase tracking-wider text-[var(--rose)]">duty</span>}
                {r.expected && <span className="ml-2 text-[9px] font-bold uppercase tracking-wider text-[var(--amber)]">norm</span>}
                {r.leverage_is_yours && <span className="ml-2 text-[9px] font-bold uppercase tracking-wider text-[var(--metric)]">your carrier</span>}
                {r.confidence === 'thin' && <span className="ml-2 text-[9px] font-bold uppercase tracking-wider text-[var(--slate)]">thin</span>}
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
