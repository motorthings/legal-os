"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getHealth, getProjects, DDProject } from "@/lib/api";

export default function DueDiligencePage() {
  const [health, setHealth] = useState<string>("");
  const [projects, setProjects] = useState<DDProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [h, p] = await Promise.all([getHealth(), getProjects()]);
        setHealth(h.status);
        setProjects(Array.isArray(p) ? p : []);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="font-mono text-[10px] text-[var(--text-muted)] uppercase tracking-wider">
              {health ? `API: ${health}` : "..."}
            </span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-[var(--text)]">
            Due Diligence Accelerator
          </h1>
          <p className="font-mono text-sm text-[var(--text-dim)] mt-1">
            Bulk document ingestion, target standards, deviation-only reporting.
          </p>
        </div>
        <Link href="/due-diligence/new" className="btn-primary no-underline">
          + New Project
        </Link>
      </div>

      {/* Error */}
      {error && (
        <div className="card p-4 mb-6 border-[var(--rose)] text-[var(--rose)] text-sm">
          {error}
        </div>
      )}

      {/* Projects list */}
      {loading ? (
        <p className="text-sm text-[var(--text-dim)]">Loading...</p>
      ) : projects.length === 0 ? (
        <div className="card p-10 text-center">
          <p className="text-[var(--text-dim)] mb-4">
            No due diligence projects yet.
          </p>
          <Link href="/due-diligence/new" className="btn-primary no-underline">
            Create your first project
          </Link>
        </div>
      ) : (
        <div className="grid gap-3">
          {projects.map((p) => (
            <Link
              key={p.id}
              href={`/due-diligence/${p.id}`}
              className="card p-5 no-underline flex items-center justify-between"
            >
              <div>
                <h3 className="font-semibold text-lg mb-1">{p.name}</h3>
                <div className="flex items-center gap-3 text-xs text-[var(--text-dim)]">
                  <span className="font-mono uppercase">
                    {p.deal_type || "No type"}
                  </span>
                  {p.counterparty && <span>&middot; {p.counterparty}</span>}
                </div>
              </div>
              <div className="flex items-center gap-3 text-right">
                <div>
                  <div className="text-sm font-semibold">
                    {p.document_count}{" "}
                    <span className="text-xs text-[var(--text-dim)]">docs</span>
                  </div>
                  <div className="text-xs text-[var(--text-dim)]">
                    {p.deviation_count} deviations
                    {p.critical_count > 0 && (
                      <span className="text-[var(--rose)] ml-1">
                        &middot; {p.critical_count} critical
                      </span>
                    )}
                  </div>
                </div>
                <span
                  className={`badge ${
                    p.status === "review"
                      ? "badge-high"
                      : p.status === "completed"
                        ? "badge-built"
                        : "badge-roadmap"
                  }`}
                >
                  {p.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
