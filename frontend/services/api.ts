import axios from "axios";
import type { AnalyzeResponse, Artifacts, ArtifactsSummary, WorkflowStatus, StageInfo } from "@/types";

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

// ──────────────── SSE Event Types ────────────────

export type SSEEventType = "start" | "stage_update" | "complete";

export interface SSEStartEvent {
  event: "start";
  status: string;
  stages: Record<string, { status: string; started_at: string | null; completed_at: string | null }>;
}

export interface SSEStageUpdateEvent {
  event: "stage_update";
  stage: string;
  status: string;
  count?: number;
  reviews_count?: number;
  error?: string;
}

export interface SSECompleteEvent {
  event: "complete";
  status: string;
  stages: Record<string, StageInfo>;
  artifacts: ArtifactsSummary;
  artifacts_data: Artifacts;
  duration_ms?: number;
  error?: string;
}

export type SSEEvent = SSEStartEvent | SSEStageUpdateEvent | SSECompleteEvent;

// ──────────────── API functions ────────────────

/**
 * Trigger a full review analysis workflow for an App Store app.
 *
 * Stages: collect → clean → classify → extract_findings → generate_prd → generate_tests
 *
 * @param url        - App Store URL of the app to analyze.
 * @param goal       - Optional analysis goal to focus the workflow.
 * @param importData - Optional raw review data string (JSON/CSV).
 * @param signal     - Optional AbortSignal for request cancellation.
 * @returns          - WorkflowResponse with per-stage status and artifact counts.
 */
export async function analyzeReviews(
  url?: string,
  goal?: string,
  importData?: string,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  try {
    const { data } = await api.post<AnalyzeResponse>(
      "/api/analyze",
      {
        url: url || undefined,
        goal: goal || undefined,
        import_data: importData || undefined,
      },
      { timeout: 600000, signal },  // 10 min — LLM pipeline is slow
    );
    return data;
  } catch (error) {
    if (signal?.aborted) {
      throw new ApiError("Request cancelled", 0);
    }
    handleError(error);
  }
}

/**
 * Trigger a review analysis workflow with SSE streaming for real-time progress.
 *
 * Uses fetch + ReadableStream to consume Server-Sent Events.
 * Each parsed SSE event fires the onEvent callback immediately.
 * The promise resolves when a 'complete' event is received.
 *
 * @param url        - App Store URL of the app to analyze.
 * @param goal       - Optional analysis goal to focus the workflow.
 * @param importData - Optional raw review data string (JSON/CSV).
 * @param onEvent    - Callback invoked for each SSE event (start, stage_update, complete).
 * @param signal     - Optional AbortSignal for request cancellation.
 * @returns          - AnalyzeResponse built from the final 'complete' event.
 */
export async function analyzeReviewsStreaming(
  url?: string,
  goal?: string,
  importData?: string,
  onEvent?: (event: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  const response = await fetch(`${backendUrl}/api/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      url: url || undefined,
      goal: goal || undefined,
      import_data: importData || undefined,
    }),
    signal,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const detail = errorData?.detail ?? response.statusText;
    if (response.status === 400) throw new ValidationError(detail);
    if (response.status === 500) throw new ServerError(detail);
    throw new ApiError(detail, response.status, detail);
  }

  if (!response.body) {
    throw new ApiError("Response body is empty", 0);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  return new Promise<AnalyzeResponse>((resolve, reject) => {
    (async () => {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          if (signal?.aborted) {
            reader.cancel();
            reject(new ApiError("Request cancelled", 0));
            return;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          // Keep any incomplete line in the buffer for the next chunk
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;

            const jsonStr = line.slice(6).trim();
            if (!jsonStr) continue;

            try {
              const event = JSON.parse(jsonStr) as SSEEvent;
              onEvent?.(event);

              if (event.event === "complete") {
                reader.cancel();
                resolve({
                  status: event.status as WorkflowStatus,
                  stages: event.stages ?? {},
                  artifacts: event.artifacts ?? {
                    reviews_count: 0, cleaned_count: 0, classified_count: 0,
                    findings_count: 0, requirements_count: 0, test_cases_count: 0,
                  },
                  artifacts_data: event.artifacts_data ?? null,
                  error: event.error ?? null,
                  started_at: null,
                  completed_at: null,
                  duration_ms: event.duration_ms ?? null,
                });
                return;
              }
            } catch {
              // Skip malformed JSON lines
            }
          }
        }

        reject(new ApiError("Stream ended without complete event", 0));
      } catch (error) {
        reader.cancel();
        if (signal?.aborted) {
          reject(new ApiError("Request cancelled", 0));
        } else if (error instanceof ApiError) {
          reject(error);
        } else {
          reject(new ApiError(
            error instanceof Error ? error.message : "Stream error",
            0,
          ));
        }
      }
    })();
  });
}

/**
 * Check if the backend API is healthy.
 */
export async function healthCheck(): Promise<{ status: string }> {
  try {
    const { data } = await api.get<{ status: string }>(
      "/api/health",
      { timeout: 5000 },  // 5s — fast failure when backend is down
    );
    return data;
  } catch (error) {
    handleError(error);
  }
}