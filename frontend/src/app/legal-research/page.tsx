'use client';

import { useCallback, useEffect, useState } from 'react';
import { Scale, Search, Link2, AlertTriangle, CheckCircle2, ShieldAlert, ShieldCheck, HelpCircle, ExternalLink, RefreshCw, Loader2 } from 'lucide-react';
import {
  connectDescrybe,
  getDescrybeStatus,
  runResearch,
  type ResearchResult,
  type ResearchResponse,
  type QueryType,
} from '@/lib/legal-research-api';
import CaseDrillDown from '@/components/legal-research/CaseDrillDown';

type Status = 'checking' | 'connected' | 'disconnected';

function treatmentBadge(r: ResearchResult) {
  if (r.is_good_law === true) {
    return { bg: 'rgba(34,197,94,0.12)', text: '#22c55e', border: 'rgba(34,197,94,0.25)', label: 'Good Law', icon: CheckCircle2 };
  }
  if (r.is_good_law === false) {
    return { bg: 'rgba(239,68,68,0.12)', text: '#ef4444', border: 'rgba(239,68,68,0.25)', label: 'Overruled', icon: ShieldAlert };
  }
  if (r.treatment === 'caution' || r.treatment_category === 'distinguished') {
    return { bg: 'rgba(245,158,11,0.12)', text: '#f59e0b', border: 'rgba(245,158,11,0.25)', label: 'Caution', icon: AlertTriangle };
  }
  return { bg: 'rgba(100,116,139,0.12)', text: '#94a3b8', border: 'rgba(100,116,139,0.25)', label: 'Untreated', icon: HelpCircle };
}

const QUERY_TYPES: { value: QueryType; label: string }[] = [
  { value: 'concept_search', label: 'Issue / concept' },
  { value: 'text_search', label: 'Exact text' },
  { value: 'law_search', label: 'Statutes & rules' },
  { value: 'citation_lookup', label: 'Citation / case name' },
];

export default function LegalResearchPage() {
  const [status, setStatus] = useState<Status>('checking');
  const [connecting, setConnecting] = useState(false);
  const [queryType, setQueryType] = useState<QueryType>('concept_search');
  const [queryText, setQueryText] = useState('');
  const [jurisdiction, setJurisdiction] = useState('');
  const [response, setResponse] = useState<ResearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const checkStatus = useCallback(async () => {
    try {
      const s = await getDescrybeStatus();
      setStatus(s.connected ? 'connected' : 'disconnected');
    } catch {
      setStatus('disconnected');
    }
  }, []);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const returnTo = window.location.href;
      const { authorization_url } = await connectDescrybe(returnTo);
      window.location.href = authorization_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start connection');
      setConnecting(false);
    }
  };

  const handleSearch = async () => {
    if (!queryText.trim()) return;
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const r = await runResearch({
        query_type: queryType,
        query_text: queryText.trim(),
        jurisdiction: jurisdiction.trim() || undefined,
      });
      setResponse(r);
      if (r.error) setError(r.error);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-4xl font-bold tracking-tight text-[var(--text)] mt-3 mb-2">
          Legal Research
        </h1>
        <p className="font-mono text-sm text-[var(--text-dim)] max-w-xl">
          Case law, statutes, and citation intelligence powered by Descrybe —
          with good-law treatment, authority ranking, and word-for-word quote verification.
        </p>
      </header>

      {/* Connect banner */}
      {status === 'checking' && (
        <div className="card p-6 mb-6 flex items-center gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-[var(--text-muted)]" />
          <span className="text-sm text-[var(--text-dim)]">Checking Descrybe connection…</span>
        </div>
      )}

      {status === 'disconnected' && (
        <div className="card p-6 mb-6 flex items-start gap-4 border border-[var(--amber)]/30">
          <div className="w-10 h-10 rounded-xl bg-[var(--primary-dim)] flex items-center justify-center flex-shrink-0">
            <Scale className="w-5 h-5 text-[var(--primary)]" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-[var(--text)] mb-1">Connect Descrybe</h3>
            <p className="text-sm text-[var(--text-dim)] mb-4">
              Descrybe uses per-user sign-in, not API keys. Connect your account once to unlock
              research, good-law checks, and citation verification.
            </p>
            <button
              onClick={handleConnect}
              disabled={connecting}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white bg-[var(--primary)] hover:opacity-90 disabled:opacity-40 transition-colors"
            >
              {connecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Link2 className="w-4 h-4" />}
              {connecting ? 'Redirecting…' : 'Connect Descrybe'}
            </button>
            {error && <p className="text-xs text-[var(--rose)] mt-3 break-words">{error}</p>}
          </div>
        </div>
      )}

      {/* Search form */}
      {status === 'connected' && (
        <div className="card p-6 mb-6">
          <div className="flex flex-col sm:flex-row gap-3 mb-3">
            <select
              value={queryType}
              onChange={(e) => setQueryType(e.target.value as QueryType)}
              className="rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/50"
              style={{ background: 'var(--surface2)' }}
            >
              {QUERY_TYPES.map((q) => (
                <option key={q.value} value={q.value}>{q.label}</option>
              ))}
            </select>
            <input
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
              placeholder="Jurisdiction (e.g. Federal, California)"
              className="flex-1 rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/50"
              style={{ background: 'var(--surface2)' }}
            />
          </div>
          <textarea
            rows={4}
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            placeholder={
              queryType === 'citation_lookup'
                ? 'e.g. "University of Tex. Southwestern Medical Center v. Nassar" or "133 S. Ct. 2517"'
                : 'e.g. "workplace discrimination retaliation under Title VII"'
            }
            className="w-full rounded-lg border border-[var(--border)] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/50 font-mono resize-y"
            style={{ background: 'var(--surface2)' }}
          />
          <div className="mt-3 flex justify-end">
            <button
              onClick={handleSearch}
              disabled={loading || !queryText.trim()}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white bg-[var(--primary)] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              {loading ? 'Searching…' : 'Research'}
            </button>
          </div>
        </div>
      )}

      {/* Results */}
      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="h-4 bg-[var(--surface2)] rounded w-2/3 mb-3" />
              <div className="h-3 bg-[var(--surface2)] rounded w-1/3 mb-2" />
              <div className="h-3 bg-[var(--surface2)] rounded w-full" />
            </div>
          ))}
        </div>
      )}

      {error && !loading && (
        <div className="card p-6 border-l-4 border-l-[var(--rose)] mb-6">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-[var(--rose)] flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-[var(--rose)] mb-1">Research failed</h3>
              <p className="text-sm text-[var(--text-dim)] break-words">{error}</p>
            </div>
          </div>
        </div>
      )}

      {response && !loading && !error && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <span className="text-sm text-[var(--text-dim)]">
              {response.results.length} result{response.results.length === 1 ? '' : 's'}
            </span>
            {response.cached && (
              <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-[var(--metric-dim)] text-[var(--metric)]">
                cached
              </span>
            )}
          </div>

          {response.results.length === 0 && (
            <div className="card p-10 text-center">
              <p className="text-sm text-[var(--text-dim)]">No results for this query.</p>
            </div>
          )}

          <div className="space-y-3">
            {response.results.map((r, i) => {
              const badge = treatmentBadge(r);
              const Icon = badge.icon;
              return (
                <div key={r.case_id || r.source_id || i} className="card p-5">
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div className="min-w-0">
                      <h3 className="text-base font-semibold text-[var(--text)] leading-snug">{r.title}</h3>
                      <p className="text-xs font-mono text-[var(--text-muted)] mt-1 truncate">
                        {r.citation || 'No citation'}
                      </p>
                    </div>
                    <span
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium font-mono flex-shrink-0"
                      style={{ background: badge.bg, color: badge.text, border: `1px solid ${badge.border}` }}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      {badge.label}
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-2 mb-3">
                    {r.authority_label && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-[var(--primary-dim)] text-[var(--primary)]">
                        {r.authority_label}
                      </span>
                    )}
                    {r.court && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--surface2)] text-[var(--text-dim)]">
                        {r.court}
                      </span>
                    )}
                    {r.decision_year && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--surface2)] text-[var(--text-dim)] font-mono">
                        {r.decision_year}
                      </span>
                    )}
                  </div>

                  {r.why_relevant && (
                    <p className="text-xs text-[var(--text-dim)] italic mb-2">{r.why_relevant}</p>
                  )}

                  {r.snippet && (
                    <p className="text-sm text-[var(--text-dim)] leading-relaxed line-clamp-4">{r.snippet}</p>
                  )}

                  <div className="flex items-center gap-4 mt-3">
                    {r.source_url && (
                      <a
                        href={r.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--primary)] hover:opacity-80 no-underline"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        Open in Descrybe
                      </a>
                    )}
                    {r.case_id && (
                      <button
                        onClick={() => setExpandedId(expandedId === r.case_id ? null : r.case_id!)}
                        className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--text-dim)] hover:text-[var(--text)] transition-colors"
                      >
                        <ShieldCheck className="w-3.5 h-3.5" />
                        {expandedId === r.case_id ? 'Hide citation intelligence' : 'Citation intelligence'}
                      </button>
                    )}
                  </div>
                  {r.case_id && expandedId === r.case_id && (
                    <CaseDrillDown caseId={r.case_id} />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
