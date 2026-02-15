import { randomUUID } from "crypto";
import { NextResponse } from "next/server";

const HEALTHZ_TIMEOUT_MS = 3_000;

function getApiBaseUrl(): string | null {
  const raw = process.env.VERIRULE_API_URL?.trim();
  if (!raw || /['"\s]/.test(raw)) {
    return null;
  }

  try {
    return new URL(raw).toString().replace(/\/$/, "");
  } catch {
    return null;
  }
}

function requestIdFromHeaders(headers: Headers): string {
  const headerValue = headers.get("x-request-id");
  if (headerValue && headerValue.trim()) {
    return headerValue.trim();
  }
  return randomUUID();
}

function withRequestId(response: NextResponse, requestId: string): NextResponse {
  response.headers.set("X-Request-ID", requestId);
  return response;
}

function apiUnreachable(requestId: string): NextResponse {
  return withRequestId(NextResponse.json({ error: "API unreachable", requestId }, { status: 502 }), requestId);
}

function parseJsonObject(payload: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(payload) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    return null;
  }
  return null;
}

export async function GET(request: Request) {
  const requestId = requestIdFromHeaders(request.headers);
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return apiUnreachable(requestId);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), HEALTHZ_TIMEOUT_MS);

  try {
    const upstreamResponse = await fetch(`${apiBaseUrl}/healthz`, {
      method: "GET",
      headers: {
        Accept: "application/json",
        "X-Request-ID": requestId,
      },
      cache: "no-store",
      signal: controller.signal,
    });

    const upstreamRequestId = upstreamResponse.headers.get("x-request-id")?.trim() || requestId;
    const upstreamJson = parseJsonObject(await upstreamResponse.text());
    if (upstreamResponse.ok) {
      return withRequestId(NextResponse.json(upstreamJson ?? { status: "ok" }, { status: 200 }), upstreamRequestId);
    }
    return apiUnreachable(upstreamRequestId);
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return apiUnreachable(requestId);
    }
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error("api/healthz proxy failed", { request_id: requestId, message });
    return apiUnreachable(requestId);
  } finally {
    clearTimeout(timeout);
  }
}
