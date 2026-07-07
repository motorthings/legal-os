"use client";

import { useCallback, useEffect, useState } from "react";
import {
  FileSearch, Clock, ChevronRight, X, ChevronDown, ChevronUp,
  Search, SlidersHorizontal, ArrowUpDown, RotateCcw,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Evaluation {
  id: number;
  created_at: string;
  overall_score: number;
  overall_risk_level: string;
  practice_area: string;
  practice_area_confidence: number;
  urgency_level: string;
  risk_score: number;
  conflict_type: string;
  conflict_entity: string | null;
  recommended_role: string;
  estimated_hours: number;
  completeness: number;
  clarity: number;
  summary_preview: string;
  processing_time_ms: number;
  model_used: string;
}

interface AuditTrail {
  id: number;
  created_at: string;
  overall_score: number;
  overall_risk_level: string;
  audit_trail: {
    pipeline_stages: Array<{
      stage: string;
      description: string;
      input: string;
      output: string;
      key_decisions: string[];
    }>;
    rubrics_used: Record<string, any>;
    explainability_summary: string;
  };
  rubrics?: Record<string, any>;
}

type SortField = "created_at" | "overall_score" | "practice_area" | "overall_risk_level";
type SortOrder = "asc" | "desc";

const RISK_LEVELS = ["", "high", "medium", "low"];
const URGENCY_LEVELS = ["", "immediate", "short-term", "routine"];
const PAGE_SIZE = 20;

function riskColor(level: string) {
  if (level === "high") return "text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-950/30";
  if (level === "medium") return "text-amber-700 dark:text-amber-400 bg-amber-100 dark:bg-amber-950/30";
  return "text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-950/30";
}

export default function HistoryPage() {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);

  // Search & filter state
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [practiceFilter, setPracticeFilter] = useState("");
  const [urgencyFilter, setUrgencyFilter] = useState("");
  const [sortBy, setSortBy] = useState<SortField>("created_at");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [practiceAreas, setPracticeAreas] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  // Audit slide-out
  const [auditOpen, setAuditOpen] = useState<number | null>(null);
  const [auditData, setAuditData] = useState<AuditTrail | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [expandedStages, setExpandedStages] = useState<Record<string, boolean>>({});

  const fetchEvaluations = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    params.set("limit", String(PAGE_SIZE));
    params.set("offset", String(page * PAGE_SIZE));
    params.set("sort_by", sortBy);
    params.set("sort_order", sortOrder);
    if (search) params.set("search", search);
    if (riskFilter) params.set("risk_level", riskFilter);
    if (practiceFilter) params.set("practice_area", practiceFilter);
    if (urgencyFilter) params.set("urgency_level", urgencyFilter);

    try {
      const r = await fetch(`${API_BASE}/api/evaluations?${params}`);
      const data = await r.json();
      if (data.success) {
        setEvaluations(data.evaluations);
        setTotal(data.total || 0);
      } else {
        setError(data.error || "Failed to load");
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [page, sortBy, sortOrder, search, riskFilter, practiceFilter, urgencyFilter]);

  // Fetch practice areas for dropdown
  useEffect(() => {
    fetch(`${API_BASE}/api/filters/practice-areas`)
      .then((r) => r.json())
      .then((data) => {
        if (data.success) setPracticeAreas(data.practice_areas);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchEvaluations();
  }, [fetchEvaluations]);

  const resetFilters = () => {
    setSearch("");
    setRiskFilter("");
    setPracticeFilter("");
    setUrgencyFilter("");
    setSortBy("created_at");
    setSortOrder("desc");
    setPage(0);
  };

  const hasActiveFilters = search || riskFilter || practiceFilter || urgencyFilter
    || sortBy !== "created_at" || sortOrder !== "desc";

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const openAudit = async (id: number) => {
    setAuditOpen(id);
    setAuditLoading(true);
    setAuditData(null);
    setExpandedStages({});
    try {
      const r = await fetch(`${API_BASE}/api/evaluations/${id}/audit`);
      const data = await r.json();
      if (data.success) setAuditData(data.audit_trail);
    } catch {
      setAuditData(null);
    } finally {
      setAuditLoading(false);
    }
  };

  if (loading && evaluations.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-[var(--text-primary)] tracking-tight">
          Evaluation History
        </h1>
        <p className="text-[var(--text-secondary)] mt-1 text-sm">
          Previous matter intake evaluations with full audit trails.
        </p>
      </header>

      {/* Search & filter bar */}
      <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-default)] p-4 mb-4 space-y-3">
        {/* Search row */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-secondary)]" />
            <input
              type="text"
              placeholder="Search practice area or summary…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(0); }}
              className="w-full bg-[var(--bg-secondary)] border border-[var(--border-default)] rounded-lg pl-10 pr-4 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-secondary)] focus:outline-none focus:border-primary-600/50 transition-colors"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border text-sm transition-colors ${
              showFilters
                ? "bg-primary-950/30 border-primary-700 text-[var(--text-primary)] dark:text-primary-400"
                : "border-[var(--border-default)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)]"
            }`}
          >
            <SlidersHorizontal className="w-4 h-4" />
            Filters
          </button>
          <button
            onClick={fetchEvaluations}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[var(--border-default)] text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)] transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>

        {/* Sort row — always visible */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <ArrowUpDown className="w-3.5 h-3.5 text-[var(--text-secondary)]" />
            <span className="text-xs text-[var(--text-secondary)]">Sort:</span>
          </div>
          {([
            ["created_at", "Date"],
            ["overall_score", "Score"],
            ["practice_area", "Practice Area"],
            ["overall_risk_level", "Risk Level"],
          ] as [SortField, string][]).map(([field, label]) => (
            <button
              key={field}
              onClick={() => {
                if (sortBy === field) {
                  setSortOrder(sortOrder === "desc" ? "asc" : "desc");
                } else {
                  setSortBy(field);
                  setSortOrder("desc");
                }
                setPage(0);
              }}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs transition-colors ${
                sortBy === field
                  ? "bg-primary-950/30 text-[var(--text-primary)] dark:text-primary-400 border border-primary-700"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-transparent"
              }`}
            >
              {label}
              {sortBy === field && (
                <span className="text-[10px]">{sortOrder === "desc" ? "↓" : "↑"}</span>
              )}
            </button>
          ))}
          {hasActiveFilters && (
            <button
              onClick={resetFilters}
              className="text-xs font-medium text-primary-700 hover:text-primary-800 dark:text-primary-400 dark:hover:text-primary-300 transition-colors ml-auto"
            >
              Reset all
            </button>
          )}
        </div>

        {/* Extended filters */}
        {showFilters && (
          <div className="flex items-center gap-3 pt-3 border-t border-[var(--border-default)] flex-wrap">
            <label className="flex items-center gap-1.5">
              <span className="text-xs text-[var(--text-secondary)]">Risk:</span>
              <select
                value={riskFilter}
                onChange={(e) => { setRiskFilter(e.target.value); setPage(0); }}
                className="bg-[var(--bg-secondary)] border border-[var(--border-default)] rounded-md px-2 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none focus:border-primary-600/50"
              >
                <option value="">All</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </label>
            <label className="flex items-center gap-1.5">
              <span className="text-xs text-[var(--text-secondary)]">Urgency:</span>
              <select
                value={urgencyFilter}
                onChange={(e) => { setUrgencyFilter(e.target.value); setPage(0); }}
                className="bg-[var(--bg-secondary)] border border-[var(--border-default)] rounded-md px-2 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none focus:border-primary-600/50"
              >
                <option value="">All</option>
                <option value="immediate">Immediate</option>
                <option value="short-term">Short-term</option>
                <option value="routine">Routine</option>
              </select>
            </label>
            <label className="flex items-center gap-1.5">
              <span className="text-xs text-[var(--text-secondary)]">Practice:</span>
              <select
                value={practiceFilter}
                onChange={(e) => { setPracticeFilter(e.target.value); setPage(0); }}
                className="bg-[var(--bg-secondary)] border border-[var(--border-default)] rounded-md px-2 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none focus:border-primary-600/50 max-w-[200px]"
              >
                <option value="">All</option>
                {practiceAreas.map((pa) => (
                  <option key={pa} value={pa}>{pa}</option>
                ))}
              </select>
            </label>
          </div>
        )}
      </div>

      {/* Results count */}
      <div className="text-xs text-[var(--text-secondary)] mb-3">
        {total} evaluation{total !== 1 ? "s" : ""}
        {hasActiveFilters && " matching filters"}
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-6 text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {evaluations.length === 0 ? (
        <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-default)] p-6 text-center py-16">
          <FileSearch className="w-12 h-12 text-[var(--text-muted-icon)] mx-auto mb-4" />
          <p className="text-[var(--text-secondary)]">
            {hasActiveFilters ? "No evaluations match your filters." : "No evaluations yet."}
          </p>
        </div>
      ) : (
        <>
          <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-default)] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-default)]">
                    <th className="text-left px-6 py-3 text-xs font-medium text-[var(--text-secondary)] uppercase">Date</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-[var(--text-secondary)] uppercase">Practice Area</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-[var(--text-secondary)] uppercase">Score</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-[var(--text-secondary)] uppercase">Risk</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-[var(--text-secondary)] uppercase">Staffing</th>
                    <th className="text-left px-6 py-3 text-xs font-medium text-[var(--text-secondary)] uppercase">Audit</th>
                  </tr>
                </thead>
                <tbody>
                  {evaluations.map((ev) => (
                    <tr
                      key={ev.id}
                      className="border-b border-[var(--border-default)] hover:bg-[var(--bg-hover)] transition-colors"
                    >
                      <td className="px-6 py-3 text-sm text-[var(--text-secondary)] whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5" />
                          {new Date(ev.created_at).toLocaleDateString()}
                        </div>
                      </td>
                      <td className="px-6 py-3 text-sm text-[var(--text-primary)]">
                        {ev.practice_area}
                      </td>
                      <td className="px-6 py-3 text-sm font-semibold text-[var(--text-primary)]">
                        {ev.overall_score}/100
                      </td>
                      <td className="px-6 py-3">
                        <span className={`inline-flex text-xs font-medium px-2 py-0.5 rounded-full ${riskColor(ev.overall_risk_level)}`}>
                          {ev.overall_risk_level}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-[var(--text-secondary)] max-w-[320px]">
                        {ev.recommended_role}
                      </td>
                      <td className="px-6 py-3">
                        <button
                          onClick={() => openAudit(ev.id)}
                          className="inline-flex items-center gap-1 text-xs font-medium text-primary-800 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors"
                        >
                          <FileSearch className="w-3.5 h-3.5" />
                          Audit
                          <ChevronRight className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 text-sm">
              <span className="text-[var(--text-secondary)]">
                Page {page + 1} of {totalPages}
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="px-3 py-1.5 rounded-lg border border-[var(--border-default)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-xs"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                  disabled={page >= totalPages - 1}
                  className="px-3 py-1.5 rounded-lg border border-[var(--border-default)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-xs"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Audit trail slide-out */}
      {auditOpen !== null && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/50" onClick={() => setAuditOpen(null)} />
          <div className="relative w-full max-w-2xl bg-[var(--bg-card)] h-full overflow-y-auto shadow-xl border-l border-[var(--border-default)]">
            <div className="sticky top-0 bg-[var(--bg-card)] border-b border-[var(--border-default)] p-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-[var(--text-primary)]">
                Audit Trail
              </h2>
              <button
                onClick={() => setAuditOpen(null)}
                className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-[#e2e8f0] rounded-lg hover:bg-gray-100 dark:hover:bg-[var(--bg-hover)] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6">
              {auditLoading ? (
                <div className="flex items-center justify-center h-32">
                  <div className="w-6 h-6 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : auditData ? (
                <div className="space-y-6">
                  {/* Summary */}
                  <div className="bg-primary-50 dark:bg-primary-950/20 rounded-lg p-4 border border-primary-100 dark:border-primary-900">
                    <p className="text-sm text-primary-900 dark:text-primary-200 leading-relaxed">
                      {auditData.audit_trail.explainability_summary}
                    </p>
                  </div>

                  {/* Pipeline stages */}
                  {auditData.audit_trail.pipeline_stages.map((stage) => {
                    const isExpanded = expandedStages[stage.stage] || false;
                    return (
                      <div key={stage.stage} className="border border-[var(--border-default)] rounded-lg overflow-hidden">
                        <button
                          onClick={() => setExpandedStages((prev) => ({ ...prev, [stage.stage]: !isExpanded }))}
                          className="w-full flex items-center justify-between p-4 text-left hover:bg-[var(--bg-hover)] transition-colors"
                        >
                          <div>
                            <div className="text-sm font-medium text-[var(--text-primary)]">
                              Stage {stage.stage.replace("_", " ")}: {stage.description}
                            </div>
                            <div className="text-xs text-[var(--text-secondary)] mt-1">
                              {stage.key_decisions.map((d, i) => (
                                <div key={i}>{d}</div>
                              ))}
                            </div>
                          </div>
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4 text-gray-400 flex-shrink-0" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
                          )}
                        </button>
                        {isExpanded && (
                          <div className="border-t border-[var(--border-default)] p-4 space-y-4 bg-gray-50/50 dark:bg-[#1a2236]/50">
                            <div>
                              <div className="text-xs font-medium text-[var(--text-secondary)] mb-1 uppercase">Input (Raw Prompt)</div>
                              <pre className="text-xs text-gray-700 dark:text-[#cbd5e1] whitespace-pre-wrap font-mono bg-[var(--bg-card)] rounded p-3 border border-[var(--border-default)] max-h-48 overflow-y-auto">
                                {stage.input}
                              </pre>
                            </div>
                            <div>
                              <div className="text-xs font-medium text-[var(--text-secondary)] mb-1 uppercase">Output (Raw Response)</div>
                              <pre className="text-xs text-gray-700 dark:text-[#cbd5e1] whitespace-pre-wrap font-mono bg-[var(--bg-card)] rounded p-3 border border-[var(--border-default)] max-h-48 overflow-y-auto">
                                {stage.output}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {/* Rubrics used */}
                  {auditData.rubrics && Object.keys(auditData.rubrics).length > 0 && (
                    <div className="border border-[var(--border-default)] rounded-lg p-4">
                      <div className="text-sm font-medium text-[var(--text-primary)] mb-3">
                        Rubrics Used (version snapshot)
                      </div>
                      <pre className="text-xs text-gray-700 dark:text-[#cbd5e1] whitespace-pre-wrap font-mono bg-[var(--bg-secondary)] rounded p-3 max-h-64 overflow-y-auto">
                        {JSON.stringify(auditData.rubrics, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-[var(--text-secondary)]">Failed to load audit trail.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
