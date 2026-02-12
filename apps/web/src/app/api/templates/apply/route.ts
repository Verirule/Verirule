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
  console.error("api/templates/apply proxy failed", { message });
}

async function mapUpstreamError(upstreamResponse: Response) {
  if (upstreamResponse.status >= 500) {
    return NextResponse.json({ message: "Upstream API error" }, { status: 502 });
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
    template_slug?: unknown;
    overrides?: unknown;
  } | null;

  const orgId = typeof payload?.org_id === "string" ? payload.org_id.trim() : "";
  const templateSlug =
    typeof payload?.template_slug === "string" ? payload.template_slug.trim().toLowerCase() : "";

  if (!orgId || !templateSlug) {
    return NextResponse.json({ message: "Invalid template apply payload" }, { status: 400 });
  }

  const overrides =
    typeof payload?.overrides === "object" && payload.overrides !== null && !Array.isArray(payload.overrides)
      ? payload.overrides
      : undefined;

  try {
    const upstreamResponse = await fetch(`${apiBaseUrl}/api/v1/templates/apply`, {
      method: "POST",
      headers: upstreamHeaders(accessToken),
      body: JSON.stringify({ org_id: orgId, template_slug: templateSlug, overrides }),
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      console.error("api/templates/apply proxy failed", {
        message: `upstream status ${upstreamResponse.status}`,
      });
      return mapUpstreamError(upstreamResponse);
    }

    const body = (await upstreamResponse.json().catch(() => ({}))) as unknown;
    return NextResponse.json(body, { status: 200 });
  } catch (error: unknown) {
    logProxyError(error);
    return NextResponse.json({ message: "Upstream API error" }, { status: 502 });
  }
}
