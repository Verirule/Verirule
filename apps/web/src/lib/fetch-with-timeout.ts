export class FetchTimeoutError extends Error {
  timeoutMs: number;

  constructor(timeoutMs: number) {
    super(`Request timed out after ${timeoutMs}ms`);
    this.name = "FetchTimeoutError";
    this.timeoutMs = timeoutMs;
  }
}

type JsonWithRequestId = {
  request_id?: unknown;
};

type FetchWithTimeoutInit = RequestInit & {
  timeoutMs?: number;
};

export type FetchWithTimeoutResult<TJson> = {
  ok: boolean;
  status: number;
  json: TJson | null;
  requestId: string | null;
};

function resolveRequestId<TJson>(response: Response, payload: TJson | null): string | null {
  const headerValue = response.headers.get("x-request-id");
  if (headerValue && headerValue.trim()) {
    return headerValue.trim();
  }

  if (payload && typeof payload === "object") {
    const maybeRequestId = (payload as JsonWithRequestId).request_id;
    if (typeof maybeRequestId === "string" && maybeRequestId.trim()) {
      return maybeRequestId.trim();
    }
  }

  return null;
}

export async function fetchWithTimeout<TJson = unknown>(
  input: RequestInfo | URL,
  init: FetchWithTimeoutInit = {},
): Promise<FetchWithTimeoutResult<TJson>> {
  const { timeoutMs = 15_000, ...requestInit } = init;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(input, { ...requestInit, signal: controller.signal });
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new FetchTimeoutError(timeoutMs);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }

  const payload = (await response.json().catch(() => null)) as TJson | null;

  return {
    ok: response.ok,
    status: response.status,
    json: payload,
    requestId: resolveRequestId(response, payload),
  };
}
