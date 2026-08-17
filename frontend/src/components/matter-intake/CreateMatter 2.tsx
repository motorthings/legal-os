'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Scale, Loader2, CheckCircle2, ExternalLink, Sparkles } from 'lucide-react';
import { createMatter, type CreatedMatter } from '@/lib/matters-api';
import type { EvaluateResponse } from '@/lib/matter-intake-types';

function deriveName(summary: string): string {
  const words = summary.trim().split(/\s+/).slice(0, 6).join(' ');
  return words ? `${words}…` : 'New Matter';
}

export default function CreateMatter({ summary, data }: { summary: string; data: EvaluateResponse }) {
  const [name, setName] = useState(deriveName(summary));
  const [jurisdiction, setJurisdiction] = useState('');
  const [creating, setCreating] = useState(false);
  const [result, setResult] = useState<CreatedMatter | null>(null);
  const [error, setError] = useState<string | null>(null);

  const adverse =
    data.conflict_check?.conflict_type === 'direct_adverse' && data.conflict_check.entity_name
      ? [data.conflict_check.entity_name]
      : [];

  const handleCreate = async () => {
    if (!name.trim() || creating) return;
    setCreating(true);
    setError(null);
    setResult(null);
    try {
      const r = await createMatter({
        name: name.trim(),
        description: summary,
        jurisdiction: jurisdiction.trim() || undefined,
        practice_area: data.practice_area?.practice_area || undefined,
        adverse_parties: adverse,
        risk_level: data.urgency_risk?.risk_level || undefined,
        risk_score: data.urgency_risk?.risk_score ?? data.overall_score,
      });
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create matter');
    } finally {
      setCreating(false);
    }
  };

  const enrichment = result?.enrichment;
  const totalResults = (enrichment?.results || []).reduce((n, r) => n + (r.results_count || 0), 0);

  return (
    <div className="card p-6">
      <div className="flex items-center gap-2 mb-1">
        <Sparkles className="w-4 h-4 text-[var(--primary)]" />
        <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
          Create matter &amp; enrich with Descrybe
        </h3>
      </div>
      <p className="text-xs text-[var(--text-dim)] mb-4">
        Save this intake as a matter and auto-surface relevant case law and statutes with the
        Descrybe Legal Engine.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={creating}
          placeholder="Matter name"
          className="rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/50"
          style={{ background: 'var(--surface2)' }}
        />
        <input
          value={jurisdiction}
          onChange={(e) => setJurisdiction(e.target.value)}
          disabled={creating}
          placeholder="Jurisdiction (e.g. Federal, California)"
          className="rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/50"
          style={{ background: 'var(--surface2)' }}
        />
      </div>

      {(data.practice_area?.practice_area || adverse.length > 0) && (
        <div className="flex flex-wrap gap-2 mb-3">
          {data.practice_area?.practice_area && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--surface2)] text-[var(--text-dim)]">
              {data.practice_area.practice_area}
            </span>
          )}
          {adverse.map((p) => (
            <span key={p} className="text-xs px-2 py-0.5 rounded-full bg-[var(--rose)]/10 text-[var(--rose)]">
              {p}
            </span>
          ))}
        </div>
      )}

      {!result && (
        <button
          onClick={handleCreate}
          disabled={creating || !name.trim()}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white bg-[var(--primary)] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Scale className="w-4 h-4" />}
          {creating ? 'Creating & enriching…' : 'Create matter & enrich'}
        </button>
      )}

      {error && <p className="text-xs text-[var(--rose)] mt-3 break-words">{error}</p>}

      {result && (
        <div className="mt-4 p-4 rounded-lg border border-emerald-500/30 bg-emerald-500/5">
          <div className="flex items-start gap-2 mb-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-[var(--text)]">Matter created</p>
              <p className="text-xs text-[var(--text-dim)] font-mono">{result.matter.name}</p>
            </div>
          </div>

          {enrichment?.reason === 'descrybe_not_configured' ? (
            <p className="text-xs text-amber-500">
              Descrybe not connected — connect it to auto-enrich this matter.
            </p>
          ) : enrichment?.error ? (
            <p className="text-xs text-[var(--rose)]">Enrichment failed: {enrichment.error}</p>
          ) : (
            <p className="text-xs text-[var(--text-dim)]">
              <strong className="text-[var(--text)]">Descrybe</strong> ran{' '}
              {enrichment?.queries_run ?? 0} research quer{(enrichment?.queries_run ?? 0) === 1 ? 'y' : 'ies'} and
              surfaced {totalResults} authorit{totalResults === 1 ? 'y' : 'ies'}.
            </p>
          )}

          <Link
            href="/legal-research"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--primary)] hover:opacity-80 mt-3 no-underline"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Research this matter
          </Link>
        </div>
      )}
    </div>
  );
}
