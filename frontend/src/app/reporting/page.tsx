"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

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

export default function ReportingPage() {
  const { user, loading: authLoading } = useAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) return;
    fetchAuth("/api/reporting/quarterly-report")
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [user]);

  if (authLoading || loading) {
    return <p className="text-sm text-[var(--text-dim)]">Loading...</p>;
  }
  if (!user) {
    return (
      <div className="card p-8 text-center">
        <p className="text-sm text-[var(--text-dim)] mb-4">
          Sign in to view client reports.
        </p>
        <Link href="/login" className="btn-primary no-underline">
          Sign In
        </Link>
      </div>
    );
  }
  if (error) {
    return <div className="card p-4 text-[var(--rose)] text-sm">{error}</div>;
  }
  if (!data?.summary) {
    return (
      <div className="card p-8 text-center text-sm text-[var(--text-dim)]">
        No metrics data yet. Start using Legal AI OS functions to generate
        reports.
      </div>
    );
  }

  const s = data.summary;
  const fn = data.by_function || [];
  const trend = data.monthly_trend || [];

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
          <h1 className="text-3xl font-bold mb-1">Client Value Report</h1>
          <p className="font-mono text-sm text-[var(--text-dim)]">
            {s.client_name || "Your Firm"}
          </p>
        </div>
        <span className="badge badge-built">Live</span>
      </div>

      {/* Hero metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        {[
          {
            label: "Hours Saved",
            value: Math.round(s.total_hours_saved || 0).toLocaleString(),
            color: "var(--metric)",
          },
          {
            label: "AI Cost",
            value: `$${((s.total_ai_cost_usd || 0)).toFixed(2)}`,
            color: "var(--secondary)",
          },
          {
            label: "Active Matters",
            value: s.active_matters || 0,
            color: "var(--primary)",
          },
          {
            label: "Functions Used",
            value: s.functions_used || 0,
            color: "var(--violet)",
          },
        ].map((m) => (
          <div key={m.label} className="card p-5 text-center">
            <div
              className="text-3xl font-bold mb-1"
              style={{ color: m.color }}
            >
              {m.value}
            </div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)]">
              {m.label}
            </div>
          </div>
        ))}
      </div>

      {/* By Function */}
      <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-[var(--text-dim)] mb-4">
        By Function
      </h2>
      <div className="grid gap-3 mb-8">
        {fn
          .filter((f: any) => f.status === "built" || f.invocations > 0)
          .map((f: any) => (
            <div
              key={f.function_id}
              className="card p-4 flex items-center justify-between"
            >
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-sm">{f.name}</span>
                  <span
                    className={`badge ${
                      f.status === "built" ? "badge-built" : "badge-roadmap"
                    }`}
                  >
                    {f.status}
                  </span>
                </div>
                <span className="text-xs text-[var(--text-dim)]">
                  {f.invocations} invocations &middot;{" "}
                  {f.total_tokens.toLocaleString()} tokens
                </span>
              </div>
              <div className="flex items-center gap-4 text-right">
                <div>
                  <div className="text-sm font-semibold text-[var(--metric)]">
                    {f.total_time_saved_hours.toFixed(1)} hrs saved
                  </div>
                  <div className="text-[10px] font-mono text-[var(--text-muted)]">
                    ${f.total_cost_usd.toFixed(4)} cost
                  </div>
                </div>
              </div>
            </div>
          ))}
      </div>

      {/* Monthly Trend */}
      {trend.length > 0 && (
        <>
          <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-[var(--text-dim)] mb-4">
            Monthly Trend
          </h2>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  <th className="text-left p-3 font-mono text-xs text-[var(--text-dim)] uppercase tracking-wider">
                    Month
                  </th>
                  <th className="text-right p-3 font-mono text-xs text-[var(--text-dim)] uppercase tracking-wider">
                    Invocations
                  </th>
                  <th className="text-right p-3 font-mono text-xs text-[var(--text-dim)] uppercase tracking-wider">
                    Tokens
                  </th>
                  <th className="text-right p-3 font-mono text-xs text-[var(--text-dim)] uppercase tracking-wider">
                    Cost
                  </th>
                  <th className="text-right p-3 font-mono text-xs text-[var(--text-dim)] uppercase tracking-wider">
                    Hours Saved
                  </th>
                </tr>
              </thead>
              <tbody>
                {trend.map((row: any, i: number) => (
                  <tr
                    key={i}
                    className="border-b border-[var(--border)] last:border-0"
                  >
                    <td className="p-3">
                      {new Date(row.month).toLocaleDateString("en-US", {
                        year: "numeric",
                        month: "short",
                      })}
                    </td>
                    <td className="p-3 text-right font-mono text-xs">
                      {row.invocations}
                    </td>
                    <td className="p-3 text-right font-mono text-xs">
                      {row.total_tokens?.toLocaleString()}
                    </td>
                    <td className="p-3 text-right font-mono text-xs">
                      ${parseFloat(row.total_cost_usd || 0).toFixed(4)}
                    </td>
                    <td className="p-3 text-right font-semibold text-[var(--metric)]">
                      {parseFloat(row.hours_saved || 0).toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Baselines */}
      <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-[var(--text-dim)] mb-4 mt-8">
        Time Saved Baselines
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {(data.baselines || []).map((b: any, i: number) => (
          <div key={i} className="card p-4">
            <div className="text-sm font-semibold mb-1">{b.description}</div>
            <div className="text-xs text-[var(--text-dim)]">
              Baseline: {(b.baseline_seconds / 60).toFixed(0)} min per
              invocation
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
