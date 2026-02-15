import { createClient } from "@/lib/supabase/server";
import { randomUUID } from "crypto";
import { NextRequest, NextResponse } from "next/server";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type PostgrestLikeError = {
  code?: string | null;
  details?: string | null;
  hint?: string | null;
  message?: string | null;
};

type SessionContext = {
  accessToken: string;
  supabase: Awaited<ReturnType<typeof createClient>>;
};

type ForwardedClientHeaders = {
  forwardedFor: string | null;
  realIp: string | null;
};

const FAST_API_TIMEOUT_MS = 10_000;
const RECOVERABLE_PROXY_ERROR_HEADER = "x-verirule-recoverable-proxy-error";

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

function extractEnvVarNames(input: string): string[] {
  const matches = input.match(
    /\b(?:NEXT_PUBLIC_[A-Z0-9_]+|SUPABASE_[A-Z0-9_]+|STRIPE_[A-Z0-9_]+|VERIRULE_[A-Z0-9_]+)\b/g,
  );
  if (!matches) {
    return [];
  }
  return Array.from(new Set(matches));
}

function isRlsOrMembershipError(error: PostgrestLikeError): boolean {
  const merged = `${error.message ?? ""} ${error.details ?? ""} ${error.hint ?? ""}`.toLowerCase();
  return (
    error.code === "42501" ||
    merged.includes("row-level security") ||
    merged.includes("permission denied") ||
    merged.includes("not a member")
  );
}

function withRequestId(response: NextResponse, requestId: string): NextResponse {
  response.headers.set("X-Request-ID", requestId);
  return response;
}

function markRecoverableProxyError(response: NextResponse): NextResponse {
  response.headers.set(RECOVERABLE_PROXY_ERROR_HEADER, "1");
  return response;
}

function markSupabaseFallback(response: NextResponse): NextResponse {
  response.headers.set("X-Verirule-Orgs-Fallback", "supabase");
  return response;
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

function toOrgRecord(value: unknown): OrgRecord | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const row = value as Record<string, unknown>;
  if (
    typeof row.id !== "string" ||
    typeof row.name !== "string" ||
    typeof row.created_at !== "string"
  ) {
    return null;
  }

  return {
    id: row.id,
    name: row.name,
    created_at: row.created_at,
  };
}

function extractCreateOrgId(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }

  if (value && typeof value === "object" && !Array.isArray(value)) {
    const row = value as Record<string, unknown>;
    for (const key of ["create_org", "id", "org_id"]) {
      const candidate = row[key];
      if (typeof candidate === "string" && candidate.trim()) {
        return candidate.trim();
      }
    }
    return null;
  }

  if (Array.isArray(value) && value.length > 0) {
    return extractCreateOrgId(value[0]);
  }

  return null;
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

function logProxyFailure(label: string, error: unknown, requestId: string): void {
  const message = error instanceof Error ? error.message : "Unknown error";
  console.error(label, { request_id: requestId, message });
}

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

async function getSessionContext(
  requestId: string,
): Promise<{ context: SessionContext; response: null } | { context: null; response: NextResponse }> {
  let supabase: Awaited<ReturnType<typeof createClient>>;
  try {
    supabase = await createClient();
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Supabase env not configured";
    const missing = extractEnvVarNames(message);
    return {
      context: null,
      response: apiError(500, "Missing required environment variables", "env_missing", requestId, { missing }),
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
    context: { supabase, accessToken: data.session.access_token },
    response: null,
  };
}

async function proxyFastApiOrgsRequest(
  method: "GET" | "POST",
  accessToken: string,
  requestId: string,
  clientHeaders: ForwardedClientHeaders,
  payload?: Record<string, unknown>,
): Promise<NextResponse | null> {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return null;
  }

  const endpointPath = method === "GET" ? "/api/v1/orgs/mine" : "/api/v1/orgs";
  try {
    const upstream = await fetchWithTimeout(
      `${apiBaseUrl}${endpointPath}`,
      {
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
      },
      FAST_API_TIMEOUT_MS,
    );

    const upstreamRequestId = upstream.headers.get("x-request-id")?.trim() || requestId;
    const upstreamBodyText = await upstream.text();
    const upstreamJson = parseJsonObject(upstreamBodyText);

    if (upstream.ok) {
      const body = upstreamJson ?? {};
      return withRequestId(NextResponse.json(body, { status: upstream.status }), upstreamRequestId);
    }

    const errorPayload: Record<string, unknown> = upstreamJson ?? {
      message: "Workspace request failed.",
      code: "upstream_error",
    };
    if (!("request_id" in errorPayload)) {
      errorPayload.request_id = upstreamRequestId;
    }
    const response = withRequestId(
      NextResponse.json(errorPayload, { status: upstream.status }),
      upstreamRequestId,
    );
    if (upstream.status >= 500) {
      return markRecoverableProxyError(response);
    }
    return response;
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return markRecoverableProxyError(
        apiError(504, "Workspace request timed out", "upstream_timeout", requestId),
      );
    }
    logProxyFailure("api/orgs upstream failed", error, requestId);
    return markRecoverableProxyError(
      apiError(502, "Workspace service unavailable", "upstream_error", requestId),
    );
  }
}

function mapPostgrestFailure(error: PostgrestLikeError, fallbackMessage: string, requestId: string): NextResponse {
  if (isRlsOrMembershipError(error)) {
    return apiError(403, "No access to orgs; verify membership", "rls_denied", requestId);
  }

  const detail =
    typeof error.message === "string" && error.message.trim().length > 0
      ? error.message
      : fallbackMessage;
  return apiError(502, detail, "supabase_error", requestId);
}

async function listOrgsFromSupabase(
  supabase: Awaited<ReturnType<typeof createClient>>,
  requestId: string,
): Promise<NextResponse> {
  const { data, error } = await supabase
    .from("orgs")
    .select("id,name,created_at")
    .order("created_at", { ascending: false });

  if (error) {
    return mapPostgrestFailure(error, "Failed to fetch organizations", requestId);
  }

  const orgs = Array.isArray(data)
    ? data.map((row) => toOrgRecord(row)).filter((row): row is OrgRecord => row !== null)
    : [];

  return withRequestId(NextResponse.json({ orgs }, { status: 200 }), requestId);
}

async function createOrgInSupabase(
  supabase: Awaited<ReturnType<typeof createClient>>,
  name: string,
  requestId: string,
): Promise<NextResponse> {
  const normalizedName = name.trim();
  if (normalizedName.length < 2 || normalizedName.length > 64) {
    return apiError(400, "Workspace name must be between 2 and 64 characters", "invalid_payload", requestId);
  }

  const { data, error } = await supabase.rpc("create_org", { p_name: normalizedName });
  if (error) {
    return mapPostgrestFailure(error, "Failed to create organization", requestId);
  }

  const orgId = extractCreateOrgId(data);
  if (!orgId) {
    return apiError(502, "Invalid create organization response", "supabase_error", requestId);
  }

  const { data: orgRow } = await supabase
    .from("orgs")
    .select("id,name,created_at")
    .eq("id", orgId)
    .maybeSingle();

  const created = toOrgRecord(orgRow);
  return withRequestId(NextResponse.json({ id: orgId, org: created }, { status: 200 }), requestId);
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

  const fastApiResponse = await proxyFastApiOrgsRequest("GET", context.accessToken, requestId, clientHeaders);
  if (fastApiResponse) {
    const recoverableProxyError =
      fastApiResponse.headers.get(RECOVERABLE_PROXY_ERROR_HEADER) === "1";
    if (!recoverableProxyError) {
      return fastApiResponse;
    }
    return markSupabaseFallback(await listOrgsFromSupabase(context.supabase, requestId));
  }

  return listOrgsFromSupabase(context.supabase, requestId);
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

  const fastApiResponse = await proxyFastApiOrgsRequest(
    "POST",
    context.accessToken,
    requestId,
    clientHeaders,
    { name: name.trim() },
  );
  if (fastApiResponse) {
    const recoverableProxyError =
      fastApiResponse.headers.get(RECOVERABLE_PROXY_ERROR_HEADER) === "1";
    if (!recoverableProxyError) {
      return fastApiResponse;
    }
    return markSupabaseFallback(await createOrgInSupabase(context.supabase, name, requestId));
  }

  return createOrgInSupabase(context.supabase, name, requestId);
}
