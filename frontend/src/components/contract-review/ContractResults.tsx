import type { ContractAnalysis } from '@/lib/contract-review-api';
import { RefreshCw, AlertTriangle, ShieldCheck, ShieldAlert } from 'lucide-react';

interface Props {
  data: ContractAnalysis;
  onReset: () => void;
}

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

export default function ContractResults({ data, onReset }: Props) {
  const risk = riskColor(data.overall_risk_level);

  return (
    <div>
      {/* Overall score */}
      <div className="card p-6 mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h2 className="text-lg font-semibold text-[var(--text)]">Analysis Results</h2>
            <p className="text-xs text-[var(--text-muted)] mt-1 font-mono">
              {data.processing_time_ms.toLocaleString()}ms · {data.model_used}
            </p>
          </div>
          <div
            className="inline-flex items-center gap-3 px-4 py-2.5 rounded-full border"
            style={{ background: risk.bg, borderColor: risk.border }}
          >
            <span className="text-sm font-semibold" style={{ color: risk.text }}>{risk.label}</span>
            <span
              className="text-xs font-medium px-2 py-0.5 rounded-full font-mono"
              style={{ background: risk.border, color: risk.text }}
            >
              {data.overall_score}/100
            </span>
          </div>
        </div>
      </div>

      {/* Clause analysis */}
      <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
        Clause Analysis
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {data.clauses.map((clause) => {
          const color = scoreColor(clause.score);
          return (
            <div key={clause.name} className="card p-5">
              <div className="flex items-start justify-between mb-3">
                <h4 className="text-sm font-medium text-[var(--text)]">{clause.name}</h4>
                <span
                  className="text-xs font-medium px-2 py-0.5 rounded-full font-mono"
                  style={{ background: riskColor(clause.risk).bg, color: riskColor(clause.risk).text }}
                >
                  {clause.risk.toUpperCase()}
                </span>
              </div>
              <div className="flex items-baseline gap-1 mb-3">
                <span className="text-2xl font-bold font-mono" style={{ color }}>{clause.score}</span>
                <span className="text-sm text-[var(--text-muted)]">/100</span>
              </div>
              <div className="h-1.5 rounded-full bg-[var(--surface2)] mb-3 overflow-hidden">
                <div className="h-full rounded-full transition-all duration-500" style={{ width: `${clause.score}%`, background: color }} />
              </div>
              <p className="text-xs text-[var(--text-dim)] leading-relaxed">{clause.reasoning}</p>
            </div>
          );
        })}
      </div>

      {/* Obligations */}
      {data.obligations.length > 0 && (
        <>
          <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
            Obligations
          </h3>
          <div className="grid grid-cols-1 gap-2 mb-6">
            {data.obligations.map((o, i) => (
              <div key={i} className="card p-4 flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-[var(--text)]">{o.party}</span>
                  <p className="text-xs text-[var(--text-dim)] mt-0.5">{o.description}</p>
                </div>
                <span className="text-xs font-mono text-[var(--text-muted)]">{o.deadline}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Recommendations */}
      {data.recommendations.length > 0 && (
        <>
          <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
            Recommendations
          </h3>
          <div className="card p-5 mb-6">
            {data.recommendations.map((r, i) => (
              <div key={i} className="flex items-start gap-2 py-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: 'var(--amber, #f59e0b)' }} />
                <p className="text-sm text-[var(--text)]">{r}</p>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Reset */}
      <div className="text-center">
        <button
          onClick={onReset}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-[var(--primary)] bg-[var(--primary-dim)] border border-[var(--primary)]/20 hover:opacity-80 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Analyze Another Contract
        </button>
      </div>
    </div>
  );
}
