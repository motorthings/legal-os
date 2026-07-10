'use client';

import { useState, useEffect } from 'react';
import { getROISummary, getQualitySummary, getAdoptionRate, type ROISummary, type QualitySummary, type AdoptionRate, type FunctionROI } from '@/lib/roi-api';
import { Clock, DollarSign, TrendingUp, Users, Shield, BarChart3, RefreshCw, Info } from 'lucide-react';

function formatUSD(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
}

function formatHours(n: number): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n);
}

function roiColor(ratio: number | null): string {
  if (!ratio) return 'var(--text-muted)';
  if (ratio >= 10) return '#22c55e';
  if (ratio >= 5) return '#f59e0b';
  return '#ef4444';
}

function adoptionColor(pct: number): string {
  if (pct >= 60) return '#22c55e';
  if (pct >= 30) return '#f59e0b';
  return '#ef4444';
}

export default function DashboardPage() {
  const [roi, setRoi] = useState<ROISummary | null>(null);
  const [quality, setQuality] = useState<QualitySummary | null>(null);
  const [adoption, setAdoption] = useState<AdoptionRate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [periodDays, setPeriodDays] = useState(90);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [roiData, qualityData, adoptionData] = await Promise.all([
        getROISummary(periodDays),
        getQualitySummary(periodDays),
        getAdoptionRate(undefined, 30),
      ]);
      setRoi(roiData);
      setQuality(qualityData);
      setAdoption(adoptionData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [periodDays]);

  if (loading) {
    return (
      <div>
        <header className="mb-6">
          <h1 className="text-4xl font-bold tracking-tight text-[var(--text)] mt-3 mb-2">Portfolio Dashboard</h1>
          <p className="font-mono text-sm text-[var(--text-dim)]">Loading metrics...</p>
        </header>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="h-4 bg-[var(--surface2)] rounded w-24 mb-3" />
              <div className="h-8 bg-[var(--surface2)] rounded w-16" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <header className="mb-6">
          <h1 className="text-4xl font-bold tracking-tight text-[var(--text)] mt-3 mb-2">Portfolio Dashboard</h1>
        </header>
        <div className="card p-6 border-l-4 border-l-[var(--rose)]">
          <p className="text-sm text-[var(--rose)]">{error}</p>
          <button onClick={fetchData} className="mt-3 px-4 py-2 rounded-lg text-sm font-medium text-white bg-[var(--primary)]">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <header className="mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-4xl font-bold tracking-tight text-[var(--text)] mt-3 mb-2">
              Portfolio Dashboard
            </h1>
            <p className="font-mono text-sm text-[var(--text-dim)] max-w-xl">
              Adoption, client outcomes, and return on innovation — across all AI functions.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {[30, 90, 180, 365].map((d) => (
              <button
                key={d}
                onClick={() => setPeriodDays(d)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-colors ${
                  periodDays === d
                    ? 'bg-[var(--primary)] text-white'
                    : 'text-[var(--text-dim)] hover:text-[var(--text)]'
                }`}
                style={periodDays !== d ? { background: 'var(--surface2)' } : {}}
              >
                {d}d
              </button>
            ))}
            <button
              onClick={fetchData}
              className="ml-2 p-2 rounded-lg hover:opacity-80 transition-colors"
              style={{ background: 'var(--surface2)' }}
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4 text-[var(--text-dim)]" />
            </button>
          </div>
        </div>
      </header>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-[var(--primary)]" />
            <span className="text-xs font-medium text-[var(--text-dim)]">Hours Saved</span>
          </div>
          <div className="text-3xl font-bold font-mono text-[var(--text)]">
            {formatHours(roi?.summary.total_hours_saved || 0)}
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1">
            {periodDays}d period · {formatHours((roi?.summary.total_hours_saved || 0) * 4)} annualized
          </div>
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="w-4 h-4 text-[var(--primary)]" />
            <span className="text-xs font-medium text-[var(--text-dim)]">Cost Avoided</span>
          </div>
          <div className="text-3xl font-bold font-mono text-[var(--text)]">
            {formatUSD(roi?.summary.total_cost_avoided_usd || 0)}
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1">
            @ {formatUSD(roi?.summary.hourly_rate_usd || 0)}/hr blended
          </div>
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-[var(--primary)]" />
            <span className="text-xs font-medium text-[var(--text-dim)]">Net ROI</span>
          </div>
          <div className="text-3xl font-bold font-mono" style={{ color: roiColor(roi?.summary.roi_ratio ?? null) }}>
            {roi?.summary.roi_ratio ? `${roi.summary.roi_ratio}:1` : '—'}
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1">
            {formatUSD(roi?.summary.net_roi_usd || 0)} net return
          </div>
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-4 h-4 text-[var(--primary)]" />
            <span className="text-xs font-medium text-[var(--text-dim)]">Adoption</span>
          </div>
          <div className="text-3xl font-bold font-mono" style={{ color: adoptionColor(adoption?.adoption_pct || 0) }}>
            {adoption?.adoption_pct ?? 0}%
          </div>
          <div className="text-xs text-[var(--text-muted)] mt-1">
            {adoption?.active_count ?? 0} of {adoption?.eligible_count ?? 0} eligible users
          </div>
        </div>
      </div>

      {/* Function Breakdown */}
      <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
        Return on Innovation by Function
      </h3>
      <div className="card mb-6" style={{ overflow: 'visible' }}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)]">
              <th className="text-left p-4 text-xs font-medium text-[var(--text-dim)]">Function</th>
              <th className="text-right p-4 text-xs font-medium text-[var(--text-dim)]">Invocations</th>
              <th className="text-right p-4 text-xs font-medium text-[var(--text-dim)]">Hours Saved</th>
              <th className="text-right p-4 text-xs font-medium text-[var(--text-dim)]">Cost Avoided</th>
              <th className="text-right p-4 text-xs font-medium text-[var(--text-dim)] overflow-visible">
                <span className="group relative inline-flex items-center gap-1 cursor-help">
                  AI Cost
                  <Info className="w-3 h-3" />
                  <span className="absolute top-full right-0 mt-2 w-64 p-3 rounded-lg text-xs font-normal text-left leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50"
                    style={{ background: 'var(--surface)', border: '1px solid var(--border)', boxShadow: '0 4px 12px rgba(0,0,0,0.3)', color: 'var(--text)' }}>
                    <span className="block font-semibold mb-1" style={{ color: 'var(--primary)' }}>Per-invocation pipeline cost</span>
                    Each invocation runs 3–6 LLM calls:<br/>
                    Router (classify) → Evaluator (reason)<br/>
                    → Hallucination check → Parallel verification<br/>
                    → Programmatic scoring<br/>
                    <span className="block mt-1 text-[var(--text-muted)]">Cost varies by function: $8–$300</span>
                  </span>
                </span>
              </th>
              <th className="text-right p-4 text-xs font-medium text-[var(--text-dim)]">Net ROI</th>
            </tr>
          </thead>
          <tbody>
            {(roi?.by_function || []).map((fn: FunctionROI) => (
              <tr key={fn.function_id} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--surface2)] transition-colors">
                <td className="p-4">
                  <div className="text-sm font-medium text-[var(--text)]">{fn.name}</div>
                  <div className="text-[10px] text-[var(--text-muted)] font-mono">{fn.slug}</div>
                </td>
                <td className="p-4 text-right font-mono text-[var(--text)]">{fn.invocations.toLocaleString()}</td>
                <td className="p-4 text-right font-mono text-[var(--text)]">{formatHours(fn.hours_saved)}</td>
                <td className="p-4 text-right font-mono text-[var(--text)]">{formatUSD(fn.cost_avoided_usd)}</td>
                <td className="p-4 text-right font-mono text-[var(--text-dim)]">{formatUSD(fn.ai_cost_usd)}</td>
                <td className="p-4 text-right font-mono" style={{ color: fn.net_roi_usd >= 0 ? '#22c55e' : '#ef4444' }}>
                  {formatUSD(fn.net_roi_usd)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Quality + Total bar */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quality Metrics */}
        <div>
          <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
            Quality Metrics
          </h3>
          <div className="card p-5">
            {quality && quality.total_reviews > 0 ? (
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-[var(--text-dim)]">Accuracy Rate</span>
                  <span className="text-sm font-bold font-mono" style={{ color: (quality.accuracy_rate ?? 0) >= 85 ? '#22c55e' : '#f59e0b' }}>
                    {quality.accuracy_rate}%
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-[var(--surface2)] overflow-hidden">
                  <div className="h-full rounded-full bg-[var(--primary)]" style={{ width: `${quality.accuracy_rate || 0}%` }} />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-[var(--text-dim)]">Override Rate</span>
                  <span className="text-sm font-bold font-mono" style={{ color: (quality.override_rate ?? 100) <= 15 ? '#22c55e' : '#ef4444' }}>
                    {quality.override_rate}%
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-[var(--text-dim)]">False Positive Rate</span>
                  <span className="text-sm font-bold font-mono text-[var(--text)]">{quality.false_positive_rate}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-[var(--text-dim)]">Avg Agreement Score</span>
                  <span className="text-sm font-bold font-mono text-[var(--text)]">{quality.avg_agreement_score}%</span>
                </div>
                <div className="text-xs text-[var(--text-muted)] mt-2">
                  {quality.total_reviews} reviews · {(quality.accuracy_rate ?? 0) >= 85 ? 'On target' : 'Needs attention'}
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <Shield className="w-8 h-8 text-[var(--text-muted)] mx-auto mb-2" />
                <p className="text-sm text-[var(--text-dim)]">No quality reviews yet</p>
                <p className="text-xs text-[var(--text-muted)] mt-1">Record quality reviews to populate metrics</p>
              </div>
            )}
          </div>
        </div>

        {/* Bar Chart: Hours Saved */}
        <div>
          <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
            Hours Saved by Function
          </h3>
          <div className="card p-5 space-y-3">
            {(roi?.by_function || []).sort((a, b) => b.hours_saved - a.hours_saved).map((fn) => {
              const maxHours = Math.max(...(roi?.by_function || []).map(f => f.hours_saved), 1);
              const pct = (fn.hours_saved / maxHours) * 100;
              return (
                <div key={fn.function_id}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-[var(--text)]">{fn.name}</span>
                    <span className="font-mono text-[var(--text-dim)]">{formatHours(fn.hours_saved)}h</span>
                  </div>
                  <div className="h-2 rounded-full bg-[var(--surface2)] overflow-hidden">
                    <div
                      className="h-full rounded-full bg-[var(--primary)] transition-all"
                      style={{ width: `${Math.max(pct, 2)}%` }}
                    />
                  </div>
                </div>
              );
            })}
            {(!roi?.by_function || roi.by_function.length === 0) && (
              <div className="text-center py-8">
                <BarChart3 className="w-8 h-8 text-[var(--text-muted)] mx-auto mb-2" />
                <p className="text-sm text-[var(--text-dim)]">No data yet</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
