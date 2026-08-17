import { fetchAPI } from "./api";

export type QueryType =
  | "concept_search"
  | "text_search"
  | "law_search"
  | "citation_lookup";

export interface ResearchResult {
  source: string;
  source_id?: string | null;
  case_id?: string | null;
  title: string;
  citation?: string | null;
  jurisdiction?: string | null;
  court?: string | null;
  decision_year?: number | null;
  source_url?: string | null;
  snippet?: string | null;
  summary?: string | null;
  treatment?: string | null;
  treatment_category?: string | null;
  is_good_law?: boolean | null;
  authority_label?: string | null;
  why_relevant?: string | null;
  raw?: Record<string, any>;
}

export interface ResearchResponse {
  query_id?: string | null;
  query_type: string;
  query_text: string;
  cached: boolean;
  results: ResearchResult[];
  processing_time_ms: number;
  error?: string | null;
}

export interface DescrybeStatus {
  connected: boolean;
  redirect_uri: string;
}

export const getDescrybeStatus = () =>
  fetchAPI<DescrybeStatus>("/api/descrybe/status");

export const connectDescrybe = (returnTo: string) =>
  fetchAPI<{ authorization_url: string }>(
    `/api/descrybe/connect?return_to=${encodeURIComponent(returnTo)}`
  );

export const disconnectDescrybe = () =>
  fetchAPI<{ connected: boolean }>("/api/descrybe/disconnect", {
    method: "POST",
  });

export async function runResearch(opts: {
  query_type: QueryType;
  query_text: string;
  jurisdiction?: string;
  limit?: number;
}): Promise<ResearchResponse> {
  return fetchAPI<ResearchResponse>("/api/legal-research/research", {
    method: "POST",
    body: JSON.stringify({
      query_type: opts.query_type,
      query_text: opts.query_text,
      jurisdiction: opts.jurisdiction || undefined,
      limit: opts.limit ?? 10,
    }),
  });
}

export async function verifyQuote(caseId: string, quote: string) {
  return fetchAPI<{ found: boolean; matched_text?: string; opinion_count_checked?: number }>(
    "/api/legal-research/verify-quote",
    { method: "POST", body: JSON.stringify({ case_id: caseId, quote }) }
  );
}

export interface CaseStatus {
  indicator?: string;
  weight?: string;
  category?: string;
  treatment_status?: number;
}

export interface CaseSummary {
  summary?: string;
  summary_type?: string;
  author?: string;
  opinion_type?: string;
  summary_available?: boolean;
}

export interface CitingCase {
  case_id: string;
  title: string;
  citation?: string;
  court?: string;
  decision_date?: string;
  case_level_indicator?: string;
  case_level_category?: string;
  url?: string;
}

export const getCaseStatus = (caseId: string) =>
  fetchAPI<CaseStatus>(`/api/legal-research/cases/${caseId}/status`);

export const getCaseSummary = (caseId: string) =>
  fetchAPI<CaseSummary>(`/api/legal-research/cases/${caseId}/summary`);

export const getCitingCases = (caseId: string) =>
  fetchAPI<{
    overall_indicator?: string;
    total_records?: number;
    truncated?: boolean;
    results?: CitingCase[];
  }>(`/api/legal-research/cases/${caseId}/citing`);
