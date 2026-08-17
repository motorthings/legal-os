'use client';

import { useEffect, useState } from 'react';
import {
  ShieldCheck, ShieldAlert, AlertTriangle, HelpCircle,
  BookOpen, GitBranch, Quote, Loader2, CheckCircle2, XCircle,
} from 'lucide-react';
import {
  getCaseStatus,
  getCaseSummary,
  getCitingCases,
  verifyQuote,
  type CaseStatus,
  type CaseSummary,
  type CitingCase,
} from '@/lib/legal-research-api';

function indicatorStyle(indicator?: string) {
  switch (indicator) {
    case 'positive':
      return { bg: 'rgba(34,197,94,0.12)', text: '#22c55e', border: 'rgba(34,197,94,0.25)', label: 'Good Law', icon: ShieldCheck };
    case 'negative':
      return { bg: 'rgba(239,68,68,0.12)', text: '#ef4444', border: 'rgba(239,68,68,0.25)', label: 'Bad Law', icon: ShieldAlert };
    case 'caution':
      return { bg: 'rgba(245,158,11,0.12)', text: '#f59e0b', border: 'rgba(245,158,11,0.25)', label: 'Caution', icon: AlertTriangle };
    default:
      return { bg: 'rgba(100,116,139,0.12)', text: '#94a3b8', border: 'rgba(100,116,139,0.25)', label: 'Untreated', icon: HelpCircle };
  }
}

export default function CaseDrillDown({ caseId }: { caseId: string }) {
  const [status, setStatus] = useState<CaseStatus | null>(null);
  const [summary, setSummary] = useState<CaseSummary | null>(null);
  const [citing, setCiting] = useState<CitingCase[]>([]);
  const [citingTotal, setCitingTotal] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [showFullSummary, setShowFullSummary] = useState(false);

  const [quote, setQuote] = useState('');
  const [quoteResult, setQuoteResult] = useState<{ found: boolean; matched_text?: string } | null>(null);
  const [quoteLoading, setQuoteLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      getCaseStatus(caseId),
      getCaseSummary(caseId),
      getCitingCases(caseId),
    ])
      .then(([s, sum, c]) => {
        if (cancelled) return;
        setStatus(s);
        setSummary(sum);
        setCiting((c.results || []).slice(0, 8));
        setCitingTotal(c.total_records);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [caseId]);

  const handleVerify = async () => {
    if (!quote.trim()) return;
    setQuoteLoading(true);
    setQuoteResult(null);
    try {
      const r = await verifyQuote(caseId, quote.trim());
      setQuoteResult(r);
    } catch {
      setQuoteResult({ found: false });
    } finally {
      setQuoteLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="mt-4 pt-4 border-t border-[var(--border)] flex items-center gap-2 text-sm text-[var(--text-muted)]">
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading citation intelligence…
      </div>
    );
  }

  const statusBadge = status ? indicatorStyle(status.indicator) : null;

  return (
    <div className="mt-4 pt-4 border-t border-[var(--border)] space-y-4">
      {/* Good-law status */}
      {status && statusBadge && (
        <div className="flex items-center gap-3">
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium font-mono"
            style={{ background: statusBadge.bg, color: statusBadge.text, border: `1px solid ${statusBadge.border}` }}
          >
            <statusBadge.icon className="w-3.5 h-3.5" />
            {statusBadge.label}
          </span>
          {status.category && (
            <span className="text-xs text-[var(--text-dim)] capitalize">{status.category}</span>
          )}
          {status.weight && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--surface2)] text-[var(--text-muted)] font-mono">
              {status.weight}
            </span>
          )}
        </div>
      )}

      {/* Summary */}
      {summary?.summary && (
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <BookOpen className="w-3.5 h-3.5 text-[var(--text-muted)]" />
            <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              Summary
            </span>
            {summary.author && <span className="text-xs text-[var(--text-dim)]">· {summary.author}</span>}
          </div>
          <p className="text-sm text-[var(--text-dim)] leading-relaxed">
            {showFullSummary ? summary.summary : summary.summary.slice(0, 500)}
            {summary.summary.length > 500 && !showFullSummary && '…'}
          </p>
          {summary.summary.length > 500 && (
            <button
              onClick={() => setShowFullSummary(!showFullSummary)}
              className="text-xs font-medium text-[var(--primary)] hover:opacity-80 mt-1"
            >
              {showFullSummary ? 'Show less' : 'Read full summary'}
            </button>
          )}
        </div>
      )}

      {/* Citing cases */}
      {citing.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <GitBranch className="w-3.5 h-3.5 text-[var(--text-muted)]" />
            <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              Cited by {citingTotal ?? citing.length} later case{citingTotal !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {citing.map((c) => {
              const b = indicatorStyle(c.case_level_indicator);
              const Icon = b.icon;
              return (
                <div key={c.case_id} className="flex items-start gap-3 p-2 rounded-lg" style={{ background: 'var(--surface2)' }}>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-[var(--text)] leading-snug">{c.title}</p>
                    <p className="text-[10px] font-mono text-[var(--text-muted)] mt-0.5 truncate">
                      {c.court}{c.decision_date ? ` · ${c.decision_date.slice(0, 4)}` : ''}
                    </p>
                  </div>
                  <span
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium font-mono flex-shrink-0"
                    style={{ background: b.bg, color: b.text, border: `1px solid ${b.border}` }}
                  >
                    <Icon className="w-3 h-3" />
                    {b.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Quote verification */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <Quote className="w-3.5 h-3.5 text-[var(--text-muted)]" />
          <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            Verify a quote
          </span>
        </div>
        <div className="flex gap-2">
          <input
            value={quote}
            onChange={(e) => setQuote(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleVerify(); }}
            placeholder="Paste a quote to verify it word-for-word…"
            className="flex-1 rounded-lg border border-[var(--border)] px-3 py-2 text-xs text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/50"
            style={{ background: 'var(--surface2)' }}
          />
          <button
            onClick={handleVerify}
            disabled={quoteLoading || !quote.trim()}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium text-white bg-[var(--primary)] hover:opacity-90 disabled:opacity-40 transition-colors"
          >
            {quoteLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
            Verify
          </button>
        </div>
        {quoteResult && (
          <div className={`mt-2 flex items-start gap-2 text-xs ${quoteResult.found ? 'text-emerald-600' : 'text-[var(--rose)]'}`}>
            {quoteResult.found ? (
              <CheckCircle2 className="w-4 h-4 flex-shrink-0 mt-0.5" />
            ) : (
              <XCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            )}
            <span>
              {quoteResult.found
                ? `Exact match found in the opinion.`
                : 'No exact match found in the opinion.'}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
