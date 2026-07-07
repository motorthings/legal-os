interface ScoreCardProps {
  name: string;
  score: number;
  weight: number;
  reasoning: string;
}

function scoreColor(score: number): string {
  if (score >= 70) return "#059669";
  if (score >= 40) return "#d97706";
  return "#dc2626";
}

export default function ScoreCard({ name, score, weight, reasoning }: ScoreCardProps) {
  const color = scoreColor(score);

  return (
    <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-default)] p-6 flex flex-col">
      <div className="flex items-start justify-between mb-3">
        <h4 className="text-sm font-medium text-[var(--text-primary)] leading-tight">
          {name}
        </h4>
        <span className="text-xs text-[var(--text-secondary)] bg-[var(--bg-secondary)] px-2 py-0.5 rounded-full whitespace-nowrap ml-2 font-mono">
          {Math.round(weight * 100)}%
        </span>
      </div>

      <div className="flex items-baseline gap-1 mb-3">
        <span className="text-2xl font-bold font-mono" style={{ color }}>
          {score}
        </span>
        <span className="text-sm text-[var(--text-tertiary)]">/100</span>
      </div>

      <div className="h-1.5 rounded-full bg-[var(--bg-secondary)] mb-3 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${score}%`, background: color }}
        />
      </div>

      <p className="text-xs text-[var(--text-secondary)] leading-relaxed mt-auto">
        {reasoning}
      </p>
    </div>
  );
}
