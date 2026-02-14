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

export async function DELETE(
  _request: NextRequest,
  context: { params: Promise<{ orgId: string; inviteId: string }> },
) {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return proxyError("API not configured", 501);
  }

  const accessToken = await getAccessToken();
  if (!accessToken) {
    return proxyError("Unauthorized", 401);
  }

  const { orgId, inviteId } = await context.params;
  const cleanedOrgId = orgId?.trim() ?? "";
  const cleanedInviteId = inviteId?.trim() ?? "";
  if (!cleanedOrgId || !cleanedInviteId) {
    return proxyError("Invalid route params", 400);
  }

  try {
    const upstreamResponse = await fetch(
      `${apiBaseUrl}/api/v1/orgs/${encodeURIComponent(cleanedOrgId)}/invites/${encodeURIComponent(cleanedInviteId)}`,
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
