'use client';

import { useEffect, useState } from 'react';

/* ------------------------------------------------------------------ types */

interface KbItem {
  date: string;
  tier: string;
  tier_label: string;
  tier_weight: number;
  title: string;
  source?: string;
  url?: string;
  empirical?: boolean;
  conflict?: boolean;
  capability?: string | null;
  market?: string | null;
  order?: number | null;
  what: string;
  role: string[];
  fault_lines: { id: string; title: string }[];
  why: string;
}
interface KnowledgeBase {
  n_items: number;
  items: KbItem[];
}

/* -------------------------------------------------------------- constants */

const ROLE_PILL: Record<string, string> = {
  'L1 capability': 'pill-brand',
  'L2 ruling': 'pill-warn',
  'L3 adoption': 'pill-success',
};

/* --------------------------------------------------------------- helpers */

const ROLE_LABEL: Record<string, string> = {
  'L1 capability': 'L1 · capability signal',
  'L2 ruling': 'L2 · ruling / authority',
  'L3 adoption': 'L3 · adoption signal',
};

/* ------------------------------------------------------------------ page */

export default function RadarKbPage() {
  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const d = await fetch('/radar/kb.json').then((r) => r.json());
        if (!cancelled) setKb(d);
      } catch {
        if (!cancelled) setError('Could not load the knowledge base.');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (error) return <div className="p-8 text-[var(--rose)]">{error}</div>;
  if (!kb) return <div className="p-8 text-[var(--text-muted)] font-mono text-sm">Loading knowledge base…</div>;

  const items = [...kb.items].sort((a, b) => a.date.localeCompare(b.date));

  return (
    <div className="space-y-8">
      {/* header */}
      <header>
        <p className="eyebrow">Predict · Knowledge base</p>
        <h1 className="text-2xl font-extrabold tracking-tight text-[var(--text-strong)] leading-tight">
          The source library behind the radar
        </h1>
        <p className="font-mono text-[12px] text-[var(--text-muted)] mt-1.5">
          {kb.n_items} source docs · every one weighted by authority, not volume
        </p>
      </header>

      {/* primer */}
      <div className="card p-5 space-y-2">
        <p className="eyebrow">What this is</p>
        <p className="text-[13px] text-[var(--text)] leading-relaxed">
          Each reading on the radar is moved by the documents below. Every source
          carries a <b>what it is</b> and a <b>why it&rsquo;s in the KB</b> — the
          provenance behind a number. Nothing is in here on volume alone.
        </p>
        <p className="text-[12px] text-[var(--text-muted)] leading-relaxed">
          The &ldquo;why&rdquo; is derived, not authored: tier authority, the lane the
          source feeds (L1 capability, L2 ruling, L3 adoption), the fault line(s) it
          evidences, and any empirical or conflict flags. Replayable like every score.
        </p>
      </div>

      {/* the library */}
      <section>
        <div className="flex items-baseline justify-between mb-3">
          <p className="eyebrow">All source docs</p>
          <p className="font-mono text-[11px] text-[var(--text-muted)]">oldest → newest</p>
        </div>
        <div className="space-y-3">
          {items.map((it, i) => (
            <article key={`${it.date}-${i}`} className="card p-4">
              <div className="flex flex-wrap items-center gap-2 mb-1.5">
                <span className="badge badge-low">{it.tier} <span className="opacity-70">{it.tier_label}</span></span>
                <span className="text-[13px] font-semibold text-[var(--text-strong)] leading-snug">
                  {it.url ? (
                    <a href={it.url} target="_blank" rel="noreferrer"
                      className="hover:text-[var(--primary)] underline decoration-[var(--border-strong)] underline-offset-2">{it.title}</a>
                  ) : it.title}
                </span>
                <span className="ml-auto inline-flex flex-wrap gap-1.5">
                  {it.role.map((r) => (
                    <span key={r} className={`pill ${ROLE_PILL[r] ?? 'pill-warn'}`} title={ROLE_LABEL[r] ?? r}>{r}</span>
                  ))}
                  {it.empirical && <span className="pill pill-success">data</span>}
                  {it.conflict && <span className="pill pill-warn">conflict</span>}
                </span>
              </div>
              <p className="text-[11px] font-mono text-[var(--text-muted)] mb-2.5">
                {it.source}{it.source && it.date ? ' · ' : ''}{it.date}
              </p>
              {it.what && (
                <p className="text-[13px] text-[var(--text)] leading-relaxed mb-2">
                  <b className="text-[var(--text-strong)]">What it is.</b> {it.what}
                </p>
              )}
              {it.why && (
                <p className="text-[12px] text-[var(--text-muted)] leading-relaxed mb-2.5">
                  <b className="text-[var(--text-strong)]">Why it&rsquo;s in the KB.</b> {it.why}
                </p>
              )}
              {it.fault_lines.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {it.fault_lines.map((fl) => (
                    <span key={fl.id} className="badge badge-low normal-case">{fl.title}</span>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      </section>

      <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
        Figures reflect the tracked feed at generation time — verify primary sources
        before relying on any number.
      </p>
    </div>
  );
}
