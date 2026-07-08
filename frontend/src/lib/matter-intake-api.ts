import type { EvaluateResponse } from "./matter-intake-types";

const API_BASE = process.env.NEXT_PUBLIC_MATTER_INTAKE_API_URL || "https://document-matter-intake-eval.fly.dev";

export async function evaluateMatter(summary: string): Promise<EvaluateResponse> {
  const response = await fetch(`${API_BASE}/api/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ matter_summary: summary }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Evaluation failed (${response.status}): ${errorText}`);
  }

  return response.json();
}

export interface UploadResult {
  success: boolean;
  filename: string;
  text: string;
  length: number;
}

export async function uploadFile(file: File): Promise<UploadResult> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Upload failed (${response.status}): ${errorText}`);
  }

  return response.json();
}
