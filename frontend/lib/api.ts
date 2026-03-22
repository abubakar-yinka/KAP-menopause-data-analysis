/** API utility functions for the KAP Study backend. */

import type { AnalysisResult } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Upload a file and run the analysis pipeline.
 * Returns the JSON summary + session ID for downloading Excel files.
 */
export async function analyzeFile(file: File): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `Analysis failed (${res.status})`);
  }

  return res.json();
}

/** Build the download URL for an Excel report. */
export function getDownloadUrl(
  type: "results" | "cleaned",
  sessionId: string,
): string {
  return `${API_BASE}/api/download/${type}/${sessionId}`;
}
