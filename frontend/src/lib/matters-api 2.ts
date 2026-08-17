import { fetchAPI } from "./api";

export interface CreatedMatter {
  matter: {
    id: string;
    name: string;
    jurisdiction?: string | null;
    practice_area?: string | null;
    adverse_parties?: string[];
    risk_level?: string | null;
  };
  enrichment: {
    matter_id?: string;
    queries_run?: number;
    reason?: string;
    error?: string;
    results?: {
      query_type: string;
      query_text: string;
      cached?: boolean;
      results_count?: number;
      error?: string;
    }[];
  };
}

export const createMatter = (data: {
  name: string;
  description?: string;
  jurisdiction?: string;
  practice_area?: string;
  adverse_parties?: string[];
  risk_level?: string;
  risk_score?: number;
}) =>
  fetchAPI<CreatedMatter>("/api/matters", {
    method: "POST",
    body: JSON.stringify(data),
  });
