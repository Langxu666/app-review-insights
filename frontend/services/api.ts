import axios from "axios";
import type { AnalyzeResponse } from "@/types";

// ──────────────── Axios instance ────────────────

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

export default api;

// ──────────────── Error types ────────────────

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class ValidationError extends ApiError {
  constructor(detail: string) {
    super(`Invalid request: ${detail}`, 400, detail);
    this.name = "ValidationError";
  }
}

export class ServerError extends ApiError {
  constructor(detail: string) {
    super(`Server error: ${detail}`, 500, detail);
    this.name = "ServerError";
  }
}

// ──────────────── Helpers ────────────────

function handleError(error: unknown): never {
  if (error instanceof ApiError) {
    throw error;
  }

  if (error && typeof error === "object" && "isAxiosError" in error) {
    const axiosErr = error as unknown as {
      response?: { status: number; data?: { detail?: string } };
      message: string;
    };

    const status = axiosErr.response?.status ?? 0;
    const detail = axiosErr.response?.data?.detail ?? axiosErr.message;

    if (status === 400) {
      throw new ValidationError(detail);
    }
    if (status === 500) {
      throw new ServerError(detail);
    }
    throw new ApiError(detail, status, detail);
  }

  if (error instanceof Error) {
    throw new ApiError(error.message, 0);
  }

  throw new ApiError("An unknown error occurred", 0);
}

// ──────────────── API functions ────────────────

/**
 * Trigger a full review analysis workflow for an App Store app.
 *
 * Stages: collect → clean → classify → extract_findings → generate_prd → generate_tests
 *
 * @param url  - App Store URL of the app to analyze.
 * @param goal - Optional analysis goal to focus the workflow.
 * @returns    - WorkflowResponse with per-stage status and artifact counts.
 */
export async function analyzeReviews(
  url: string,
  goal?: string,
): Promise<AnalyzeResponse> {
  try {
    const { data } = await api.post<AnalyzeResponse>("/api/analyze", {
      url,
      goal: goal || undefined,
    });
    return data;
  } catch (error) {
    handleError(error);
  }
}

/**
 * Check if the backend API is healthy.
 */
export async function healthCheck(): Promise<{ status: string }> {
  try {
    const { data } = await api.get<{ status: string }>("/api/health");
    return data;
  } catch (error) {
    handleError(error);
  }
}