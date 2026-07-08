'use client';

import { useState } from 'react';
import { pollRegulatory } from '@/lib/regulatory-api';
import type { RegulatoryAnalysis } from '@/lib/regulatory-api';
import { Send, RefreshCw, AlertTriangle, Globe, Building2, MapPin } from 'lucide-react';

type State =
  | { status: 'empty' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'success'; data: RegulatoryAnalysis };

function impactColor(level: string) {
  switch (level) {
    case 'critical': return { bg: 'rgba(239,68,68,0.1)', text: '#ef4444', border: 'rgba(239,68,68,0.2)', label: 'Critical' };
    case 'high': return { bg: 'rgba(239,68,68,0.08)', text: '#f97316', border: 'rgba(249,115,22,0.2)', label: 'High' };
    case 'medium': return { bg: 'rgba(245,158,11,0.1)', text: '#f59e0b', border: 'rgba(245,158,11,0.2)', label: 'Medium' };
    case 'low': return { bg: 'rgba(34,197,94,0.1)', text: '#22c55e', border: 'rgba(34,197,94,0.2)', label: 'Low' };
    default: return { bg: 'rgba(100,100,100,0.1)', text: '#888', border: 'rgba(100,100,100,0.2)', label: 'Unknown' };
  }
}

function statusColor(status: string) {
  switch (status) {
    case 'active': return '#22c55e';
    case 'pending': return '#f59e0b';
    case 'monitoring': return '#888';
    default: return '#888';
  }
}

export default function RegulatoryPage() {
  const [value, setValue] = useState('');
  const [state, setState] = useState<State>({ status: 'empty' });

  const handleSubmit = async () => {
    const text = value.trim();
    if (!text) return;
    setState({ status: 'loading' });
    try {
      const data = await pollRegulatory(text);
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
          Regulatory Change Monitor
        </h1>
        <p className="font-mono text-sm text-[var(--text-dim)] max-w-xl">
          Poll regulatory sources, map changes to active matters by jurisdiction,
          and flag impacted clients automatically.
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
            placeholder={`Describe the regulatory landscape or jurisdiction to monitor...

Examples:
- "Monitor California employment law changes for Q3 2026 — wage & hour, classification, and paid leave updates"
- "Track SEC rulemaking on climate disclosure, crypto custody, and private fund adviser rules across federal register"
- "State-level data privacy: Colorado CPA amendments, Texas TDPSA enforcement, and Oregon OCPA rulemaking"`}
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
              <Globe className="w-4 h-4" />
              Poll Sources
            </button>
          </div>
        </div>
      )}

      <div className="mt-8">
        {/* Empty */}
        {state.status === 'empty' && (
          <div className="card p-6 text-center py-16">
            <div className="w-12 h-12 rounded-xl bg-[var(--primary-dim)] flex items-center justify-center mx-auto mb-4 border border-[var(--primary)]/20">
              <Globe className="w-6 h-6 text-[var(--primary)]" />
            </div>
            <h3 className="text-lg font-semibold text-[var(--text)] mb-2">Ready to monitor</h3>
            <p className="text-sm text-[var(--text-dim)] mb-8 max-w-md mx-auto">
              Describe a jurisdiction or regulatory domain and the system will scan across
              federal register, state bulletins, and agency guidance.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-xl mx-auto">
              {['Multi-Source Polling', 'Impact Mapping', 'Automated Flags'].map((d) => (
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
              <p className="text-sm text-[var(--text-dim)]">Polling regulatory sources across jurisdictions...</p>
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
                <h3 className="text-sm font-semibold text-[var(--rose)] mb-1">Polling failed</h3>
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
                  <h2 className="text-lg font-semibold text-[var(--text)]">Regulatory Scan Results</h2>
                  <p className="text-xs text-[var(--text-muted)] mt-1 font-mono">
                    {state.data.sources.length} sources · {state.data.changes.length} changes · {state.data.processing_time_ms.toLocaleString()}ms · {state.data.model_used}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {state.data.flags.critical > 0 && (
                    <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-[var(--rose)]/10 text-[var(--rose)] font-mono">
                      {state.data.flags.critical} critical
                    </span>
                  )}
                  {state.data.flags.high > 0 && (
                    <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-[#f97316]/10 text-[#f97316] font-mono">
                      {state.data.flags.high} high
                    </span>
                  )}
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-[#22c55e]/10 text-[#22c55e] font-mono">
                    {state.data.flags.medium + state.data.flags.low} low/med
                  </span>
                </div>
              </div>
            </div>

            {/* Sources */}
            <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
              Monitored Sources
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
              {state.data.sources.map((s) => (
                <div key={s.source} className="card p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: statusColor(s.status) }} />
                    <div>
                      <h4 className="text-sm font-medium text-[var(--text)]">{s.source}</h4>
                      <p className="text-xs text-[var(--text-dim)]">{s.jurisdiction} · {s.agency}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-mono font-semibold text-[var(--text)]">{s.relevance}%</span>
                    <p className="text-[10px] text-[var(--text-muted)] uppercase">{s.status}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Changes */}
            <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
              Detected Changes
            </h3>
            <div className="space-y-3 mb-6">
              {state.data.changes.map((c) => {
                const imp = impactColor(c.impact_level);
                return (
                  <div key={c.id} className="card p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-sm font-semibold text-[var(--text)]">{c.title}</h4>
                          <span
                            className="text-[10px] font-medium px-1.5 py-0.5 rounded-full uppercase"
                            style={{ background: imp.bg, color: imp.text }}
                          >
                            {imp.label}
                          </span>
                        </div>
                        <p className="text-xs text-[var(--text-dim)] mb-2">{c.summary}</p>
                        <div className="flex items-center gap-3 text-[10px] text-[var(--text-muted)] font-mono">
                          <span className="inline-flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            {c.jurisdiction}
                          </span>
                          <span className="inline-flex items-center gap-1">
                            <Building2 className="w-3 h-3" />
                            {c.agency}
                          </span>
                          <span>Effective: {c.effective_date}</span>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-1 flex-shrink-0">
                        {c.affected_practice_areas.map((pa) => (
                          <span key={pa} className="text-[10px] px-1.5 py-0.5 rounded border font-mono" style={{ borderColor: 'var(--border)', color: 'var(--text-dim)' }}>
                            {pa}
                          </span>
                        ))}
                      </div>
                    </div>
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
                Run Another Scan
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
