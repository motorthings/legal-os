'use client';

import { useState } from 'react';
import { searchKnowledge } from '@/lib/km-api';
import type { KMAnalysis } from '@/lib/km-api';
import { Send, RefreshCw, AlertTriangle, Search, FileText, Link2, GitGraph } from 'lucide-react';

type State =
  | { status: 'empty' }
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'success'; data: KMAnalysis };

function docTypeLabel(type: string) {
  switch (type) {
    case 'brief': return 'Brief';
    case 'memo': return 'Memo';
    case 'contract': return 'Contract';
    case 'email': return 'Email';
    case 'opinion': return 'Opinion';
    case 'research': return 'Research';
    default: return type;
  }
}

function relevanceColor(score: number) {
  if (score >= 70) return '#22c55e';
  if (score >= 40) return '#f59e0b';
  return '#ef4444';
}

function nodeColor(type: string) {
  switch (type) {
    case 'entity': return '#6366f1';
    case 'jurisdiction': return '#22c55e';
    case 'party': return '#f59e0b';
    case 'outcome': return '#3b82f6';
    case 'doctrine': return '#ec4899';
    default: return '#888';
  }
}

export default function KMPage() {
  const [value, setValue] = useState('');
  const [state, setState] = useState<State>({ status: 'empty' });

  const handleSubmit = async () => {
    const text = value.trim();
    if (!text) return;
    setState({ status: 'loading' });
    try {
      const data = await searchKnowledge(text);
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
          KM &amp; Precedent Intelligence
        </h1>
        <p className="font-mono text-sm text-[var(--text-dim)] max-w-xl">
          Semantic search across all firm documents with citations.
          Connect every output, finding, and precedent into a single searchable knowledge layer.
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
            placeholder={`Describe what you're searching for...

Examples:
- "Find all matters involving force majeure clauses in California supply chain contracts since 2022"
- "Show me prior analyses of non-compete enforceability under Delaware law for tech industry clients"
- "What precedent do we have on trade secret misappropriation damages in the Eastern District of Texas?"`}
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
              <Search className="w-4 h-4" />
              Search Knowledge Base
            </button>
          </div>
        </div>
      )}

      <div className="mt-8">
        {/* Empty */}
        {state.status === 'empty' && (
          <div className="card p-6 text-center py-16">
            <div className="w-12 h-12 rounded-xl bg-[var(--primary-dim)] flex items-center justify-center mx-auto mb-4 border border-[var(--primary)]/20">
              <Search className="w-6 h-6 text-[var(--primary)]" />
            </div>
            <h3 className="text-lg font-semibold text-[var(--text)] mb-2">Ready to search</h3>
            <p className="text-sm text-[var(--text-dim)] mb-8 max-w-md mx-auto">
              Describe what you need and the system will semantically search all documents,
              surface related precedents, and build a knowledge graph of connections.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-xl mx-auto">
              {['Semantic Search', 'Precedent Linking', 'Knowledge Graph'].map((d) => (
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
              <p className="text-sm text-[var(--text-dim)]">Searching across documents, precedents, and knowledge graph...</p>
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
                <h3 className="text-sm font-semibold text-[var(--rose)] mb-1">Search failed</h3>
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
                  <h2 className="text-lg font-semibold text-[var(--text)]">Search Results</h2>
                  <p className="text-xs text-[var(--text-muted)] mt-1 font-mono">
                    {state.data.total_documents_searched.toLocaleString()} docs searched · {state.data.results.length} results · {state.data.processing_time_ms.toLocaleString()}ms
                  </p>
                </div>
                <span className="text-xs text-[var(--text-dim)] font-mono">{state.data.model_used}</span>
              </div>
              {state.data.query_understanding && (
                <p className="text-xs text-[var(--text-dim)] mt-3 italic">
                  &ldquo;{state.data.query_understanding}&rdquo;
                </p>
              )}
            </div>

            {/* Semantic Search Results */}
            <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
              Document Results
            </h3>
            <div className="space-y-3 mb-6">
              {state.data.results.map((r) => {
                const color = relevanceColor(r.relevance);
                return (
                  <div key={r.id} className="card p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <FileText className="w-4 h-4 text-[var(--text-dim)] flex-shrink-0" />
                          <h4 className="text-sm font-semibold text-[var(--text)]">{r.title}</h4>
                          <span className="text-[10px] px-1.5 py-0.5 rounded font-mono border" style={{ borderColor: 'var(--border)', color: 'var(--text-dim)' }}>
                            {docTypeLabel(r.document_type)}
                          </span>
                        </div>
                        <p className="text-xs text-[var(--text-dim)] mb-2">{r.snippet}</p>
                        <div className="flex items-center gap-3 text-[10px] text-[var(--text-muted)] font-mono">
                          <span>{r.citation}</span>
                          <span>·</span>
                          <span>{r.date}</span>
                          <span>·</span>
                          <span>{r.practice_area}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <div className="w-10 h-10 rounded-full flex items-center justify-center border-2" style={{ borderColor: color }}>
                          <span className="text-sm font-bold font-mono" style={{ color }}>{r.relevance}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Precedent Links */}
            {state.data.precedents.length > 0 && (
              <>
                <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
                  Precedent Links
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
                  {state.data.precedents.map((p, i) => (
                    <div key={i} className="card p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Link2 className="w-4 h-4 text-[var(--primary)]" />
                        <span className="text-[10px] font-medium uppercase text-[var(--text-dim)]">{p.relationship}</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-muted)]">
                        <span className="truncate">{p.source_id}</span>
                        <span>→</span>
                        <span className="truncate">{p.target_id}</span>
                      </div>
                      <div className="mt-2 h-1 rounded-full bg-[var(--surface2)] overflow-hidden">
                        <div className="h-full rounded-full bg-[var(--primary)]" style={{ width: `${p.strength}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* Knowledge Graph */}
            {state.data.knowledge_graph.length > 0 && (
              <>
                <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
                  Knowledge Graph
                </h3>
                <div className="card p-5 mb-6">
                  <div className="flex flex-wrap gap-3">
                    {state.data.knowledge_graph.map((node) => (
                      <div
                        key={node.id}
                        className="inline-flex items-center gap-2 px-3 py-2 rounded-full border"
                        style={{ borderColor: nodeColor(node.type), background: `${nodeColor(node.type)}10` }}
                      >
                        <GitGraph className="w-3.5 h-3.5" style={{ color: nodeColor(node.type) }} />
                        <span className="text-sm font-medium text-[var(--text)]">{node.label}</span>
                        <span className="text-[10px] font-mono" style={{ color: nodeColor(node.type) }}>
                          {node.type} · {node.connections}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            <div className="text-center">
              <button
                onClick={handleReset}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-[var(--primary)] bg-[var(--primary-dim)] border border-[var(--primary)]/20 hover:opacity-80 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                New Search
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
