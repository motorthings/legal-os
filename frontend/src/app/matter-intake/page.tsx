'use client';

import { useState } from 'react';
import { evaluateMatter } from '@/lib/matter-intake-api';
import type { AppState } from '@/lib/matter-intake-types';
import MatterInput from '@/components/matter-intake/MatterInput';
import EmptyState from '@/components/matter-intake/EmptyState';
import LoadingState from '@/components/matter-intake/LoadingState';
import ErrorState from '@/components/matter-intake/ErrorState';
import ResultsDisplay from '@/components/matter-intake/ResultsDisplay';
import CreateMatter from '@/components/matter-intake/CreateMatter';

export default function MatterIntakePage() {
  const [state, setState] = useState<AppState>({ status: 'empty' });
  const [summary, setSummary] = useState('');

  const handleSubmit = async (summary: string) => {
    setState({ status: 'loading' });
    try {
      const data = await evaluateMatter(summary);
      setSummary(summary);
      setState({ status: 'success', data });
    } catch (err) {
      setState({
        status: 'error',
        error: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  };

  const handleReset = () => setState({ status: 'empty' });

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-4xl font-bold tracking-tight text-[var(--text)] mt-3 mb-2">
          Matter Intake & Triage
        </h1>
        <p className="font-mono text-sm text-[var(--text-dim)] max-w-xl">
          Paste a matter summary to receive AI-powered classification, conflict
          check, risk assessment, and staffing recommendations.
        </p>
      </header>

      <MatterInput
        onSubmit={handleSubmit}
        disabled={state.status === 'loading'}
      />

      <div className="mt-8">
        {state.status === 'empty' && <EmptyState />}
        {state.status === 'loading' && <LoadingState />}
        {state.status === 'error' && (
          <ErrorState error={state.error} onRetry={handleReset} />
        )}
        {state.status === 'success' && (
          <>
            <ResultsDisplay data={state.data} onReset={handleReset} />
            <div className="mt-6">
              <CreateMatter summary={summary} data={state.data} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
