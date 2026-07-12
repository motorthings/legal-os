"use client";

import { useState, useEffect, useCallback } from "react";
import { Loader2, AlertCircle, FileText, History } from "lucide-react";
import DocumentUpload from "@/components/maturity/DocumentUpload";
import MaturityModelCard from "@/components/maturity/MaturityModelCard";
import type {
  MaturityAssessment,
  MaturityAssessmentSummary,
  MaturityDocument,
} from "@/lib/maturity-types";
import {
  getAssessments,
  getAssessment,
  getMaturityDocuments,
  runAssessment,
} from "@/lib/maturity-api";

export default function MaturityPage() {
  const [documents, setDocuments] = useState<MaturityDocument[]>([]);
  const [assessments, setAssessments] = useState<MaturityAssessmentSummary[]>(
    []
  );
  const [currentAssessment, setCurrentAssessment] =
    useState<MaturityAssessment | null>(null);
  const [isAssessing, setIsAssessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Load documents and assessments on mount
  useEffect(() => {
    Promise.all([
      getMaturityDocuments().catch(() => []),
      getAssessments().catch(() => []),
    ])
      .then(([docs, ass]) => {
        setDocuments(docs.filter((d: MaturityDocument) => d.is_active !== false));
        setAssessments(ass);
        // Load latest assessment if exists
        if (ass.length > 0) {
          return getAssessment(ass[0].id);
        }
        return null;
      })
      .then((latest) => {
        if (latest) setCurrentAssessment(latest);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleDocumentsUploaded = useCallback(
    (newDocs: MaturityDocument[]) => {
      setDocuments((prev) => [...newDocs, ...prev]);
    },
    []
  );

  const handleRunAssessment = useCallback(
    async (docIds: string[]) => {
      setIsAssessing(true);
      setError(null);
      try {
        const result = await runAssessment(docIds);
        setCurrentAssessment(result);
        // Refresh assessments list
        const list = await getAssessments();
        setAssessments(list);
      } catch (err: any) {
        setError(err.message || "Assessment failed");
      } finally {
        setIsAssessing(false);
      }
    },
    []
  );

  const handleViewAssessment = useCallback(async (id: string) => {
    setError(null);
    try {
      const result = await getAssessment(id);
      setCurrentAssessment(result);
    } catch (err: any) {
      setError(err.message);
    }
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-[var(--text-muted)]" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1
          className="text-2xl font-bold text-[var(--text)] mb-2"
          style={{ fontFamily: "'Fraunces', Georgia, serif" }}
        >
          AI Maturity Assessment
        </h1>
        <p className="text-sm text-[var(--text-dim)] max-w-2xl">
          Upload your firm's operational documents — policies, playbooks,
          technology docs, training materials, process maps — and get an honest
          assessment of your AI readiness across five legal-specific dimensions.
          The bottleneck principle applies: you're only as mature as your weakest
          dimension.
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-start gap-2 text-sm text-red-600 dark:text-red-400 mb-6 p-4 rounded-lg bg-red-50 dark:bg-red-900/20">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Document upload */}
      <DocumentUpload
        onDocumentsUploaded={handleDocumentsUploaded}
        existingDocs={documents}
        onRunAssessment={handleRunAssessment}
        isAssessing={isAssessing}
      />

      {/* Assessment results */}
      {isAssessing && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-12 text-center mb-6">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-[var(--primary)]" />
          <p className="text-sm text-[var(--text-dim)]">
            Analyzing documents and assessing maturity across all five
            dimensions...
          </p>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            This typically takes 15-30 seconds
          </p>
        </div>
      )}

      {currentAssessment && !isAssessing && (
        <>
          {/* Summary prose */}
          {currentAssessment.summary && (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 mb-6">
              <h3 className="text-sm font-semibold text-[var(--text)] mb-2">
                Assessment Summary
              </h3>
              <p className="text-sm text-[var(--text-dim)] leading-relaxed">
                {currentAssessment.summary}
              </p>
              <div className="flex items-center gap-4 mt-3 text-xs text-[var(--text-muted)]">
                <span>
                  Documents analyzed: {currentAssessment.document_count}
                </span>
                {currentAssessment.cost_usd !== undefined && (
                  <span>
                    Cost: ${currentAssessment.cost_usd.toFixed(4)}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Maturity model card */}
          <MaturityModelCard assessment={currentAssessment} />
        </>
      )}

      {/* Empty state */}
      {!currentAssessment && !isAssessing && documents.length === 0 && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-12 text-center">
          <FileText className="w-12 h-12 mx-auto mb-4 text-[var(--text-muted)]" />
          <h3 className="text-lg font-semibold text-[var(--text)] mb-2">
            No documents uploaded yet
          </h3>
          <p className="text-sm text-[var(--text-dim)] max-w-md mx-auto">
            Upload your firm's operational documents above to get started. The
            more context you provide, the richer the assessment.
          </p>
        </div>
      )}

      {/* Past assessments */}
      {assessments.length > 1 && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 mt-6">
          <div className="flex items-center gap-2 mb-4">
            <History className="w-4 h-4 text-[var(--text-muted)]" />
            <h3 className="text-sm font-semibold text-[var(--text)]">
              Past Assessments
            </h3>
          </div>
          <div className="space-y-1">
            {assessments.slice(1).map((a) => (
              <button
                key={a.id}
                onClick={() => handleViewAssessment(a.id)}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-left hover:bg-[var(--surface2)] transition-colors"
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    a.overall_level >= 4
                      ? "bg-green-500"
                      : a.overall_level >= 3
                        ? "bg-yellow-500"
                        : "bg-red-500"
                  }`}
                />
                <span className="flex-1 text-[var(--text)]">
                  {a.overall_level_label}
                </span>
                <span className="text-xs text-[var(--text-muted)]">
                  {a.document_count} docs
                </span>
                <span className="text-xs text-[var(--text-muted)]">
                  {new Date(a.created_at).toLocaleDateString()}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
