'use client';

import { useState } from 'react';
import { generateReport } from '@/lib/reporting-api';
import type { ReportingAnalysis } from '@/lib/reporting-api';
import { Send, RefreshCw, AlertTriangle, TrendingUp, TrendingDown, Minus, Clock, Shield, FileCheck } from 'lucide-react';

type State =
  | { status: 'empty' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'success'; data: ReportingAnalysis };

function trendIcon(trend: string) {
  switch (trend) {
    case 'up': return <TrendingUp className="w-4 h-4" style={{ color: '#22c55e' }} />;
    case 'down': return <TrendingDown className="w-4 h-4" style={{ color: '#ef4444' }} />;
    default: return <Minus className="w-4 h-4" style={{ color: '#f59e0b' }} />;
  }
}

function yoyColor(trend: string) {
  switch (trend) {
    case 'improving': return { bg: 'rgba(34,197,94,0.1)', text: '#22c55e', border: 'rgba(34,197,94,0.2)', label: 'Improving YoY' };
    case 'declining': return { bg: 'rgba(239,68,68,0.1)', text: '#ef4444', border: 'rgba(239,68,68,0.2)', label: 'Declining YoY' };
    default: return { bg: 'rgba(245,158,11,0.1)', text: '#f59e0b', border: 'rgba(245,158,11,0.2)', label: 'Stable YoY' };
  }
}

function savingsColor(pct: number) {
  if (pct >= 70) return '#22c55e';
  if (pct >= 40) return '#f59e0b';
  return '#ef4444';
}

export default function ReportingPage() {
  const [value, setValue] = useState('');
  const [state, setState] = useState<State>({ status: 'empty' });

  const handleSubmit = async () => {
    const text = value.trim();
    if (!text) return;
    setState({ status: 'loading' });
    try {
      const data = await generateReport(text);
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
          Client Value Reporting
        </h1>
        <p className="font-mono text-sm text-[var(--text-dim)] max-w-xl">
          Per-client quarterly reports — time saved, risk mitigated, and governance
          artifacts delivered, with year-over-year trend analysis.
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
            placeholder={`Describe the client or practice area for the value report...

Examples:
- "Generate Q3 2026 value report for Acme Corp — across all 7 Legal AI OS functions, with YoY comparison"
- "Quarterly client report: time saved, risk flags resolved, and governance artifacts for the employment practice"
- "Annual report for the litigation department — matter throughput, AI-assisted hours, and outcome trends"`}
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
              <FileCheck className="w-4 h-4" />
              Generate Report
            </button>
          </div>
        </div>
      )}

      <div className="mt-8">
        {/* Empty */}
        {state.status === 'empty' && (
          <div className="card p-6 text-center py-16">
            <div className="w-12 h-12 rounded-xl bg-[var(--primary-dim)] flex items-center justify-center mx-auto mb-4 border border-[var(--primary)]/20">
              <FileCheck className="w-6 h-6 text-[var(--primary)]" />
            </div>
            <h3 className="text-lg font-semibold text-[var(--text)] mb-2">Ready to report</h3>
            <p className="text-sm text-[var(--text-dim)] mb-8 max-w-md mx-auto">
              Describe a client, practice area, or time period to generate a value report
              with time savings, risk metrics, and governance artifacts.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-xl mx-auto">
              {['Time Saved', 'Risk Metrics', 'Governance Trail'].map((d) => (
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
              <p className="text-sm text-[var(--text-dim)]">Generating client value report...</p>
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

        {/* Error */}
        {state.status === 'error' && (
          <div className="card p-6 border-l-4 border-l-[var(--rose)]">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-[var(--rose)] flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-[var(--rose)] mb-1">Report generation failed</h3>
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
            {/* Overall header */}
            <div className="card p-6 mb-6">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-[var(--text)]">Client Value Report — {state.data.period}</h2>
                  <p className="text-xs text-[var(--text-muted)] mt-1 font-mono">
                    {state.data.processing_time_ms.toLocaleString()}ms · {state.data.model_used}
                  </p>
                </div>
                <div
                  className="inline-flex items-center gap-3 px-4 py-2.5 rounded-full border"
                  style={{ background: yoyColor(state.data.yoy_trend).bg, borderColor: yoyColor(state.data.yoy_trend).border }}
                >
                  <span className="text-sm font-semibold" style={{ color: yoyColor(state.data.yoy_trend).text }}>
                    {yoyColor(state.data.yoy_trend).label}
                  </span>
                </div>
              </div>

              {/* KPI row */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6">
                <div className="p-4 rounded-lg" style={{ background: 'var(--surface2)' }}>
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="w-4 h-4 text-[var(--primary)]" />
                    <span className="text-xs font-medium text-[var(--text-dim)]">Hours Saved</span>
                  </div>
                  <span className="text-3xl font-bold font-mono text-[var(--text)]">
                    {state.data.total_hours_saved.toLocaleString()}
                  </span>
                  <span className="text-sm text-[var(--text-dim)] ml-2">this quarter</span>
                </div>
                <div className="p-4 rounded-lg" style={{ background: 'var(--surface2)' }}>
                  <div className="flex items-center gap-2 mb-2">
                    <Shield className="w-4 h-4 text-[var(--primary)]" />
                    <span className="text-xs font-medium text-[var(--text-dim)]">Risk Flags Resolved</span>
                  </div>
                  <span className="text-3xl font-bold font-mono text-[var(--text)]">
                    {state.data.total_flags_resolved.toLocaleString()}
                  </span>
                  <span className="text-sm text-[var(--text-dim)] ml-2">flags</span>
                </div>
                <div className="p-4 rounded-lg" style={{ background: 'var(--surface2)' }}>
                  <div className="flex items-center gap-2 mb-2">
                    <FileCheck className="w-4 h-4 text-[var(--primary)]" />
                    <span className="text-xs font-medium text-[var(--text-dim)]">Artifacts</span>
                  </div>
                  <span className="text-3xl font-bold font-mono text-[var(--text)]">
                    {state.data.governance_artifacts.length.toLocaleString()}
                  </span>
                  <span className="text-sm text-[var(--text-dim)] ml-2">audit trail</span>
                </div>
              </div>
            </div>

            {/* Time Savings per Function */}
            <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
              Time Savings by Function
            </h3>
            <div className="space-y-3 mb-6">
              {state.data.time_savings.map((t) => {
                const color = savingsColor(t.percent_reduction);
                return (
                  <div key={t.function} className="card p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--text)]">{t.function}</span>
                        {trendIcon(t.trend)}
                      </div>
                      <div className="flex items-center gap-3 text-right">
                        <span className="text-xs text-[var(--text-dim)] font-mono">
                          {t.hours_saved}h saved ({t.baseline_hours}h → {t.ai_hours}h)
                        </span>
                        <span className="text-sm font-bold font-mono" style={{ color }}>{t.percent_reduction}%</span>
                      </div>
                    </div>
                    <div className="h-1.5 rounded-full bg-[var(--surface2)] overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${t.percent_reduction}%`, background: color }} />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Risk Metrics */}
            <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
              Risk Mitigation
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 mb-6">
              {state.data.risk_metrics.map((r) => (
                <div key={r.category} className="card p-5">
                  <h4 className="text-sm font-medium text-[var(--text)] mb-3">{r.category}</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-[var(--text-dim)]">Flags resolved</span>
                      <span className="font-mono text-[var(--text)]">{r.flags_resolved}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-[var(--text-dim)]">Gaps closed</span>
                      <span className="font-mono text-[var(--text)]">{r.gaps_closed}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-[var(--text-dim)]">Changes addressed</span>
                      <span className="font-mono text-[var(--text)]">{r.changes_addressed}</span>
                    </div>
                  </div>
                  <div className="mt-3 h-1.5 rounded-full bg-[var(--surface2)] overflow-hidden">
                    <div className="h-full rounded-full bg-[var(--primary)]" style={{ width: `${r.score}%` }} />
                  </div>
                </div>
              ))}
            </div>

            {/* Governance Trail */}
            <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
              Governance Artifacts
            </h3>
            <div className="card p-5 mb-6">
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {state.data.governance_artifacts.map((a) => (
                  <div key={a.id} className="flex items-center justify-between py-2 border-b last:border-0" style={{ borderColor: 'var(--border)' }}>
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-mono uppercase" style={{ background: 'var(--surface2)', color: 'var(--text-muted)' }}>
                        {a.type}
                      </span>
                      <div className="min-w-0">
                        <p className="text-sm text-[var(--text)] truncate">{a.description}</p>
                        <p className="text-[10px] text-[var(--text-muted)] font-mono">{a.matter} · {a.function}</p>
                      </div>
                    </div>
                    <span className="text-[10px] text-[var(--text-muted)] font-mono flex-shrink-0 ml-3">{a.date}</span>
                  </div>
                ))}
              </div>
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
                Generate Another Report
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
