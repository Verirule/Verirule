import { createClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";

function getApiBaseUrl(): string | null {
  const apiBaseUrl = process.env.VERIRULE_API_URL?.replace(/\/$/, "");
  return apiBaseUrl || null;
}

async function getAccessToken(): Promise<string | null> {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getSession();

  if (error || !data.session?.access_token) {
    return null;
  }

  return data.session.access_token;
}

function upstreamHeaders(accessToken: string): HeadersInit {
  return {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  };
}

function proxyError(message: string, status = 502) {
  return NextResponse.json({ message }, { status });
}

async function upstreamErrorResponse(upstreamResponse: Response) {
  if (upstreamResponse.status === 502) {
    return proxyError("Upstream API error", 502);
  }

  const body = (await upstreamResponse.json().catch(() => ({}))) as { detail?: unknown };
  const detail = typeof body.detail === "string" ? body.detail : "Request failed";
  return NextResponse.json({ message: detail }, { status: upstreamResponse.status });
}

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ orgId: string }> },
) {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return proxyError("API not configured", 501);
  }

  const accessToken = await getAccessToken();
  if (!accessToken) {
    return proxyError("Unauthorized", 401);
  }

  const { orgId } = await context.params;
  const cleanedOrgId = orgId?.trim() ?? "";
  if (!cleanedOrgId) {
    return proxyError("orgId is required", 400);
  }

  try {
    const upstreamResponse = await fetch(
      `${apiBaseUrl}/api/v1/orgs/${encodeURIComponent(cleanedOrgId)}/automation/alert-task-rules`,
      {
        method: "GET",
        headers: upstreamHeaders(accessToken),
        cache: "no-store",
      },
    );

    if (!upstreamResponse.ok) {
      return upstreamErrorResponse(upstreamResponse);
    }

    const body = (await upstreamResponse.json().catch(() => ({}))) as unknown;
    return NextResponse.json(body, { status: 200 });
  } catch {
    return proxyError("Upstream API error", 502);
  }
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ orgId: string }> },
) {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return proxyError("API not configured", 501);
  }

  const accessToken = await getAccessToken();
  if (!accessToken) {
    return proxyError("Unauthorized", 401);
  }

  const { orgId } = await context.params;
  const cleanedOrgId = orgId?.trim() ?? "";
  if (!cleanedOrgId) {
    return proxyError("orgId is required", 400);
  }

  const payload = (await request.json().catch(() => null)) as Record<string, unknown> | null;
  if (!payload || typeof payload !== "object") {
    return proxyError("Invalid payload", 400);
  }

  try {
    const upstreamResponse = await fetch(
      `${apiBaseUrl}/api/v1/orgs/${encodeURIComponent(cleanedOrgId)}/automation/alert-task-rules`,
      {
        method: "PUT",
        headers: upstreamHeaders(accessToken),
        body: JSON.stringify(payload),
        cache: "no-store",
      },
    );

    if (!upstreamResponse.ok) {
      return upstreamErrorResponse(upstreamResponse);
    }

    const body = (await upstreamResponse.json().catch(() => ({}))) as unknown;
    return NextResponse.json(body, { status: 200 });
  } catch {
    return proxyError("Upstream API error", 502);
  }
}
