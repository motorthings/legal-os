'use client';

// The 10-second answer: the decision in one sentence and a two-sided comparison —
// where you land if nothing changes vs. where you'd be if you pull the recommended
// levers. Built from structured payload numbers, not markdown, so the hero can't
// drift from the report.

const fmtM = (v?: number | null) => (v == null ? '—' : `$${(v / 1_000_000).toFixed(2)}M`);

const LEVER_LABEL: Record<string, string> = {
  pricing: 'flat fees',
  seams: 'codified hand-offs',
  comp: 'pay partners to use AI',
  latency: 'act on results faster',
  leverage: 'a flatter pyramid',
};

interface Props {
  reportedPPP: number | null;
  baseline: number | null;   // the no-changes projection
  recovered: number | null;  // the recommended (levered) projection
  levers: string[];
  sprints?: number | null;   // the horizon, in quarters
}

function Side({ label, value, accent, delta }: { label: string; value: string; accent?: boolean; delta?: string | null }) {
  return (
    <div className="p-4 rounded-lg" style={{ background: 'var(--surface2)' }}>
      <div className="text-[11px] font-medium text-[var(--text-dim)] mb-1">{label}</div>
      <div className="text-2xl font-bold font-mono" style={{ color: accent ? 'var(--primary)' : 'var(--text)' }}>
        {value}
      </div>
      {delta && <div className="mt-1 text-[12px] font-medium" style={{ color: 'var(--text-dim)' }}>{delta}</div>}
    </div>
  );
}

export default function SimulationHero({ reportedPPP, baseline, recovered, levers, sprints }: Props) {
  if (recovered == null || baseline == null) return null;
  const seq = levers.map((l) => LEVER_LABEL[l] ?? l).join(' → ');
  const delta = recovered - baseline;
  const horizon = sprints != null && sprints > 0
    ? `over ${sprints} quarters`
    : 'over the run';
  const deltaTxt = delta > 0 ? `+${fmtM(delta)}` : fmtM(delta);

  return (
    <div className="card p-6 mb-6" style={{ borderColor: 'var(--primary)' }}>
      <div className="text-[15px] font-semibold text-[var(--text)] leading-relaxed">
        {reportedPPP != null && <>The firm is at <strong>{fmtM(reportedPPP)}</strong> a partner today. </>}
        Do nothing and it settles around <strong>{fmtM(baseline)}</strong> {horizon}. Pull{' '}
        {seq ? <strong>{seq}</strong> : 'these levers'} and it rises to <strong>{fmtM(recovered)}</strong> —{' '}
        a <strong style={{ color: 'var(--primary)' }}>{deltaTxt}</strong> difference.
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-5">
        <Side label="If nothing changes" value={fmtM(baseline)} delta={horizon} />
        <Side label="With the recommendation" value={fmtM(recovered)} accent delta={`${deltaTxt} vs standing still`} />
      </div>

      {levers.length > 0 && (
        <div className="mt-4 text-[13px] text-[var(--text-dim)]">
          <span className="font-medium text-[var(--text)]">The move:</span> {seq}
        </div>
      )}
    </div>
  );
}
