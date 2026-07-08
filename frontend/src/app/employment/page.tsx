'use client';

import { useState } from 'react';
import { analyzeEmployment } from '@/lib/employment-api';
import type { EmploymentAnalysis } from '@/lib/employment-api';
import { Send, RefreshCw, AlertTriangle } from 'lucide-react';

type State =
  | { status: 'empty' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'success'; data: EmploymentAnalysis };

function riskColor(level: string) {
  switch (level) {
    case 'high': return { bg: 'rgba(239,68,68,0.1)', text: '#ef4444', border: 'rgba(239,68,68,0.2)', label: 'High Risk' };
    case 'medium': return { bg: 'rgba(245,158,11,0.1)', text: '#f59e0b', border: 'rgba(245,158,11,0.2)', label: 'Medium Risk' };
    case 'low': return { bg: 'rgba(34,197,94,0.1)', text: '#22c55e', border: 'rgba(34,197,94,0.2)', label: 'Low Risk' };
    default: return { bg: 'rgba(100,100,100,0.1)', text: '#888', border: 'rgba(100,100,100,0.2)', label: 'Unknown' };
  }
}

function scoreColor(score: number) {
  if (score >= 70) return '#22c55e';
  if (score >= 40) return '#f59e0b';
  return '#ef4444';
}

export default function EmploymentPage() {
  const [value, setValue] = useState('');
  const [state, setState] = useState<State>({ status: 'empty' });

  const handleSubmit = async () => {
    const text = value.trim();
    if (!text) return;
    setState({ status: 'loading' });
    try {
      const data = await analyzeEmployment(text);
      setState({ status: 'success', data });
    } catch (err) {
      setState({
        status: 'error',
        error: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  };

  const handleReset = () => {
    setValue('');
    setState({ status: 'empty' });
  };

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-4xl font-bold tracking-tight text-[var(--text)] mt-3 mb-2">
          Employment Legal Agents
        </h1>
        <p className="font-mono text-sm text-[var(--text-dim)] max-w-xl">
          AI agents for employment law — policy review, worker classification analysis,
          compliance auditing with jurisdiction-aware reasoning.
        </p>
      </header>

      {/* Input */}
      {state.status !== 'success' && (
        <div className="card p-6">
          <textarea
            rows={12}
            disabled={state.status === 'loading'}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder={`Paste an employment policy, handbook excerpt, or worker classification scenario...

Examples:
- "Our company uses 1099 contractors for core product development roles. They work full-time, use company equipment, and report to engineering managers..."
- "Employee handbook section 4.2: Overtime policy for exempt vs non-exempt employees in California..."`}
            className="w-full rounded-lg border border-[var(--border)] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/50 focus:border-transparent resize-y disabled:opacity-50 font-mono"
            style={{ background: 'var(--surface2)' }}
          />
          <div className="mt-3 flex items-center justify-between">
            <span className="text-xs text-[var(--text-muted)] font-mono">{value.length.toLocaleString()} chars</span>
            <button
              onClick={handleSubmit}
              disabled={state.status === 'loading' || !value.trim()}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white bg-[var(--primary)] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-4 h-4" />
              Analyze Employment Matter
            </button>
          </div>
        </div>
      )}

      <div className="mt-8">
        {/* Empty */}
        {state.status === 'empty' && (
          <div className="card p-6 text-center py-16">
            <div className="w-12 h-12 rounded-xl bg-[var(--primary-dim)] flex items-center justify-center mx-auto mb-4 border border-[var(--primary)]/20">
              <svg className="w-6 h-6 text-[var(--primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0M12 12.75h.008v.008H12v-.008z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-[var(--text)] mb-2">Ready to evaluate</h3>
            <p className="text-sm text-[var(--text-dim)] mb-8 max-w-md mx-auto">
              Paste an employment policy, contractor classification scenario, or handbook excerpt
              for AI analysis across compliance dimensions.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-xl mx-auto">
              {['Worker Classification', 'FLSA Compliance', 'Handbook Audit'].map((d) => (
                <div key={d} className="p-3 rounded-lg border" style={{ background: 'var(--surface2)', borderColor: 'var(--border)' }}>
                  <div className="text-xs font-medium text-[var(--text)]">{d}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Loading */}
        {state.status === 'loading' && (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-5 h-5 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-[var(--text-dim)]">Analyzing employment matter...</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[1, 2, 3, 4].map((i) => (
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

        {/* Error */}
        {state.status === 'error' && (
          <div className="card p-6 border-l-4 border-l-[var(--rose)]">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-[var(--rose)] flex-shrink-0 mt-0.5" />
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

        {/* Success */}
        {state.status === 'success' && (
          <div>
            {/* Overall */}
            <div className="card p-6 mb-6">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-[var(--text)]">Analysis Results</h2>
                  <p className="text-xs text-[var(--text-muted)] mt-1 font-mono">
                    {state.data.processing_time_ms.toLocaleString()}ms · {state.data.model_used}
                  </p>
                </div>
                <div
                  className="inline-flex items-center gap-3 px-4 py-2.5 rounded-full border"
                  style={{ background: riskColor(state.data.overall_risk_level).bg, borderColor: riskColor(state.data.overall_risk_level).border }}
                >
                  <span className="text-sm font-semibold" style={{ color: riskColor(state.data.overall_risk_level).text }}>
                    {riskColor(state.data.overall_risk_level).label}
                  </span>
                  <span
                    className="text-xs font-medium px-2 py-0.5 rounded-full font-mono"
                    style={{ background: riskColor(state.data.overall_risk_level).border, color: riskColor(state.data.overall_risk_level).text }}
                  >
                    {state.data.overall_score}/100
                  </span>
                </div>
              </div>
            </div>

            {/* Classification */}
            <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
              Worker Classification
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              <div className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-[var(--text)]">Contractor Misclassification Risk</h4>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full font-mono ${state.data.classification.contractor_risk >= 70 ? 'bg-[var(--rose)]/10 text-[var(--rose)]' : state.data.classification.contractor_risk >= 40 ? 'bg-[var(--amber)]/10 text-[var(--amber)]' : 'bg-[var(--metric-dim)] text-[var(--metric)]'}`}>
                    {state.data.classification.contractor_risk}/100
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-[var(--surface2)] mb-3 overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-500" style={{ width: `${state.data.classification.contractor_risk}%`, background: scoreColor(state.data.classification.contractor_risk) }} />
                </div>
                <p className="text-xs text-[var(--text-dim)]">{state.data.classification.reasoning}</p>
              </div>
              <div className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-medium text-[var(--text)]">Exemption Classification Risk</h4>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full font-mono ${state.data.classification.exempt_risk >= 70 ? 'bg-[var(--rose)]/10 text-[var(--rose)]' : state.data.classification.exempt_risk >= 40 ? 'bg-[var(--amber)]/10 text-[var(--amber)]' : 'bg-[var(--metric-dim)] text-[var(--metric)]'}`}>
                    {state.data.classification.exempt_risk}/100
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-[var(--surface2)] mb-3 overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-500" style={{ width: `${state.data.classification.exempt_risk}%`, background: scoreColor(state.data.classification.exempt_risk) }} />
                </div>
                <p className="text-xs text-[var(--text-dim)]">{state.data.classification.reasoning}</p>
              </div>
            </div>

            {/* Compliance dimensions */}
            <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
              Compliance Review
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {state.data.compliance.map((c) => {
                const color = scoreColor(c.score);
                return (
                  <div key={c.dimension} className="card p-5">
                    <div className="flex items-start justify-between mb-3">
                      <h4 className="text-sm font-medium text-[var(--text)]">{c.dimension}</h4>
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full font-mono" style={{ background: riskColor(c.risk).bg, color: riskColor(c.risk).text }}>
                        {c.risk.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex items-baseline gap-1 mb-3">
                      <span className="text-2xl font-bold font-mono" style={{ color }}>{c.score}</span>
                      <span className="text-sm text-[var(--text-muted)]">/100</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-[var(--surface2)] mb-3 overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${c.score}%`, background: color }} />
                    </div>
                    <p className="text-xs text-[var(--text-dim)]">{c.reasoning}</p>
                  </div>
                );
              })}
            </div>

            {/* Recommendations */}
            {state.data.recommendations.length > 0 && (
              <>
                <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
                  Recommendations
                </h3>
                <div className="card p-5 mb-6">
                  {state.data.recommendations.map((r, i) => (
                    <div key={i} className="flex items-start gap-2 py-2">
                      <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: 'var(--amber, #f59e0b)' }} />
                      <p className="text-sm text-[var(--text)]">{r}</p>
                    </div>
                  ))}
                </div>
              </>
            )}

            <div className="text-center">
              <button
                onClick={handleReset}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-[var(--primary)] bg-[var(--primary-dim)] border border-[var(--primary)]/20 hover:opacity-80 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Analyze Another Matter
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
