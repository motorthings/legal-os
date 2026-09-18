'use client';

import { useEffect, useRef, useState, type ReactNode } from 'react';
import Link from 'next/link';

/* ------------------------------------------------------------------ types */

interface FaultLine {
  id: string;
  title: string;
  control: string;
  horizon: string;
  vector: string;
  capability: number;
  pressure: number;
  adoption: number;
  enable: number;
  software: number;
  queue: number;
  lead: string;
  is_duty: boolean;
  /** The shared ordering tuple, from radar/ordering.py. Lower sorts first. */
  order_key?: number[];
  model_rules: string[];
}
interface RadarData {
  as_of: string;
  n_items: number;
  fault_lines: FaultLine[];
  tiers: Record<string, { label: string; weight: number; desc: string }>;
}

/* ------------------------------------------------------------ scroll reveal */

function Reveal({
  children,
  delay = 0,
  className = '',
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (
      typeof IntersectionObserver === 'undefined' ||
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      setShown(true);
      return;
    }
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            setShown(true);
            obs.disconnect();
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -60px 0px' },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: shown ? 1 : 0,
        transform: shown ? 'none' : 'translateY(24px)',
        transition: `opacity 0.6s cubic-bezier(0.22,1,0.36,1) ${delay}ms, transform 0.6s cubic-bezier(0.22,1,0.36,1) ${delay}ms`,
        willChange: 'opacity, transform',
      }}
    >
      {children}
    </div>
  );
}

/* -------------------------------------------------------------- meter cell */

function meterColor(v: number): string {
  if (v >= 8.5) return 'var(--rose)';
  if (v >= 7) return 'var(--amber)';
  if (v >= 5) return 'var(--metric)';
  return 'var(--text-muted)';
}

/* -------------------------------------------------------------- section */

function Part({
  n,
  title,
  lede,
  children,
  delay = 0,
}: {
  n: string;
  title: string;
  lede: string;
  children: ReactNode;
  delay?: number;
}) {
  return (
    <Reveal delay={delay}>
      <section className="mt-12">
        <p className="eyebrow mb-1">Part {n}</p>
        <h2 className="text-xl font-extrabold tracking-tight text-[var(--text-strong)] mb-2">
          {title}
        </h2>
        <p className="text-[14px] text-[var(--text)] leading-relaxed max-w-3xl mb-5">{lede}</p>
        {children}
      </section>
    </Reveal>
  );
}

/* ------------------------------------------------------------------- page */

export default function ReferencePage() {
  const [data, setData] = useState<RadarData | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Read the flag threshold from the calibration output rather than restating it, the same
  // way the radar page does. The Python side already shipped one drift bug from a hardcoded
  // threshold whose comment claimed to be this number.
  const [callThreshold, setCallThreshold] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [d, c] = await Promise.all([
          fetch('/radar/data.json').then((r) => r.json()),
          fetch('/radar/calibration.json').then((r) => r.json()).catch(() => null),
        ]);
        if (!cancelled) {
          setData(d);
          setCallThreshold(c?.call_threshold ?? null);
        }
      } catch {
        if (!cancelled) setError('Could not load radar data.');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <div className="p-8 text-[var(--rose)]">{error}</div>;
  if (!data) return <div className="p-8 text-[var(--text-muted)] font-mono text-sm">Loading…</div>;

  // Duties first, then the lines not required yet. Within the duties, the shared ordering
  // rule from radar/ordering.py: shortest measured warning window first. This used to sort
  // by `queue`, which is now an internal sort rather than a public claim, so the reference
  // was presenting a superseded order under a heading that promised the current one.
  const lines = [...data.fault_lines].sort((a, b) => {
    if (a.is_duty !== b.is_duty) return a.is_duty ? -1 : 1;
    if (a.is_duty && a.order_key && b.order_key) {
      for (let i = 0; i < Math.max(a.order_key.length, b.order_key.length); i++) {
        const d = (a.order_key[i] ?? 0) - (b.order_key[i] ?? 0);
        if (d !== 0) return d;
      }
    }
    return b.pressure - a.pressure;
  });
  const tiers = Object.entries(data.tiers);

  return (
    <div className="max-w-4xl mx-auto pb-16">
      {/* hero */}
      <Reveal>
        <header className="pt-2 pb-4">
          <p className="eyebrow">Fault-Line Radar · reference</p>
          <h1 className="text-3xl font-extrabold tracking-tight text-[var(--text-strong)] leading-tight mt-1">
            The whole picture, in one scroll
          </h1>
          <p className="text-[15px] text-[var(--text)] leading-relaxed max-w-2xl mt-3">
            What the radar reads off the record, how it scores, how evidence earns the right to move
            a meter — and what is building right now. Each part reveals as you reach it.
          </p>
          <p className="font-mono text-[12px] text-[var(--text-muted)] mt-2">
            {data.as_of} · {data.n_items}{' '}tracked items · deterministic &amp; replayable
          </p>
        </header>
      </Reveal>

      {/* part 1 — what it is */}
      <Part n="1" title="What it is" delay={0} lede="The radar tracks fault lines — the places a new AI capability rubs against an existing legal duty. It reports what the record already shows and how much warning it gave, not what happens next. Where a reading is a sort rather than a claim, the page says so.">
        <div className="grid md:grid-cols-3 gap-4">
          {[
            { tag: 'Part A', color: 'var(--primary)', q: 'Will a court, bar, or law move on this?', p: 'Graded against what actually happened. This is the part that earns trust by being scored, not by sounding sure.' },
            { tag: 'Part B', color: 'var(--metric)', q: 'What should a firm build and buy next?', p: 'Turns Part A into build-and-buy advice. Evidence-traced, never framed as a prediction.' },
            { tag: 'Part C', color: 'var(--amber)', q: 'Can this firm afford to act?', p: 'A what-if model of one firm\'s economics. On hourly billing more AI is a net loss; on fixed fee it\'s a net win.' },
          ].map((p) => (
            <div key={p.tag} className="card p-4" style={{ borderTop: `3px solid ${p.color}` }}>
              <p className="font-mono text-[10px] font-bold uppercase tracking-wider" style={{ color: p.color }}>{p.tag}</p>
              <p className="text-[14px] font-semibold text-[var(--text-strong)] mt-1.5 mb-1">{p.q}</p>
              <p className="text-[12px] text-[var(--text-muted)] leading-relaxed">{p.p}</p>
            </div>
          ))}
        </div>
        <div className="grid md:grid-cols-2 gap-4 mt-4">
          <div className="card p-4">
            <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-[var(--metric)] mb-2">The supply stack</p>
            <div className="space-y-1 text-[13px]">
              <p><span className="font-mono font-bold text-[var(--text)]">L1 capability</span> <span className="text-[var(--text-muted)]">— can the AI do the thing yet</span></p>
              <p><span className="font-mono font-bold text-[var(--text)]">S software</span> <span className="text-[var(--text-muted)]">— are legal-AI vendors enabled to build it</span></p>
              <p><span className="font-mono font-bold text-[var(--text)]">E enablement</span> <span className="text-[var(--text-muted)]">— can a firm stand the fix up with what the market sells</span></p>
            </div>
          </div>
          <div className="card p-4">
            <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-[var(--primary)] mb-2">The governance side</p>
            <div className="space-y-1 text-[13px]">
              <p><span className="font-mono font-bold text-[var(--text)]">L2 ruling</span> <span className="text-[var(--text-muted)]">— will a court, bar, or statute move on it</span></p>
              <p><span className="font-mono font-bold text-[var(--text)]">L3 adoption</span> <span className="text-[var(--text-muted)]">— is the fix becoming table stakes, court or no court</span></p>
            </div>
          </div>
        </div>
      </Part>

      {/* part 2 — fault lines */}
      <Part n="2" title="The eleven fault lines" delay={80} lede="Five meters each, 0 to 10. A control is required of a firm once ruling pressure reaches 8.0 on ruling evidence alone; the lines below that threshold are shown too, labelled as not yet required. Duties come first, then those, and within each the shortest measured warning window leads. That is the order the radar page uses.">
        <div className="card overflow-hidden">
          <div className="grid grid-cols-[1.6fr_0.75fr_0.75fr_0.75fr_0.75fr_0.8fr] gap-1 px-4 py-2 border-b border-[var(--border)] text-[9px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
            <span>Fault line</span><span className="text-center">Cap</span><span className="text-center">Soft</span><span className="text-center">Rule</span><span className="text-center">Adopt</span><span className="text-center">Enable</span>
          </div>
          {lines.map((f) => (
            <div key={f.id} className="grid grid-cols-[1.6fr_0.75fr_0.75fr_0.75fr_0.75fr_0.8fr] gap-1 px-4 py-2.5 items-center border-b border-[var(--border)] last:border-0">
              <div className="min-w-0">
                <p className="text-[13px] font-semibold text-[var(--text-strong)] leading-tight">
                  {f.title}
                  {f.is_duty ? (
                    <span className="ml-2 text-[9px] font-bold uppercase tracking-wider text-[var(--rose)]">duty</span>
                  ) : (
                    <span className="ml-2 text-[9px] font-bold uppercase tracking-wider text-[var(--text-muted)]">not required</span>
                  )}
                </p>
                <p className="text-[11px] text-[var(--text-muted)] truncate">{f.control}</p>
              </div>
              {[f.capability, f.software, f.pressure, f.adoption, f.enable].map((v, i) => (
                <span key={i} className="text-center font-mono text-[12px] font-bold" style={{ color: meterColor(v) }}>{v.toFixed(1)}</span>
              ))}
            </div>
          ))}
        </div>
        <p className="text-[12px] text-[var(--text-muted)] mt-3">
          The full interactive charts and evidence trails live on{' '}
          <Link href="/radar" className="text-[var(--primary)] hover:underline">the radar page</Link>.
        </p>
      </Part>

      {/* part 3 — how it scores */}
      <Part n="3" title="How it scores" delay={80} lede="Authority over volume. Every piece of evidence is stamped with a tier when it enters, and the tier decides the weight — not how many people repeated it.">
        <div className="card overflow-hidden">
          {tiers.map(([key, t]) => (
            <div key={key} className="grid grid-cols-[3rem_1fr_4rem] gap-2 px-4 py-2.5 items-center border-b border-[var(--border)] last:border-0">
              <span className="badge badge-low">{key}</span>
              <div className="min-w-0">
                <p className="text-[13px] font-semibold text-[var(--text-strong)]">{t.label}</p>
                <p className="text-[11px] text-[var(--text-muted)] truncate">{t.desc}</p>
              </div>
              <span className="text-right font-mono text-[13px] font-bold text-[var(--text)]">{t.weight}</span>
            </div>
          ))}
        </div>
        <p className="text-[12px] text-[var(--text-muted)] leading-relaxed mt-3 max-w-3xl">
          A vendor blog carries a hundred and twenty-fifth of a bar opinion, so it takes 125 of them
          to outweigh one ruling. Two things keep it honest: the <b className="text-[var(--text)]">L2
          ruling meter is two-sided</b> — an item can argue against a line and drag it down, not just
          up — and every capital event is <b className="text-[var(--text)]">flagged</b> continuation /
          origination / direction-shift, because a momentum signal can only predict continuation. A
          first-of-kind move is labeled, not scored as if it were predictable.
        </p>
      </Part>

      {/* part 4 — evidence */}
      <Part n="4" title="How evidence gets in" delay={80} lede="A fact does not enter the feed because someone found it. It enters because it survived being argued against.">
        <div className="space-y-0 max-w-lg mx-auto">
          {[
            { text: 'A fact is found on the internet', color: 'var(--primary)' },
            { text: 'Split the question, search it from several directions at once — including one angle that looks for where the story is wrong', color: 'var(--secondary)' },
            { text: 'Three independent reviewers each try to prove it false', color: 'var(--amber)' },
            { text: 'Does it survive two of three skeptics?', color: 'var(--metric)', gate: true },
            { text: 'Admitted and ranked — or killed. And if a date or amount cannot be verified, the honest answer is "we found nothing," not a guessed number', color: 'var(--rose)', gate: true },
          ].map((s, i, arr) => (
            <div key={i} className="flex flex-col items-center">
              <div className="w-full rounded-lg border-2 px-4 py-3 text-center text-[13px] font-semibold text-[var(--text-strong)]"
                style={{ background: 'var(--surface)', borderColor: s.color, borderStyle: s.gate ? 'dashed' : 'solid' }}>
                {s.text}
              </div>
              {i < arr.length - 1 && (
                <div className="py-1 font-mono text-[var(--text-muted)]">&darr;</div>
              )}
            </div>
          ))}
        </div>
        <p className="text-[12px] text-[var(--text-muted)] mt-4 text-center max-w-xl mx-auto">
          This is the step that caught real mistakes: a court rule only one source mentioned, a
          "disqualification" that was actually a reprimand, a claim about two vendors no source could hold up.
        </p>
      </Part>

      {/* part 5 — the decision model */}
      <Part n="5" title="How a line becomes an instruction" delay={80} lede="Scoring is what the record says. This is what it tells a firm to do, and the two are kept apart on purpose. Everything above is true of every firm; everything here depends on who you are.">
        <div className="grid md:grid-cols-2 gap-4">
          <div className="card p-4" style={{ borderTop: '3px solid var(--primary)' }}>
            <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-[var(--primary)]">Govern</p>
            <p className="text-[14px] font-semibold text-[var(--text-strong)] mt-1.5 mb-1">Do you have to do this?</p>
            <p className="text-[12px] text-[var(--text-muted)] leading-relaxed">
              Answered from the law and the market, never from the economics. A required control is
              never deferred because the AI math is poor. The billable hour does not excuse a firm
              from a competence program it is required to have.
            </p>
          </div>
          <div className="card p-4" style={{ borderTop: '3px solid var(--metric)' }}>
            <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-[var(--metric)]">Deploy</p>
            <p className="text-[14px] font-semibold text-[var(--text-strong)] mt-1.5 mb-1">Does it pay to put AI on the work?</p>
            <p className="text-[12px] text-[var(--text-muted)] leading-relaxed">
              A separate question with a separate answer. A rule requiring something is not a reason
              to put AI on it, and on hourly billing more AI is usually a net loss whatever the rule
              says.
            </p>
          </div>
        </div>

        <div className="card p-4 mt-4">
          <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-[var(--amber)] mb-2">Have to comes in two kinds, and they are never blended</p>
          <div className="space-y-2 text-[13px]">
            <p>
              <b className="text-[var(--text)]">A duty</b>{' '}
              <span className="text-[var(--text-muted)]">
                — the law has already moved. Ruling pressure at or above {(callThreshold ?? 8.0).toFixed(1)},
                on ruling evidence alone. The choice is comply or risk being sanctioned.
              </span>
            </p>
            <p>
              <b className="text-[var(--text)]">A market norm</b>{' '}
              <span className="text-[var(--text-muted)]">
                — your peers have started. The choice is match it or lose work.
              </span>
            </p>
          </div>
          <p className="text-[12px] text-[var(--text)] leading-relaxed mt-3 max-w-3xl">
            A norm only counts if <b>someone with something to withhold requires it</b>. An insurer who
            can drop your coverage. A client who can move the engagement. A platform that can withhold
            the docket. A high adoption score on its own is not enough, and that is deliberate: this is
            why the model does not use one.
          </p>
          <p className="text-[12px] text-[var(--text)] leading-relaxed mt-3 max-w-3xl">
            Leverage is <b>firm-relative</b>. A carrier you name yourself clears the evidence bar by
            itself, because one carrier requiring something of you is a stronger signal than two
            requiring it of the market in general. Naming your carrier is what turns a thin norm into a
            supported one.
          </p>
        </div>

        <p className="text-[12px] text-[var(--text-muted)] mt-3 max-w-3xl">
          Where the evidence behind a call is thin, the page says so rather than rounding up. Below the
          duty threshold a line is still shown, labelled as not yet required, with the reason it is
          worth watching. Run{' '}
          <Link href="/radar/advisory" className="text-[var(--primary)] hover:underline">the firm advisory</Link>{' '}
          to see these verdicts against a named posture.
        </p>
      </Part>

      {/* part 6 — watch next */}
      <Part n="6" title="What to watch next" delay={80} lede="The single most valuable signal in the whole system is the thing that has not happened yet.">
        <div className="card p-5" style={{ background: 'var(--metric-dim)', borderColor: 'var(--border-bright)' }}>
          <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-[var(--metric)] mb-1.5">The open signal</p>
          <p className="text-[14px] text-[var(--text)] leading-relaxed">
            Carriers have started asking. CNA added AI-governance questions to malpractice renewals and
            underwriting in June 2026, which is a questionnaire rather than a condition, and no bar has
            yet adopted a named benchmark. The event to watch is the step past asking: an insurer naming
            a certified tool as a condition of coverage. That is what flips the method layer from
            voluntary to enforceable.
          </p>
        </div>
        <p className="text-[12px] text-[var(--text-muted)] mt-3">
          Want the sources, the roadmap, and the full cited evidence? See{' '}
          <Link href="/radar/kb" className="text-[var(--primary)] hover:underline">the knowledge base</Link> and{' '}
          <Link href="/radar/advisory" className="text-[var(--primary)] hover:underline">the advisory</Link>.
        </p>
      </Part>
    </div>
  );
}
