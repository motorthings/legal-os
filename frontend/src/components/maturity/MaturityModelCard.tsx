"use client";

import { TrendingUp, AlertTriangle, ArrowRight } from "lucide-react";
import type { MaturityAssessment } from "@/lib/maturity-types";
import { LEVEL_LABELS, LEVEL_COLORS, DIM_LABELS } from "@/lib/maturity-types";

interface Props {
  assessment: MaturityAssessment;
}

export default function MaturityModelCard({ assessment }: Props) {
  const currentNum = assessment.overall_level;
  const bottleneckKey = assessment.bottleneck_dimension;
  const bottleneckName =
    DIM_LABELS[bottleneckKey] || bottleneckKey;
  const stageGaps = assessment.stage_gaps || [];
  const dimensions = assessment.dimensions || [];
  const nextLevel =
    currentNum < 5 ? LEVEL_LABELS[currentNum + 1] : "";
  const nextGapIndex = Math.max(0, currentNum - 1);
  const nextGap = stageGaps[nextGapIndex] || null;

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 mb-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <TrendingUp
          className="w-5 h-5"
          style={{ color: "var(--primary)" }}
        />
        <h3 className="text-lg font-semibold text-[var(--text)]">
          AI Maturity Assessment
        </h3>
      </div>

      {/* 5-stage scale bar */}
      <div className="mb-5">
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((level) => {
            const isCurrent = level === currentNum;
            const isPast = level < currentNum;
            const opacity = isCurrent
              ? "opacity-100"
              : isPast
                ? "opacity-50"
                : "opacity-20";
            return (
              <div key={level} className="flex-1 text-center">
                <div
                  className={`h-2.5 rounded-sm mb-1.5 ${LEVEL_COLORS[level]} ${opacity}`}
                />
                <p
                  className={`text-[10px] font-semibold ${opacity} text-[var(--text)]`}
                >
                  {LEVEL_LABELS[level]}
                </p>
                {isCurrent && (
                  <p className="text-[9px] text-[var(--text-muted)] italic mt-0.5">
                    You are here
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Current level card */}
      <div
        className="rounded-lg border p-4 mb-4"
        style={{
          borderColor: "var(--primary)",
          backgroundColor: "var(--primary-dim)",
        }}
      >
        <p
          className="text-xs font-semibold uppercase tracking-wider mb-1"
          style={{ color: "var(--primary)" }}
        >
          Current Level
        </p>
        <p className="text-base font-bold text-[var(--text)] mb-2">
          {assessment.overall_level_label}
        </p>
        {assessment.bottleneck_what_this_means && (
          <p className="text-sm text-[var(--text-dim)] mb-2 leading-relaxed">
            {assessment.bottleneck_what_this_means}
          </p>
        )}
        <div className="flex items-start gap-2 text-sm text-amber-600 dark:text-amber-400">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>
            <strong>Bottleneck:</strong> {bottleneckName}
            {assessment.bottleneck_why && (
              <span className="block text-xs mt-0.5 text-[var(--text-muted)]">
                {assessment.bottleneck_why}
              </span>
            )}
          </span>
        </div>
      </div>

      {/* Dimension Scorecard */}
      {dimensions.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-[var(--text)] mb-2">
            Dimension Scores
          </h4>
          <div className="space-y-1.5">
            {dimensions.map((dim, i) => {
              const dname =
                DIM_LABELS[dim.key] || dim.name || dim.key;
              const dscore = dim.score;
              const pct = (dscore / 5) * 100;
              const barColor =
                dscore >= 4
                  ? "bg-green-500"
                  : dscore >= 3
                    ? "bg-amber-500"
                    : "bg-red-500";
              return (
                <div key={i}>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-[var(--text-dim)] w-36 shrink-0 truncate">
                      {dname}
                    </span>
                    <div className="flex-1 h-1.5 bg-[var(--surface2)] rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${barColor}`}
                        style={{ width: `${Math.min(pct, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs font-semibold text-[var(--text)] w-5 text-right">
                      {dscore}
                    </span>
                  </div>
                  {dim.rationale && (
                    <p className="text-[10px] text-[var(--text-muted)] ml-[9.25rem] mt-0.5 line-clamp-1">
                      {dim.rationale}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Next level */}
      {nextLevel && (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface2)] p-4 mb-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-1">
            Next Level
          </p>
          <p className="text-sm font-semibold text-[var(--text)] mb-2">
            {nextLevel}
          </p>
          {nextGap && (
            <>
              <p className="text-sm text-[var(--text-dim)] mb-1">
                {nextGap.whats_missing}
              </p>
              {nextGap.what_it_unlocks && (
                <p
                  className="text-xs italic"
                  style={{ color: "var(--primary)" }}
                >
                  <ArrowRight className="w-3 h-3 inline mr-1" />
                  <strong>Unlocks:</strong> {nextGap.what_it_unlocks}
                </p>
              )}
            </>
          )}
        </div>
      )}

      {/* Stage gaps */}
      {stageGaps.length > 1 && (
        <div>
          <h4 className="text-sm font-semibold text-[var(--text)] mb-2">
            Path to Advancement
          </h4>
          <div className="space-y-2">
            {stageGaps.map((gap, i) => {
              const isPast = gap.from_level < currentNum;
              return (
                <div
                  key={i}
                  className={`rounded-lg border border-[var(--border)] p-3 ${
                    isPast ? "opacity-50" : ""
                  }`}
                >
                  <p className="text-xs font-medium text-[var(--text)] mb-0.5">
                    {gap.from_label} → {gap.to_label}
                    {isPast && (
                      <span className="ml-2 text-[10px] text-green-600 dark:text-green-400">
                        achieved
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-[var(--text-dim)]">
                    {gap.whats_missing}
                  </p>
                  {gap.what_it_unlocks && !isPast && (
                    <p
                      className="text-xs italic mt-0.5"
                      style={{ color: "var(--primary)" }}
                    >
                      Unlocks: {gap.what_it_unlocks}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
