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
      `${apiBaseUrl}/api/v1/orgs/${encodeURIComponent(cleanedOrgId)}/members`,
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

type PatchPayload = {
  user_id?: unknown;
  role?: unknown;
};

export async function PATCH(
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

  const payload = (await request.json().catch(() => null)) as PatchPayload | null;
  const userId = typeof payload?.user_id === "string" ? payload.user_id.trim() : "";
  const role = typeof payload?.role === "string" ? payload.role.trim().toLowerCase() : "";
  if (!userId || !role) {
    return proxyError("user_id and role are required", 400);
  }

  if (!["owner", "admin", "member", "viewer"].includes(role)) {
    return proxyError("Invalid member role", 400);
  }

  try {
    const upstreamResponse = await fetch(
      `${apiBaseUrl}/api/v1/orgs/${encodeURIComponent(cleanedOrgId)}/members/${encodeURIComponent(userId)}`,
      {
        method: "PATCH",
        headers: upstreamHeaders(accessToken),
        body: JSON.stringify({ role }),
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

type DeletePayload = {
  user_id?: unknown;
};

export async function DELETE(
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

  const payload = (await request.json().catch(() => null)) as DeletePayload | null;
  const userId = typeof payload?.user_id === "string" ? payload.user_id.trim() : "";
  if (!userId) {
    return proxyError("user_id is required", 400);
  }

  try {
    const upstreamResponse = await fetch(
      `${apiBaseUrl}/api/v1/orgs/${encodeURIComponent(cleanedOrgId)}/members/${encodeURIComponent(userId)}`,
      {
        method: "DELETE",
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
