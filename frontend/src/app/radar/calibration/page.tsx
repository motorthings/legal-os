'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

/* ------------------------------------------------------------------ types */

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
interface Rate {
  n: number;
  hits: number;
  hit_rate: number | null;
}
interface Calibration {
  resolutions: Resolution[];
  hits: number;
  n_resolutions: number;
  hit_rate: number;
  by_order: Record<string, Rate>;
  by_sample: Record<string, Rate>;
  knobs_frozen_at: string;
  call_threshold: number;
  lead_days: number;
  precision: {
    precision: number | null;
    recall: number | null;
    lift: number | null;
    flag_rate: number | null;
    base_rate: number;
    tp: number;
    fp: number;
    fn: number;
    tn: number;
  };
  seed_ablation: {
    seed_dependence: number | null;
    default_seeds: { hit_rate: number | null };
    neutral_seeds: { hit_rate: number | null };
  };
}

/* -------------------------------------------------------------- constants */

const ORDER_LABEL: Record<string, string> = { '1': 'L1 capability', '2': 'L2 ruling', '3': 'L3 adoption' };
const dec = (n: number) => n.toFixed(1);
const pct = (n: number | null | undefined) => (n == null ? '—' : `${Math.round(n * 100)}%`);

/* ------------------------------------------------------------------- page */

export default function CalibrationPage() {
  const [cal, setCal] = useState<Calibration | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const c = await fetch('/radar/calibration.json').then((r) => r.json());
        if (!cancelled) setCal(c);
      } catch {
        if (!cancelled) setError('Could not load calibration data.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (error) return <div className="p-8 text-[var(--rose)]">{error}</div>;
  if (!cal) return <div className="p-8 text-[var(--text-muted)] font-mono text-sm">Loading calibration…</div>;

  const recall = cal.hit_rate;
  const prec = cal.precision;
  const ab = cal.seed_ablation;
  const inSample = cal.by_sample?.in_sample;
  const outSample = cal.by_sample?.out_of_sample;

  return (
    <div className="px-4 md:px-8 py-6 max-w-[1100px] mx-auto space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Fault-Line Radar · Calibration</p>
          <h1 className="text-2xl font-extrabold tracking-tight text-[var(--text-strong)] leading-tight">
            Does the engine actually call it?
          </h1>
          <p className="font-mono text-[12px] text-[var(--text-muted)] mt-1.5">
            {cal.n_resolutions} real events · threshold {cal.call_threshold} · {cal.lead_days} days lead · knobs frozen {cal.knobs_frozen_at}
          </p>
        </div>
        <Link href="/radar" className="btn-secondary no-underline">← back to the radar</Link>
      </header>

      {/* the honest headline: recall, and the two sides that temper it */}
      <div className="grid md:grid-cols-3 gap-4">
        <div className="card p-4">
          <p className="eyebrow mb-1">Recall</p>
          <p className="font-mono text-3xl font-extrabold text-[var(--text-strong)]">{pct(recall)}</p>
          <p className="text-[12px] text-[var(--text-muted)] mt-1 leading-snug">
            {cal.hits} of {cal.n_resolutions} real rulings were already flagged {cal.lead_days} days early.
          </p>
        </div>
        <div className="card p-4">
          <p className="eyebrow mb-1">Precision</p>
          <p className="font-mono text-3xl font-extrabold text-[var(--text-strong)]">{pct(prec?.precision)}</p>
          <p className="text-[12px] text-[var(--text-muted)] mt-1 leading-snug">
            of everything flagged, how much produced a ruling. Flag rate {pct(prec?.flag_rate)} · base rate {pct(prec?.base_rate)} · lift {prec?.lift == null ? '—' : `${prec.lift.toFixed(2)}×`}.
          </p>
        </div>
        <div className="card p-4">
          <p className="eyebrow mb-1">Seed dependence</p>
          <p className="font-mono text-3xl font-extrabold text-[var(--text-strong)]">{ab?.seed_dependence == null ? '—' : `${ab.seed_dependence.toFixed(2)}`}</p>
          <p className="text-[12px] text-[var(--text-muted)] mt-1 leading-snug">
            share of calls resting on the analyst seed, not evidence. Default {pct(ab?.default_seeds.hit_rate)} → neutral {pct(ab?.neutral_seeds.hit_rate)}.
          </p>
        </div>
      </div>

      {/* holdout: the retrodiction vs. real-track-record split */}
      <section className="card p-5">
        <p className="eyebrow mb-1">Forward-only holdout</p>
        <p className="text-[13px] text-[var(--text)] leading-relaxed mb-4">
          Knobs and the curated feed were authored knowing how these events came out. So anything dated on or before {cal.knobs_frozen_at} is <b>retrodiction</b> — a sanity check, not a track record. Only rulings <b>after</b> the freeze count as a real forecast.
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-lg border border-[var(--border)] p-4">
            <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)] mb-1">In-sample (retrodiction)</p>
            <p className="font-mono text-2xl font-extrabold text-[var(--text-strong)]">{pct(inSample?.hit_rate)}</p>
            <p className="text-[11px] text-[var(--text-muted)]">{inSample?.hits ?? 0}/{inSample?.n ?? 0} · tuned on the outcome — not a track record</p>
          </div>
          <div className="rounded-lg border border-[var(--border)] p-4">
            <p className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)] mb-1">Out-of-sample (real forecast)</p>
            <p className="font-mono text-2xl font-extrabold text-[var(--primary)]">{pct(outSample?.hit_rate)}</p>
            <p className="text-[11px] text-[var(--text-muted)]">{outSample?.hits ?? 0}/{outSample?.n ?? 0} · post-freeze rulings — the honest score, still empty</p>
          </div>
        </div>
      </section>

      {/* recall by stage */}
      <section>
        <p className="eyebrow mb-3">Recall by stage</p>
        <div className="grid grid-cols-3 gap-3">
          {['1', '2', '3'].map((o) => {
            const b = cal.by_order[o];
            if (!b) return null;
            return (
              <div key={o} className="card p-4 text-center">
                <p className="font-mono text-2xl font-extrabold text-[var(--text-strong)]">{pct(b.hit_rate)}</p>
                <p className="text-[11px] text-[var(--text-muted)] mt-0.5">{ORDER_LABEL[o]} · {b.hits}/{b.n}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* resolutions table */}
      <section>
        <p className="eyebrow mb-1">Every event, graded</p>
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
          The L1 misses are honest: first-of-kind capability jumps with no precursor to call from. The engine reports them as misses rather than tuning them away. Precision (not recall) is the number that can't be gamed — a model that pins every line high scores perfect recall and zero skill.
        </p>
      </section>
    </div>
  );
}
