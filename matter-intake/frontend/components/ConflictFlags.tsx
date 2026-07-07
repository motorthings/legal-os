import type { ConflictEntry } from "@/lib/types";
import { ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";

interface ConflictFlagsProps {
  conflict: ConflictEntry;
}

const CONFIG: Record<string, { icon: typeof ShieldAlert; label: string; color: string }> = {
  direct_adverse: { icon: ShieldAlert, label: "Direct Adverse", color: "#dc2626" },
  business_conflict: { icon: ShieldQuestion, label: "Business Conflict", color: "#d97706" },
  none_identified: { icon: ShieldCheck, label: "None Identified", color: "#059669" },
};

export default function ConflictFlags({ conflict }: ConflictFlagsProps) {
  const c = CONFIG[conflict.conflict_type] || CONFIG.none_identified;
  const Icon = c.icon;

  return (
    <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-default)] p-6">
      <h4 className="text-sm font-medium text-[var(--text-primary)] mb-3">
        Conflict Check
      </h4>

      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-4 h-4" style={{ color: c.color }} />
        <span className="text-xs font-medium" style={{ color: c.color }}>
          {c.label}
        </span>
      </div>

      {conflict.entity_name && (
        <p className="text-sm text-[var(--text-primary)] mb-2">
          <span className="text-[var(--text-secondary)]">Entity:</span>{" "}
          <span className="font-medium">{conflict.entity_name}</span>
        </p>
      )}

      <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
        {conflict.detail}
      </p>
    </div>
  );
}
