import { createClient } from "@/lib/supabase/server";
import { randomUUID } from "crypto";
import { NextResponse } from "next/server";

const JOBS_TIMEOUT_MS = 8_000;

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
  const value = headers.get("x-request-id");
  if (value && value.trim()) {
    return value.trim();
  }
  return randomUUID();
}

function withRequestId(response: NextResponse, requestId: string): NextResponse {
  response.headers.set("X-Request-ID", requestId);
  return response;
}

function apiError(status: number, message: string, requestId: string): NextResponse {
  return withRequestId(NextResponse.json({ error: message, requestId }, { status }), requestId);
}

function parseJson(value: string): unknown {
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return null;
  }
}

async function getAccessToken(requestId: string): Promise<{ token: string | null; response: NextResponse | null }> {
  let supabase: Awaited<ReturnType<typeof createClient>>;
  try {
    supabase = await createClient();
  } catch {
    return { token: null, response: apiError(500, "Missing required environment variables", requestId) };
  }

  const { data, error } = await supabase.auth.getSession();
  if (error || !data.session?.access_token) {
    return { token: null, response: apiError(401, "Unauthorized", requestId) };
  }
  return { token: data.session.access_token, response: null };
}

export async function GET(request: Request) {
  const requestId = requestIdFromHeaders(request.headers);
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return apiError(501, "API not configured", requestId);
  }

  const { token, response } = await getAccessToken(requestId);
  if (response || !token) {
    return response ?? apiError(401, "Unauthorized", requestId);
  }

  const requestUrl = new URL(request.url);
  const type = requestUrl.searchParams.get("type");
  const statusValue = requestUrl.searchParams.get("status") ?? "failed";
  const limit = requestUrl.searchParams.get("limit") ?? "50";

  const upstreamSearchParams = new URLSearchParams({ status: statusValue, limit });
  if (type && type.trim()) {
    upstreamSearchParams.set("type", type.trim());
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), JOBS_TIMEOUT_MS);

  try {
    const upstreamResponse = await fetch(`${apiBaseUrl}/api/v1/system/jobs?${upstreamSearchParams.toString()}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "X-Request-ID": requestId,
      },
      cache: "no-store",
      signal: controller.signal,
    });

    const upstreamRequestId = upstreamResponse.headers.get("x-request-id")?.trim() || requestId;
    const rawBody = await upstreamResponse.text();
    const parsedBody = parseJson(rawBody);

    if (upstreamResponse.ok) {
      return withRequestId(NextResponse.json(parsedBody ?? {}, { status: upstreamResponse.status }), upstreamRequestId);
    }

    if (upstreamResponse.status === 502) {
      return apiError(502, "Workspace service unavailable", upstreamRequestId);
    }
    if (upstreamResponse.status === 504) {
      return apiError(504, "Workspace service timed out", upstreamRequestId);
    }

    if (parsedBody && typeof parsedBody === "object" && !Array.isArray(parsedBody)) {
      const errorBody = parsedBody as Record<string, unknown>;
      if (!("requestId" in errorBody) && !("request_id" in errorBody)) {
        errorBody.requestId = upstreamRequestId;
      }
      return withRequestId(NextResponse.json(errorBody, { status: upstreamResponse.status }), upstreamRequestId);
    }

    return apiError(upstreamResponse.status, "Workspace service error", upstreamRequestId);
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return apiError(504, "Workspace service timed out", requestId);
    }
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error("api/system/jobs proxy failed", { request_id: requestId, message });
    return apiError(502, "Workspace service unavailable", requestId);
  } finally {
    clearTimeout(timeout);
  }
}
