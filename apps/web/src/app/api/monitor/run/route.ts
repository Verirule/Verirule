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

function logProxyError(error: unknown): void {
  const message = error instanceof Error ? error.message : undefined;
  console.error("api/monitor/run proxy failed", { message });
}

export async function POST(request: NextRequest) {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return NextResponse.json({ message: "API not configured" }, { status: 501 });
  }

  const accessToken = await getAccessToken();
  if (!accessToken) {
    return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
  }

  const payload = (await request.json().catch(() => null)) as {
    org_id?: unknown;
    source_id?: unknown;
  } | null;
  const orgId = typeof payload?.org_id === "string" ? payload.org_id.trim() : "";
  const sourceId = typeof payload?.source_id === "string" ? payload.source_id.trim() : "";

  if (!orgId || !sourceId) {
    return NextResponse.json({ message: "Invalid monitor run payload" }, { status: 400 });
  }

  try {
    const upstreamResponse = await fetch(`${apiBaseUrl}/api/v1/monitor/run`, {
      method: "POST",
      headers: upstreamHeaders(accessToken),
      body: JSON.stringify({ org_id: orgId, source_id: sourceId }),
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      console.error("api/monitor/run proxy failed", {
        message: `upstream status ${upstreamResponse.status}`,
      });
      return NextResponse.json({ message: "Upstream API error" }, { status: 502 });
    }

    const body = (await upstreamResponse.json().catch(() => ({}))) as unknown;
    return NextResponse.json(body, { status: 200 });
  } catch (error: unknown) {
    logProxyError(error);
    return NextResponse.json({ message: "Upstream API error" }, { status: 502 });
  }
}
