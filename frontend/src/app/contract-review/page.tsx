'use client';

import { useState } from 'react';
import { analyzeContract } from '@/lib/contract-review-api';
import type { ContractAnalysis } from '@/lib/contract-review-api';
import ContractInput from '@/components/contract-review/ContractInput';
import ContractResults from '@/components/contract-review/ContractResults';

type State =
  | { status: 'empty' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'success'; data: ContractAnalysis };

export default function ContractReviewPage() {
  const [state, setState] = useState<State>({ status: 'empty' });

  const handleSubmit = async (text: string) => {
    setState({ status: 'loading' });
    try {
      const data = await analyzeContract(text);
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
          Contract Review & Analysis
        </h1>
        <p className="font-mono text-sm text-[var(--text-dim)] max-w-xl">
          Paste a contract clause or upload a document for AI-powered risk analysis,
          clause-level flagging, and obligation extraction.
        </p>
      </header>

      <ContractInput
        onSubmit={handleSubmit}
        disabled={state.status === 'loading'}
      />

      <div className="mt-8">
        {state.status === 'empty' && (
          <div className="card p-6 text-center py-16">
            <div className="w-12 h-12 rounded-xl bg-[var(--primary-dim)] flex items-center justify-center mx-auto mb-4 border border-[var(--primary)]/20">
              <svg className="w-6 h-6 text-[var(--primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-[var(--text)] mb-2">Ready to analyze</h3>
            <p className="text-sm text-[var(--text-dim)] mb-8 max-w-md mx-auto">
              Paste contract text above and the system will evaluate it across key
              dimensions: risk level, clause analysis, obligations, and recommendations.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 max-w-2xl mx-auto">
              {['Risk Assessment', 'Clause Analysis', 'Obligations', 'Recommendations'].map((d) => (
                <div key={d} className="p-3 rounded-lg border" style={{ background: 'var(--surface2)', borderColor: 'var(--border)' }}>
                  <div className="text-xs font-medium text-[var(--text)]">{d}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {state.status === 'loading' && (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-5 h-5 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-[var(--text-dim)]">Analyzing contract...</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="card p-6">
                  <div className="animate-pulse space-y-3">
                    <div className="h-4 bg-[var(--surface2)] rounded w-32" />
                    <div className="h-8 bg-[var(--surface2)] rounded w-16" />
                    <div className="h-2 bg-[var(--surface2)] rounded w-full" />
                    <div className="h-3 bg-[var(--surface2)] rounded w-full" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {state.status === 'error' && (
          <div className="card p-6 border-l-4 border-l-[var(--rose)]">
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 text-[var(--rose)] flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-[var(--rose)] mb-1">Analysis failed</h3>
                <p className="text-sm text-[var(--text-dim)] break-words">{state.error}</p>
                <button
                  onClick={handleReset}
                  className="mt-3 inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium text-white bg-[var(--primary)] hover:opacity-90 transition-colors"
                >
                  Try Again
                </button>
              </div>
            </div>
          </div>
        )}

        {state.status === 'success' && (
          <ContractResults data={state.data} onReset={handleReset} />
        )}
      </div>
    </div>
  );
}
