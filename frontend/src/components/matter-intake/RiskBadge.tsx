interface RiskBadgeProps {
  level: "high" | "medium" | "low";
  score: number;
}

const CONFIG: Record<string, { bg: string; text: string; border: string; label: string }> = {
  high: {
    bg: "#1a0f12", text: "#f87171", border: "#3b1518",
    label: "High Risk",
  },
  medium: {
    bg: "#1a140b", text: "#fbbf24", border: "#3b2e0f",
    label: "Medium Risk",
  },
  low: {
    bg: "#0a1514", text: "#34d399", border: "#0f3d32",
    label: "Low Risk",
  },
};

export default function RiskBadge({ level, score }: RiskBadgeProps) {
  const c = CONFIG[level];

  return (
    <div
      className="inline-flex items-center gap-3 px-4 py-2.5 rounded-full border"
      style={{ background: c.bg, borderColor: c.border }}
    >
      <span className="text-sm font-semibold" style={{ color: c.text }}>
        {c.label}
      </span>
      <span
        className="text-xs font-medium px-2 py-0.5 rounded-full font-mono"
        style={{ background: c.border, color: c.text }}
      >
        {score}/100
      </span>
    </div>
  );
}
