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

async function mapUpstreamError(upstreamResponse: Response) {
  if (upstreamResponse.status >= 500) {
    return proxyError("Upstream API error", 502);
  }

  const body = (await upstreamResponse.json().catch(() => ({}))) as {
    detail?: unknown;
    message?: unknown;
  };
  const detail =
    typeof body.detail === "string"
      ? body.detail
      : typeof body.message === "string"
        ? body.message
        : "Request failed";
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
    return proxyError("Invalid org id", 400);
  }

  try {
    const upstreamResponse = await fetch(
      `${apiBaseUrl}/api/v1/orgs/${encodeURIComponent(cleanedOrgId)}/invites`,
      {
        method: "GET",
        headers: upstreamHeaders(accessToken),
        cache: "no-store",
      },
    );

    if (!upstreamResponse.ok) {
      return mapUpstreamError(upstreamResponse);
    }

    const body = (await upstreamResponse.json().catch(() => ({}))) as unknown;
    return NextResponse.json(body, { status: 200 });
  } catch {
    return proxyError("Upstream API error", 502);
  }
}

type InvitePayload = {
  email?: unknown;
  role?: unknown;
  expires_hours?: unknown;
};

export async function POST(
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
    return proxyError("Invalid org id", 400);
  }

  const payload = (await request.json().catch(() => null)) as InvitePayload | null;
  const email = typeof payload?.email === "string" ? payload.email.trim() : "";
  const role = typeof payload?.role === "string" ? payload.role.trim().toLowerCase() : "member";
  const expiresHours =
    typeof payload?.expires_hours === "number" && Number.isFinite(payload.expires_hours)
      ? Math.trunc(payload.expires_hours)
      : 72;

  if (!email) {
    return proxyError("email is required", 400);
  }

  if (!["admin", "member", "viewer"].includes(role)) {
    return proxyError("Invalid invite role", 400);
  }

  try {
    const upstreamResponse = await fetch(
      `${apiBaseUrl}/api/v1/orgs/${encodeURIComponent(cleanedOrgId)}/invites`,
      {
        method: "POST",
        headers: upstreamHeaders(accessToken),
        body: JSON.stringify({ email, role, expires_hours: expiresHours }),
        cache: "no-store",
      },
    );

    if (!upstreamResponse.ok) {
      return mapUpstreamError(upstreamResponse);
    }

    const body = (await upstreamResponse.json().catch(() => ({}))) as unknown;
    return NextResponse.json(body, { status: 200 });
  } catch {
    return proxyError("Upstream API error", 502);
  }
}
