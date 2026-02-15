import { createClient } from "@/lib/supabase/server";
import { randomUUID } from "crypto";
import { NextRequest, NextResponse } from "next/server";

type SessionContext = {
  accessToken: string;
};

type ForwardedClientHeaders = {
  forwardedFor: string | null;
  realIp: string | null;
};

const ORGS_GET_TIMEOUT_MS = 8_000;
const ORGS_POST_TIMEOUT_MS = 12_000;

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

function apiError(
  status: number,
  message: string,
  code: string,
  requestId: string,
  extra?: Record<string, unknown>,
): NextResponse {
  return withRequestId(
    NextResponse.json({ message, code, request_id: requestId, ...(extra ?? {}) }, { status }),
    requestId,
  );
}

async function getSessionContext(
  requestId: string,
): Promise<{ context: SessionContext; response: null } | { context: null; response: NextResponse }> {
  let supabase: Awaited<ReturnType<typeof createClient>>;
  try {
    supabase = await createClient();
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Supabase env not configured";
    const missing = message.match(/\b(?:NEXT_PUBLIC_[A-Z0-9_]+|SUPABASE_[A-Z0-9_]+|VERIRULE_[A-Z0-9_]+)\b/g) ?? [];
    return {
      context: null,
      response: apiError(500, "Missing required environment variables", "env_missing", requestId, {
        missing: Array.from(new Set(missing)),
      }),
    };
  }

  const { data, error } = await supabase.auth.getSession();
  if (error || !data.session?.access_token) {
    return {
      context: null,
      response: apiError(401, "Sign in again", "unauthorized", requestId),
    };
  }

  return {
    context: { accessToken: data.session.access_token },
    response: null,
  };
}

async function proxyOrgsRequest(
  method: "GET" | "POST",
  accessToken: string,
  requestId: string,
  clientHeaders: ForwardedClientHeaders,
  payload?: Record<string, unknown>,
): Promise<NextResponse> {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return apiError(501, "API not configured", "api_not_configured", requestId);
  }

  const endpointPath = method === "GET" ? "/api/v1/orgs/mine" : "/api/v1/orgs";
  const timeoutMs = method === "POST" ? ORGS_POST_TIMEOUT_MS : ORGS_GET_TIMEOUT_MS;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const upstream = await fetch(`${apiBaseUrl}${endpointPath}`, {
      method,
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
        "X-Request-ID": requestId,
        ...(clientHeaders.forwardedFor ? { "X-Forwarded-For": clientHeaders.forwardedFor } : {}),
        ...(clientHeaders.realIp ? { "X-Real-IP": clientHeaders.realIp } : {}),
      },
      body: payload ? JSON.stringify(payload) : undefined,
      cache: "no-store",
      signal: controller.signal,
    });

    const upstreamRequestId = upstream.headers.get("x-request-id")?.trim() || requestId;
    const upstreamBodyText = await upstream.text();
    const upstreamJson = parseJsonObject(upstreamBodyText);

    if (upstream.ok) {
      return withRequestId(NextResponse.json(upstreamJson ?? {}, { status: upstream.status }), upstreamRequestId);
    }

    const safeErrorBody: Record<string, unknown> =
      upstreamJson ?? { error: "Workspace service error", requestId: upstreamRequestId };
    if (!("requestId" in safeErrorBody) && !("request_id" in safeErrorBody)) {
      safeErrorBody.requestId = upstreamRequestId;
    }
    return withRequestId(NextResponse.json(safeErrorBody, { status: upstream.status }), upstreamRequestId);
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return withRequestId(
        NextResponse.json({ error: "Workspace service timed out", requestId }, { status: 504 }),
        requestId,
      );
    }

    const message = error instanceof Error ? error.message : "Unknown error";
    console.error("api/orgs upstream failed", { request_id: requestId, message });
    return withRequestId(
      NextResponse.json({ error: "Workspace service unavailable", requestId }, { status: 502 }),
      requestId,
    );
  } finally {
    clearTimeout(timeout);
  }
}

export async function GET(request: NextRequest) {
  const requestId = requestIdFromHeaders(request.headers);
  const clientHeaders: ForwardedClientHeaders = {
    forwardedFor:
      request.headers.get("x-forwarded-for")?.trim() ||
      request.headers.get("x-vercel-forwarded-for")?.trim() ||
      null,
    realIp: request.headers.get("x-real-ip")?.trim() || null,
  };

  const { context, response } = await getSessionContext(requestId);
  if (response) {
    return response;
  }

  return proxyOrgsRequest("GET", context.accessToken, requestId, clientHeaders);
}

export async function POST(request: NextRequest) {
  const requestId = requestIdFromHeaders(request.headers);
  const clientHeaders: ForwardedClientHeaders = {
    forwardedFor:
      request.headers.get("x-forwarded-for")?.trim() ||
      request.headers.get("x-vercel-forwarded-for")?.trim() ||
      null,
    realIp: request.headers.get("x-real-ip")?.trim() || null,
  };

  const payload = (await request.json().catch(() => null)) as { name?: unknown } | null;
  const name = typeof payload?.name === "string" ? payload.name : "";
  if (!name.trim()) {
    return apiError(400, "Invalid org payload", "invalid_payload", requestId);
  }

  const { context, response } = await getSessionContext(requestId);
  if (response) {
    return response;
  }

  return proxyOrgsRequest("POST", context.accessToken, requestId, clientHeaders, {
    name: name.trim(),
  });
}
