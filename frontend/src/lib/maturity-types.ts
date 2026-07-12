// ---------------------------------------------------------------------------
// AI Maturity Assessment — TypeScript Types
// ---------------------------------------------------------------------------

export interface MaturityDimension {
  key: string;          // e.g. "knowledge_management"
  name: string;         // e.g. "Knowledge Management & Precedent"
  score: number;        // 1-5
  rationale: string;    // evidence cited from documents
}

export interface StageGap {
  from_level: number;
  to_level: number;
  from_label: string;
  to_label: string;
  whats_missing: string;
  what_it_unlocks: string;
}

export interface MaturityAssessment {
  id: string;
  client_id?: string;
  version: number;
  overall_level: number;           // 1-5
  overall_level_label: string;     // "AI Aware", "AI Ready", etc.
  bottleneck_dimension: string;    // dimension key
  bottleneck_why: string;
  bottleneck_what_this_means: string;
  dimensions: MaturityDimension[];
  stage_gaps: StageGap[];
  summary: string;
  document_count: number;
  document_ids?: string[];
  cost_usd?: number;
  created_by?: string;
  created_at: string;
}

export interface MaturityAssessmentSummary {
  id: string;
  version: number;
  overall_level: number;
  overall_level_label: string;
  bottleneck_dimension: string;
  document_count: number;
  cost_usd: number;
  created_at: string;
}

export interface MaturityDocument {
  id: string;
  title: string;
  document_type: string;
  source_file: string | null;
  chunk_count: number;
  is_active?: boolean;
  created_at: string;
}

export interface BulkUploadResult {
  uploaded: MaturityDocument[];
  errors: { filename: string; error: string }[];
  total: number;
  succeeded: number;
  failed: number;
}

export const LEVEL_LABELS: Record<number, string> = {
  1: "AI Aware",
  2: "AI Ready",
  3: "AI Capable",
  4: "AI Mature",
  5: "AI Native",
};

export const LEVEL_COLORS: Record<number, string> = {
  1: "bg-red-500",
  2: "bg-amber-500",
  3: "bg-yellow-500",
  4: "bg-blue-500",
  5: "bg-green-500",
};

export const DIM_LABELS: Record<string, string> = {
  knowledge_management: "Knowledge & Precedent",
  workflow_process: "Workflow & Process",
  governance_risk: "Governance & Risk",
  team_capability: "Team AI Literacy",
  technology_data: "Technology & Data",
};
