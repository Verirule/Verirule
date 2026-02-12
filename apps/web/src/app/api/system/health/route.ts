import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

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

function logProxyError(error: unknown): void {
  const message = error instanceof Error ? error.message : undefined;
  console.error("api/system/health proxy failed", { message });
}

async function upstreamErrorResponse(upstreamResponse: Response) {
  if (upstreamResponse.status === 502) {
    return NextResponse.json({ message: "Upstream API error" }, { status: 502 });
  }

  const body = (await upstreamResponse.json().catch(() => ({}))) as { detail?: unknown };
  const detail = typeof body.detail === "string" ? body.detail : "Request failed";
  return NextResponse.json({ message: detail }, { status: upstreamResponse.status });
}

export async function GET() {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return NextResponse.json({ message: "API not configured" }, { status: 501 });
  }

  const accessToken = await getAccessToken();
  if (!accessToken) {
    return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
  }

  try {
    const upstreamResponse = await fetch(`${apiBaseUrl}/api/v1/system/health`, {
      method: "GET",
      headers: upstreamHeaders(accessToken),
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      console.error("api/system/health proxy failed", {
        message: `upstream status ${upstreamResponse.status}`,
      });
      return upstreamErrorResponse(upstreamResponse);
    }

    const body = (await upstreamResponse.json().catch(() => ({}))) as unknown;
    return NextResponse.json(body, { status: 200 });
  } catch (error: unknown) {
    logProxyError(error);
    return NextResponse.json({ message: "Upstream API error" }, { status: 502 });
  }
}
