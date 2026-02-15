import { createClient } from "@/lib/supabase/server";
import { randomUUID } from "crypto";
import { NextRequest, NextResponse } from "next/server";

const FAST_API_TIMEOUT_MS = 10_000;

function getApiBaseUrl(): string | null {
  const apiBaseUrl = process.env.VERIRULE_API_URL?.trim()?.replace(/\/$/, "");
  return apiBaseUrl || null;
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

function apiError(status: number, message: string, requestId: string): NextResponse {
  return withRequestId(NextResponse.json({ message, request_id: requestId }, { status }), requestId);
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

async function getAccessToken(): Promise<string | null> {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getSession();
  if (error || !data.session?.access_token) {
    return null;
  }
  return data.session.access_token;
}

async function proxyToApi(
  request: NextRequest,
  orgId: string,
  method: "GET" | "PUT",
): Promise<NextResponse> {
  const requestId = requestIdFromHeaders(request.headers);
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return apiError(501, "API not configured", requestId);
  }

  const accessToken = await getAccessToken();
  if (!accessToken) {
    return apiError(401, "Unauthorized", requestId);
  }

  const cleanedOrgId = orgId.trim();
  if (!cleanedOrgId) {
    return apiError(400, "orgId is required", requestId);
  }

  const payload =
    method === "PUT" ? ((await request.json().catch(() => null)) as Record<string, unknown> | null) : null;
  if (method === "PUT" && (!payload || typeof payload !== "object")) {
    return apiError(400, "Invalid payload", requestId);
  }

  try {
    const upstream = await fetchWithTimeout(
      `${apiBaseUrl}/api/v1/orgs/${encodeURIComponent(cleanedOrgId)}/sla`,
      {
        method,
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
          "X-Request-ID": requestId,
        },
        body: payload ? JSON.stringify(payload) : undefined,
        cache: "no-store",
      },
      FAST_API_TIMEOUT_MS,
    );

    const upstreamRequestId = upstream.headers.get("x-request-id")?.trim() || requestId;
    const bodyText = await upstream.text();
    const body = parseJsonObject(bodyText) ?? {};
    if (!("request_id" in body)) {
      body.request_id = upstreamRequestId;
    }

    return withRequestId(NextResponse.json(body, { status: upstream.status }), upstreamRequestId);
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return apiError(504, "Upstream API timed out", requestId);
    }
    console.error("sla rules proxy failed", { request_id: requestId });
    return apiError(502, "Upstream API error", requestId);
  }
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ orgId: string }> },
) {
  const { orgId } = await context.params;
  return proxyToApi(request, orgId, "GET");
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ orgId: string }> },
) {
  const { orgId } = await context.params;
  return proxyToApi(request, orgId, "PUT");
}
