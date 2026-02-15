import { createClient } from "@/lib/supabase/server";
import { randomUUID } from "crypto";
import { NextResponse } from "next/server";

const HEALTH_TIMEOUT_MS = 5_000;

function getApiBaseUrl(): string | null {
  const raw = process.env.VERIRULE_API_URL?.trim();
  if (!raw || /['"\s]/.test(raw)) {
    return null;
  }

  try {
    const parsed = new URL(raw);
    return parsed.toString().replace(/\/$/, "");
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

function apiError(status: number, message: string, code: string, requestId: string): NextResponse {
  return withRequestId(NextResponse.json({ message, code, request_id: requestId }, { status }), requestId);
}

function parseJsonObject(value: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(value) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    return null;
  }
  return null;
}

async function getAccessToken(requestId: string): Promise<{ token: string | null; response: NextResponse | null }> {
  let supabase: Awaited<ReturnType<typeof createClient>>;
  try {
    supabase = await createClient();
  } catch {
    return { token: null, response: apiError(500, "Missing required environment variables", "env_missing", requestId) };
  }

  const { data, error } = await supabase.auth.getSession();
  if (error || !data.session?.access_token) {
    return { token: null, response: apiError(401, "Unauthorized", "unauthorized", requestId) };
  }

  return { token: data.session.access_token, response: null };
}

export async function GET(request: Request) {
  const requestId = requestIdFromHeaders(request.headers);
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return apiError(501, "API not configured", "api_not_configured", requestId);
  }

  const { token, response } = await getAccessToken(requestId);
  if (response || !token) {
    return response ?? apiError(401, "Unauthorized", "unauthorized", requestId);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);

  try {
    const upstreamResponse = await fetch(`${apiBaseUrl}/api/v1/system/health`, {
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
    const upstreamBodyText = await upstreamResponse.text();
    const upstreamJson = parseJsonObject(upstreamBodyText);

    if (upstreamResponse.ok) {
      return withRequestId(NextResponse.json(upstreamJson ?? {}, { status: upstreamResponse.status }), upstreamRequestId);
    }

    if (upstreamResponse.status === 502) {
      return withRequestId(
        NextResponse.json({ error: "Workspace service unavailable", requestId: upstreamRequestId }, { status: 502 }),
        upstreamRequestId,
      );
    }
    if (upstreamResponse.status === 504) {
      return withRequestId(
        NextResponse.json({ error: "Workspace service timed out", requestId: upstreamRequestId }, { status: 504 }),
        upstreamRequestId,
      );
    }

    const errorBody: Record<string, unknown> = upstreamJson ?? {
      error: "Workspace service error",
      requestId: upstreamRequestId,
    };
    if (!("requestId" in errorBody) && !("request_id" in errorBody)) {
      errorBody.requestId = upstreamRequestId;
    }
    return withRequestId(NextResponse.json(errorBody, { status: upstreamResponse.status }), upstreamRequestId);
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return withRequestId(
        NextResponse.json({ error: "Workspace service timed out", requestId }, { status: 504 }),
        requestId,
      );
    }
    const message = error instanceof Error ? error.message : "Unknown error";
    console.error("api/system/health proxy failed", { request_id: requestId, message });
    return withRequestId(
      NextResponse.json({ error: "Workspace service unavailable", requestId }, { status: 502 }),
      requestId,
    );
  } finally {
    clearTimeout(timeout);
  }
}
