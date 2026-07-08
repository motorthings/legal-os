"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

function getAccessToken(): string | null {
  try {
    const stored = localStorage.getItem("sb-rkiaocarugdbcgtonfuq-auth-token");
    if (stored) return JSON.parse(stored).access_token || null;
  } catch {}
  return null;
}

async function fetchAuth<T>(path: string): Promise<T> {
  const token = getAccessToken();
  const res = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export default function RegulatoryPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [polling, setPolling] = useState(false);

  useEffect(() => {
    fetchAuth("/api/regulatory/dashboard")
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function triggerPoll() {
    setPolling(true);
    try {
      await fetchAuth("/api/regulatory/poll");
      // Refresh after a moment
      setTimeout(async () => {
        const fresh = await fetchAuth("/api/regulatory/dashboard");
        setData(fresh);
        setPolling(false);
      }, 3000);
    } catch (e: any) {
      setError(e.message);
      setPolling(false);
    }
  }

  if (loading) return <p className="text-sm text-[var(--text-dim)]">Loading...</p>;
  if (error) return <div className="card p-4 text-[var(--rose)] text-sm">{error}</div>;

  const summary = data?.summary || {};
  const updates = data?.recent_updates || [];
  const flags = data?.open_flags || [];
  const sources = data?.sources || [];

  return (
    <div>
      <Link
        href="/"
        className="font-mono text-xs text-[var(--text-dim)] hover:text-[var(--secondary)] no-underline mb-4 inline-block"
      >
        &larr; Dashboard
      </Link>

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="badge badge-roadmap">Roadmap</span>
            <span className="font-mono text-[10px] text-[var(--text-muted)] uppercase tracking-wider">
              v0.1.0
            </span>
          </div>
          <h1 className="text-3xl font-bold">Regulatory Change Monitor</h1>
          <p className="font-mono text-sm text-[var(--text-dim)] mt-1">
            {summary.active_sources || 0} active sources across multiple jurisdictions
          </p>
        </div>
        <button onClick={triggerPoll} disabled={polling} className="btn-primary">
          {polling ? "Polling..." : "Poll Sources"}
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        {[
          { label: "Sources", value: summary.total_sources || 0, color: "var(--secondary)" },
          { label: "Open Flags", value: summary.open_flags_count || 0, color: "var(--primary)" },
          { label: "Critical", value: summary.critical_flags || 0, color: "var(--rose)" },
          { label: "Active", value: summary.active_sources || 0, color: "var(--metric)" },
        ].map((m) => (
          <div key={m.label} className="card p-4 text-center">
            <div className="text-2xl font-bold mb-1" style={{ color: m.color }}>{m.value}</div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)]">{m.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sources */}
        <div>
          <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-[var(--text-dim)] mb-4">
            Sources
          </h2>
          <div className="grid gap-2">
            {sources.map((s: any) => (
              <div key={s.id} className="card p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold">{s.agency}</span>
                  <span className={`badge ${s.status === "active" ? "badge-built" : "badge-roadmap"}`}>
                    {s.status}
                  </span>
                </div>
                <div className="text-xs text-[var(--text-dim)]">{s.name}</div>
                <div className="flex items-center gap-2 mt-1 text-[10px] font-mono text-[var(--text-muted)]">
                  <span>{s.jurisdiction}</span>
                  <span>&middot;</span>
                  <span>{s.poll_frequency}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Updates */}
        <div className="lg:col-span-2">
          <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-[var(--text-dim)] mb-4">
            Recent Updates
          </h2>
          {updates.length === 0 ? (
            <div className="card p-6 text-center text-sm text-[var(--text-dim)]">
              No regulatory updates yet. Poll sources to extract changes.
            </div>
          ) : (
            <div className="grid gap-2">
              {updates.map((u: any) => (
                <div key={u.id} className="card p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-[var(--secondary)] uppercase">
                        {u.agency}
                      </span>
                      <span className={`badge ${
                        u.change_type === "enforcement_action" ? "badge-critical" :
                        u.change_type === "new_regulation" ? "badge-high" :
                        u.change_type === "amendment" ? "badge-medium" : "badge-low"
                      }`}>
                        {u.change_type}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-[var(--text-muted)]">
                      {u.effective_date || "TBD"}
                    </span>
                  </div>
                  <h3 className="font-semibold text-sm mb-1">{u.regulation_name}</h3>
                  <p className="text-sm text-[var(--text-dim)] line-clamp-2">{u.change_summary}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Open Flags */}
      {flags.length > 0 && (
        <>
          <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-[var(--text-dim)] mb-4 mt-8">
            Open Flags
          </h2>
          <div className="grid gap-2">
            {flags.map((f: any) => (
              <div key={f.id} className="card p-4 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`badge ${
                      f.impact_severity === "critical" ? "badge-critical" :
                      f.impact_severity === "high" ? "badge-high" :
                      f.impact_severity === "medium" ? "badge-medium" : "badge-low"
                    }`}>
                      {f.impact_severity}
                    </span>
                    <span className="badge badge-roadmap">{f.status}</span>
                  </div>
                  <p className="text-sm">{f.impact_summary}</p>
                </div>
                <span className="text-[10px] font-mono text-[var(--text-muted)]">
                  {f.matter_id ? "Linked to matter" : ""}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
