'use client';

// The 10-second answer: the recovery story in one sentence plus a three-number strip,
// before any charts or the full report. Built from structured payload numbers, not
// markdown, so the hero can't drift from the report.

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
  baseline: number | null;
  recovered: number | null;
  levers: string[];
}

function KPI({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="p-4 rounded-lg" style={{ background: 'var(--surface2)' }}>
      <div className="text-[11px] font-medium text-[var(--text-dim)] mb-1">{label}</div>
      <div className="text-2xl font-bold font-mono" style={{ color: accent ? 'var(--primary)' : 'var(--text)' }}>
        {value}
      </div>
    </div>
  );
}

export default function SimulationHero({ reportedPPP, baseline, recovered, levers }: Props) {
  if (recovered == null || baseline == null) return null;
  const seq = levers.map((l) => LEVER_LABEL[l] ?? l).join(' → ');

  return (
    <div className="card p-6 mb-6" style={{ borderColor: 'var(--primary)' }}>
      <div className="text-[15px] font-semibold text-[var(--text)] leading-relaxed">
        {reportedPPP != null ? (
          <>
            The firm reports <strong>{fmtM(reportedPPP)}</strong> a partner, but the model prices that
            at <strong>{fmtM(baseline)}</strong> once rework and write-offs are counted. The plan lifts
            it back to <strong>{fmtM(recovered)}</strong>.
          </>
        ) : (
          <>
            The plan lifts profit per partner from <strong>{fmtM(baseline)}</strong> back to{' '}
            <strong>{fmtM(recovered)}</strong>.
          </>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-5">
        <KPI label="Reported" value={fmtM(reportedPPP)} />
        <KPI label="What it's really worth" value={fmtM(baseline)} />
        <KPI label="Recovered" value={fmtM(recovered)} accent />
      </div>

      {levers.length > 0 && (
        <div className="mt-4 text-[13px] text-[var(--text-dim)]">
          <span className="font-medium text-[var(--text)]">The move:</span> {seq}
        </div>
      )}
    </div>
  );
}
