"use client";

import { useState } from "react";
import { evaluateMatter } from "@/lib/api";
import type { AppState } from "@/lib/types";
import MatterInput from "@/components/MatterInput";
import EmptyState from "@/components/EmptyState";
import LoadingState from "@/components/LoadingState";
import ErrorState from "@/components/ErrorState";
import ResultsDisplay from "@/components/ResultsDisplay";

export default function EvaluatePage() {
  const [state, setState] = useState<AppState>({ status: "empty" });

  const handleSubmit = async (summary: string) => {
    setState({ status: "loading" });
    try {
      const data = await evaluateMatter(summary);
      setState({ status: "success", data });
    } catch (err) {
      setState({
        status: "error",
        error: err instanceof Error ? err.message : "Unknown error",
      });
    }
  };

  const handleReset = () => setState({ status: "empty" });

  return (
    <div>
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--text-primary)] tracking-tight">
          Document Matter Intake Evaluation
        </h1>
        <p className="text-[var(--text-secondary)] mt-1 text-sm leading-relaxed">
          Paste a matter summary to receive AI-powered classification, conflict
          check, risk assessment, and staffing recommendations.
        </p>
      </header>

      <MatterInput
        onSubmit={handleSubmit}
        disabled={state.status === "loading"}
      />

      <div className="mt-8">
        {state.status === "empty" && <EmptyState />}
        {state.status === "loading" && <LoadingState />}
        {state.status === "error" && (
          <ErrorState error={state.error} onRetry={handleReset} />
        )}
        {state.status === "success" && (
          <ResultsDisplay data={state.data} onReset={handleReset} />
        )}
      </div>
    </div>
  );
}
