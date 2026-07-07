import type { EvaluateResponse } from "@/lib/types";
import RiskBadge from "./RiskBadge";
import ScoreCard from "./ScoreCard";
import ConflictFlags from "./ConflictFlags";
import StaffingRecommendation from "./StaffingRecommendation";
import { RefreshCw } from "lucide-react";

interface ResultsDisplayProps {
  data: EvaluateResponse;
  onReset: () => void;
}

export default function ResultsDisplay({ data, onReset }: ResultsDisplayProps) {
  return (
    <div>
      {/* Overall header */}
      <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-default)] p-6 mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">
              Evaluation Results
            </h2>
            <p className="text-xs text-[var(--text-tertiary)] mt-1 font-mono">
              {data.processing_time_ms.toLocaleString()}ms · {data.model_used}
            </p>
          </div>
          <RiskBadge level={data.overall_risk_level} score={data.overall_score} />
        </div>
      </div>

      {/* Dimension score cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {data.dimension_scores.map((dim) => (
          <ScoreCard
            key={dim.dimension_name}
            name={dim.dimension_name}
            score={dim.score}
            weight={dim.weight}
            reasoning={dim.reasoning}
          />
        ))}
      </div>

      {/* Conflict + Staffing */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <ConflictFlags conflict={data.conflict_check} />
        <StaffingRecommendation staffing={data.staffing} />
      </div>

      {/* Reset */}
      <div className="text-center">
        <button
          onClick={onReset}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-primary-700 dark:text-primary-300 bg-primary-950/30 hover:bg-primary-950/50 border border-primary-500/20 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Evaluate Another Matter
        </button>
      </div>
    </div>
  );
}
