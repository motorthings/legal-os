"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import FileUpload from "@/components/FileUpload";
import {
  getProject,
  getDeviations,
  reviewDeviation,
  DDProject,
  DDDocument,
  DDDeviation,
} from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<
    (DDProject & { target_standards: any[]; documents: DDDocument[] }) | null
  >(null);
  const [deviations, setDeviations] = useState<DDDeviation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [proj, devs] = await Promise.all([
          getProject(id),
          getDeviations(id).catch(() => ({ deviations: [], summary: null })),
        ]);
        setProject(proj);
        setDeviations(devs.deviations || []);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  async function handleReview(
    deviationId: string,
    decision: string,
    notes?: string
  ) {
    try {
      await reviewDeviation(deviationId, {
        review_decision: decision,
        review_notes: notes,
        reviewed_by: "user", // TODO: real user ID from Supabase Auth
      });
      // Refresh
      const devs = await getDeviations(id);
      setDeviations(devs.deviations || []);
    } catch (e: any) {
      setError(e.message);
    }
  }

  if (loading)
    return <p className="text-sm text-[var(--text-dim)]">Loading...</p>;
  if (error)
    return <div className="card p-4 text-[var(--rose)] text-sm">{error}</div>;
  if (!project)
    return <div className="card p-4 text-sm">Project not found</div>;

  const severityColor = (s: string) =>
    s === "critical"
      ? "badge-critical"
      : s === "high"
        ? "badge-high"
        : s === "medium"
          ? "badge-medium"
          : "badge-low";

  return (
    <div>
      {/* Breadcrumb */}
      <Link
        href="/due-diligence"
        className="font-mono text-xs text-[var(--text-dim)] hover:text-[var(--secondary)] no-underline mb-4 inline-block"
      >
        &larr; Back to projects
      </Link>

      {/* Project header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">{project.name}</h1>
          <div className="flex items-center gap-3 text-xs text-[var(--text-dim)]">
            <span className="font-mono uppercase">
              {project.deal_type || "No type"}
            </span>
            {project.counterparty && (
              <>
                <span>&middot;</span>
                <span>{project.counterparty}</span>
              </>
            )}
            <span>&middot;</span>
            <span>{project.document_count} documents</span>
          </div>
        </div>
        <span
          className={`badge ${
            project.status === "review"
              ? "badge-high"
              : project.status === "completed"
                ? "badge-built"
                : "badge-roadmap"
          }`}
        >
          {project.status}
        </span>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-8">
        {[
          {
            label: "Documents",
            value: project.document_count,
            color: "var(--secondary)",
          },
          {
            label: "Deviations",
            value: project.deviation_count,
            color: "var(--primary)",
          },
          {
            label: "Critical",
            value: project.critical_count,
            color: "var(--rose)",
          },
          {
            label: "Unreviewed",
            value: deviations.filter((d) => !d.review_decision).length,
            color: "var(--amber)",
          },
          {
            label: "Standards",
            value: project.target_standards?.length || 0,
            color: "var(--metric)",
          },
        ].map((s) => (
          <div key={s.label} className="card p-4 text-center">
            <div
              className="text-2xl font-bold mb-1"
              style={{ color: s.color }}
            >
              {s.value}
            </div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-dim)]">
              {s.label}
            </div>
          </div>
        ))}
      </div>

      {/* Upload + Analyze */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2">
          <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-[var(--text-dim)] mb-4">
            Upload Documents
          </h2>
          <FileUpload
            projectId={id}
            onUploadComplete={async () => {
              const proj = await getProject(id);
              setProject(proj);
            }}
          />
        </div>
        <div>
          <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-[var(--text-dim)] mb-4">
            Analysis
          </h2>
          <div className="card p-5">
            <p className="text-sm text-[var(--text-dim)] mb-4">
              Run AI analysis across all uploaded documents against target
              standards. Each document is analyzed clause-by-clause.
            </p>
            <button
              className="btn-primary w-full"
              disabled={project.document_count === 0}
              onClick={async () => {
                try {
                  const token = (() => {
                    try {
                      const stored = localStorage.getItem(
                        "sb-rkiaocarugdbcgtonfuq-auth-token"
                      );
                      if (stored)
                        return JSON.parse(stored).access_token || null;
                    } catch {}
                    return null;
                  })();
                  const res = await fetch(
                    `${API_URL}/api/due-diligence/projects/${id}/analyze`,
                    {
                      method: "POST",
                      headers: {
                        "Content-Type": "application/json",
                        ...(token
                          ? { Authorization: `Bearer ${token}` }
                          : {}),
                      },
                      body: JSON.stringify({ project_id: id }),
                    }
                  );
                  if (!res.ok) throw new Error(await res.text());
                  // Refresh after a moment to see results
                  setTimeout(async () => {
                    const [proj, devs] = await Promise.all([
                      getProject(id),
                      getDeviations(id).catch(() => ({
                        deviations: [],
                        summary: null,
                      })),
                    ]);
                    setProject(proj);
                    setDeviations(devs.deviations || []);
                  }, 5000);
                } catch (e: any) {
                  setError(e.message);
                }
              }}
            >
              Analyze Documents
            </button>
          </div>
        </div>
      </div>

      {/* Deviations */}
      <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-[var(--text-dim)] mb-4">
        Deviations
      </h2>

      {deviations.length === 0 ? (
        <div className="card p-6 text-center text-sm text-[var(--text-dim)]">
          No deviations found. Run analysis to detect clause-level deviations
          against target standards.
        </div>
      ) : (
        <div className="grid gap-3">
          {deviations.map((d) => (
            <div key={d.id} className="card p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs font-semibold uppercase text-[var(--secondary)]">
                      {d.clause_type}
                    </span>
                    <span className={`badge ${severityColor(d.severity)}`}>
                      {d.severity}
                    </span>
                    {d.confidence != null && (
                      <span className="text-[10px] font-mono text-[var(--text-muted)]">
                        {d.confidence}% conf
                      </span>
                    )}
                  </div>
                  {d.clause_location && (
                    <span className="text-xs text-[var(--text-dim)] font-mono">
                      {d.clause_location}
                    </span>
                  )}
                </div>
                {d.review_decision ? (
                  <span className="badge badge-built text-xs">
                    {d.review_decision}
                  </span>
                ) : (
                  <div className="flex gap-1">
                    <button
                      onClick={() =>
                        handleReview(d.id, "accept_risk", "Accepted risk")
                      }
                      className="text-[10px] font-mono uppercase px-2 py-1 rounded border border-[var(--border)] text-[var(--text-dim)] hover:border-[var(--metric)] hover:text-[var(--metric)]"
                    >
                      Accept
                    </button>
                    <button
                      onClick={() =>
                        handleReview(d.id, "must_fix", "Must fix")
                      }
                      className="text-[10px] font-mono uppercase px-2 py-1 rounded border border-[var(--border)] text-[var(--text-dim)] hover:border-[var(--rose)] hover:text-[var(--rose)]"
                    >
                      Must Fix
                    </button>
                    <button
                      onClick={() =>
                        handleReview(d.id, "false_positive", "Not a deviation")
                      }
                      className="text-[10px] font-mono uppercase px-2 py-1 rounded border border-[var(--border)] text-[var(--text-dim)] hover:border-[var(--slate)] hover:text-[var(--slate)]"
                    >
                      False
                    </button>
                  </div>
                )}
              </div>

              {d.deviation_summary && (
                <p className="text-sm mb-1">{d.deviation_summary}</p>
              )}
              {d.detailed_analysis && (
                <p className="text-sm text-[var(--text-dim)] mb-2 line-clamp-3">
                  {d.detailed_analysis}
                </p>
              )}
              {d.recommendation && (
                <p className="text-sm text-[var(--secondary)] font-medium">
                  Fix: {d.recommendation}
                </p>
              )}

              {d.clause_text && (
                <details className="mt-3">
                  <summary className="text-[10px] font-mono uppercase text-[var(--text-muted)] cursor-pointer hover:text-[var(--text-dim)]">
                    View clause text
                  </summary>
                  <pre className="mt-2 p-3 bg-[var(--surface2)] rounded-lg text-xs font-mono whitespace-pre-wrap text-[var(--text-dim)] max-h-48 overflow-y-auto">
                    {d.clause_text}
                  </pre>
                </details>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
