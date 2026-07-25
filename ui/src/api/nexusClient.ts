/**
 * NexusClient — Production API layer with retry, backoff, cancellation.
 * Pattern from: frontend-api-integration-patterns skill
 */

import { API } from "@/api/config";

// ─── Error Normalization ────────────────────────────────────────
export class NexusApiError extends Error {
  status: number;
  payload: unknown;
  retryable: boolean;

  constructor(message: string, status: number, payload: unknown = null) {
    super(message);
    this.name = "NexusApiError";
    this.status = status;
    this.payload = payload;
    this.retryable = status >= 500 || status === 0; // 0 = network error
  }
}

// ─── Retry with Exponential Backoff ─────────────────────────────
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function fetchWithBackoff<T>(
  fn: () => Promise<T>,
  retries = 3,
  delay = 300
): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    const isRetryable = err instanceof NexusApiError ? err.retryable : true;
    if (retries <= 0 || !isRetryable) throw err;
    const nextDelay = delay * 2 + Math.random() * 100;
    await sleep(nextDelay);
    return fetchWithBackoff(fn, retries - 1, nextDelay);
  }
}

// ─── Core API Client ────────────────────────────────────────────
export async function nexusApi<T = unknown>(
  endpoint: string,
  options: RequestInit & { retry?: number; signal?: AbortSignal } = {}
): Promise<T> {
  const { retry = 2, signal, ...fetchOpts } = options;

  const doFetch = async (): Promise<T> => {
    const res = await fetch(`${API}/api${endpoint}`, {
      headers: { "Content-Type": "application/json" },
      signal,
      ...fetchOpts,
    });

    if (!res.ok) {
      let payload = null;
      try { payload = await res.json(); } catch {}
      throw new NexusApiError(
        (payload as { error?: string })?.error || `HTTP ${res.status}`,
        res.status,
        payload
      );
    }

    if (res.status === 204) return null as unknown as T;
    const text = await res.text();
    return (text ? JSON.parse(text) : null) as T;
  };

  return fetchWithBackoff(doFetch, retry);
}

// ─── Convenience Methods ────────────────────────────────────────
export const nexusGet = <T = unknown>(endpoint: string, signal?: AbortSignal) =>
  nexusApi<T>(endpoint, { signal });

export const nexusPost = <T = unknown>(endpoint: string, body: unknown, signal?: AbortSignal) =>
  nexusApi<T>(endpoint, {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });

// ─── React Hook Helper: Race-Safe Fetch ─────────────────────────
export function createAbortableFetch() {
  let controller: AbortController | null = null;

  return {
    fetch: <T>(endpoint: string, options?: RequestInit) => {
      controller?.abort();
      controller = new AbortController();
      return nexusApi<T>(endpoint, { ...options, signal: controller.signal });
    },
    abort: () => controller?.abort(),
  };
}

// ─── Debounced Fetch (for search inputs) ────────────────────────
export function debouncedFetch<T>(
  fn: (query: string) => Promise<T>,
  delayMs = 300
): (query: string) => Promise<T> {
  let timeoutId: ReturnType<typeof setTimeout>;
  let lastController: AbortController | null = null;

  return (query: string) => {
    lastController?.abort();
    clearTimeout(timeoutId);
    lastController = new AbortController();

    return new Promise<T>((resolve, reject) => {
      timeoutId = setTimeout(async () => {
        try {
          resolve(await fn(query));
        } catch (err) {
          if (err instanceof DOMException && err.name === "AbortError") return;
          reject(err);
        }
      }, delayMs);
    });
  };
}
