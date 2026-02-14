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

type AcceptPayload = {
  token?: unknown;
};

export async function POST(request: NextRequest) {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return proxyError("API not configured", 501);
  }

  const accessToken = await getAccessToken();
  if (!accessToken) {
    return proxyError("Unauthorized", 401);
  }

  const payload = (await request.json().catch(() => null)) as AcceptPayload | null;
  const token = typeof payload?.token === "string" ? payload.token.trim() : "";
  if (!token) {
    return proxyError("token is required", 400);
  }

  try {
    const upstreamResponse = await fetch(`${apiBaseUrl}/api/v1/invites/accept`, {
      method: "POST",
      headers: upstreamHeaders(accessToken),
      body: JSON.stringify({ token }),
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      return mapUpstreamError(upstreamResponse);
    }

    const body = (await upstreamResponse.json().catch(() => ({}))) as unknown;
    return NextResponse.json(body, { status: 200 });
  } catch {
    return proxyError("Upstream API error", 502);
  }
}
