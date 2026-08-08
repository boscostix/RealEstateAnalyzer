import { getApiBaseUrl } from "@/lib/env";

import type { ApiErrorResponse, StructuredApiError } from "./types";

export class ApiClientError extends Error {
  readonly status: number;
  readonly details: StructuredApiError;

  constructor(status: number, details: StructuredApiError) {
    super(details.message);
    this.name = "ApiClientError";
    this.status = status;
    this.details = details;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  timeoutMs?: number;
};

const DEFAULT_TIMEOUT_MS = 12_000;

export async function fetchJson<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs ?? DEFAULT_TIMEOUT_MS);

  try {
    const response = await fetch(`${getApiBaseUrl()}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
      cache: "no-store",
    });

    const text = await response.text();
    const payload = text ? (JSON.parse(text) as unknown) : null;

    if (!response.ok) {
      const normalized = normalizeApiError(response.status, payload);
      throw new ApiClientError(response.status, normalized);
    }

    return payload as T;
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }

    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiClientError(408, {
        code: "request_timeout",
        message: "The request took too long to complete.",
        retryable: true,
      });
    }

    throw new ApiClientError(500, {
      code: "network_error",
      message: "Unable to reach the backend service.",
      retryable: true,
    });
  } finally {
    clearTimeout(timeout);
  }
}

function normalizeApiError(status: number, payload: unknown): StructuredApiError {
  const candidate = payload as Partial<ApiErrorResponse> | null;
  if (candidate?.error?.code && candidate.error.message) {
    return candidate.error;
  }

  return {
    code: `http_${status}`,
    message: "The backend returned an unexpected error response.",
    retryable: status >= 500,
  };
}
