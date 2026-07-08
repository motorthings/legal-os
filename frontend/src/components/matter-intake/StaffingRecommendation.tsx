import type { StaffingRecommendation as Staffing } from "@/lib/matter-intake-types";
import { Users } from "lucide-react";

interface StaffingRecommendationProps {
  staffing: Staffing;
}

export default function StaffingRecommendation({ staffing }: StaffingRecommendationProps) {
  return (
    <div className="bg-[var(--surface)] rounded-xl border border-[var(--border)] p-6">
      <h4 className="text-sm font-medium text-[var(--text)] mb-3">
        Staffing Recommendation
      </h4>

      <div className="flex items-center gap-2 mb-3">
        <Users className="w-4 h-4 text-[var(--primary)]" />
        <span className="text-base font-semibold text-[var(--text)]">
          {staffing.recommended_role}
        </span>
      </div>

      {staffing.estimated_hours > 0 && (
        <p className="text-xs text-[var(--text-dim)] mb-3 font-mono">
          Estimated: {staffing.estimated_hours.toLocaleString()} hours
        </p>
      )}

      <p className="text-xs text-[var(--text-dim)] leading-relaxed">
        {staffing.reasoning}
      </p>
    </div>
  );
}
