import type {
  MaturityAssessment,
  MaturityAssessmentSummary,
  MaturityDocument,
  BulkUploadResult,
} from "./maturity-types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

let _getToken: (() => string | null) | null = null;
export function setTokenProvider(fn: (() => string | null) | null) {
  _getToken = fn;
}

function getAccessToken(): string | null {
  if (_getToken) return _getToken();
  try {
    const stored = localStorage.getItem("sb-rkiaocarugdbcgtonfuq-auth-token");
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed.access_token || null;
    }
  } catch {}
  return null;
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options?.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error: ${res.status} ${res.statusText} — ${body}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Assessments
// ---------------------------------------------------------------------------

export const getAssessments = () =>
  fetchAPI<MaturityAssessmentSummary[]>("/api/maturity/assessments");

export const getAssessment = (id: string) =>
  fetchAPI<MaturityAssessment>(`/api/maturity/assessments/${id}`);

export const runAssessment = (documentIds: string[]) =>
  fetchAPI<MaturityAssessment>("/api/maturity/assessments", {
    method: "POST",
    body: JSON.stringify({ document_ids: documentIds }),
  });

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

export const getMaturityDocuments = () =>
  fetchAPI<MaturityDocument[]>("/api/maturity/documents");

export const uploadDocument = async (file: File): Promise<MaturityDocument> => {
  const formData = new FormData();
  formData.append("file", file);
  return fetchAPI<MaturityDocument>("/api/maturity/documents/upload", {
    method: "POST",
    body: formData,
  });
};

export const uploadDocuments = async (
  files: File[]
): Promise<BulkUploadResult> => {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  return fetchAPI<BulkUploadResult>("/api/maturity/documents/upload-bulk", {
    method: "POST",
    body: formData,
  });
};

export const deleteDocument = (id: string) =>
  fetchAPI<{ status: string }>(`/api/maturity/documents/${id}`, {
    method: "DELETE",
  });
