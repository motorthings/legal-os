"use client";

import { useEffect, useState, FormEvent } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

function getAccessToken(): string | null {
  try {
    const stored = localStorage.getItem("sb-rkiaocarugdbcgtonfuq-auth-token");
    if (stored) return JSON.parse(stored).access_token || null;
  } catch {}
  return null;
}

async function fetchAuth<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAccessToken();
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options?.headers as Record<string, string> || {}),
    },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export default function KMPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [method, setMethod] = useState("");
  const [stats, setStats] = useState<any>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchAuth("/api/km/stats").then(setStats).catch(() => {});
  }, []);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setError("");
    try {
      const data = await fetchAuth<any>(
        `/api/km/search?q=${encodeURIComponent(query)}&limit=20`
      );
      setResults(data.results || []);
      setMethod(data.method || "");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSearching(false);
    }
  }

  async function findSimilar(docId: string) {
    try {
      const data = await fetchAuth<any>(`/api/km/search/similar/${docId}`);
      setResults(data.similar || []);
      setMethod("similarity");
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <div>
      <Link
        href="/"
        className="font-mono text-xs text-[var(--text-dim)] hover:text-[var(--secondary)] no-underline mb-4 inline-block"
      >
        &larr; Dashboard
      </Link>

      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="badge badge-roadmap">Roadmap</span>
            <span className="font-mono text-[10px] text-[var(--text-muted)] uppercase tracking-wider">
              v0.1.0
            </span>
          </div>
          <h1 className="text-3xl font-bold">KM &amp; Precedent Intelligence</h1>
          <p className="font-mono text-sm text-[var(--text-dim)] mt-1">
            {stats
              ? `${stats.active_documents || 0} documents indexed`
              : "Semantic search across all firm documents"}
          </p>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {Object.entries(stats.by_type || {}).map(([type, count]) => (
            <div key={type} className="card p-3 text-center">
              <div className="text-lg font-bold text-[var(--secondary)]">{count as number}</div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--text-dim)]">
                {type}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-3 mb-6">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search firm knowledge — 'Have we done an indemnification clause with a 90-day cap?'"
          className="flex-1"
        />
        <button type="submit" className="btn-primary" disabled={searching}>
          {searching ? "Searching..." : "Search"}
        </button>
      </form>

      {method && (
        <div className="font-mono text-[10px] text-[var(--text-muted)] uppercase tracking-wider mb-3">
          Search method: {method} &middot; {results.length} results
        </div>
      )}

      {error && (
        <div className="card p-4 mb-4 text-[var(--rose)] text-sm">{error}</div>
      )}

      {/* Results */}
      {results.length > 0 ? (
        <div className="grid gap-3">
          {results.map((r: any, i: number) => (
            <div key={r.id || i} className="card p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-semibold text-sm mb-1">{r.title}</h3>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] uppercase text-[var(--secondary)]">
                      {r.document_type || "document"}
                    </span>
                    {r.similarity != null && (
                      <span className="font-mono text-[10px] text-[var(--text-muted)]">
                        {(r.similarity * 100).toFixed(0)}% match
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => findSimilar(r.id)}
                  className="text-[10px] font-mono uppercase text-[var(--text-dim)] hover:text-[var(--secondary)] bg-transparent border border-[var(--border)] rounded px-2 py-1 cursor-pointer"
                >
                  Find Similar
                </button>
              </div>
              {r.source_url && (
                <a
                  href={r.source_url}
                  target="_blank"
                  rel="noopener"
                  className="text-xs text-[var(--secondary)] hover:underline break-all"
                >
                  {r.source_file || r.source_url}
                </a>
              )}
              {r.metadata?.summary && (
                <p className="text-sm text-[var(--text-dim)] mt-2 line-clamp-2">
                  {r.metadata.summary}
                </p>
              )}
              {r.chunk_count > 0 && (
                <div className="text-[10px] font-mono text-[var(--text-muted)] mt-1">
                  {r.chunk_count} chunks &middot; v{r.version}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : query && !searching ? (
        <div className="card p-8 text-center text-sm text-[var(--text-dim)]">
          No results found for &ldquo;{query}&rdquo;.
          <br />
          Try different keywords or ingest more documents into the knowledge base.
        </div>
      ) : null}
    </div>
  );
}
