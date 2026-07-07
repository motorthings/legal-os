"use client";

import { useEffect, useState } from "react";

export default function LoadingState() {
  const [stage, setStage] = useState<"classifying" | "evaluating">("classifying");

  useEffect(() => {
    const t1 = setTimeout(() => setStage("evaluating"), 2000);
    return () => clearTimeout(t1);
  }, []);

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-5 h-5 border-2 border-primary-400 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-[var(--text-secondary)]">
          {stage === "classifying"
            ? "Classifying practice area..."
            : "Evaluating across 5 dimensions..."}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-default)] p-6">
            <div className="animate-pulse space-y-3">
              <div className="h-4 bg-[var(--bg-secondary)] rounded w-32" />
              <div className="h-8 bg-[var(--bg-secondary)] rounded w-16" />
              <div className="h-2 bg-[var(--bg-secondary)] rounded w-full" />
              <div className="h-3 bg-[var(--bg-secondary)] rounded w-full" />
              <div className="h-3 bg-[var(--bg-secondary)] rounded w-3/4" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
