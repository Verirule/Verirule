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
  console.error("api/exports proxy failed", { message });
}

async function upstreamErrorResponse(upstreamResponse: Response) {
  if (upstreamResponse.status === 502) {
    return NextResponse.json({ message: "Upstream API error" }, { status: 502 });
  }

  const body = (await upstreamResponse.json().catch(() => ({}))) as { detail?: unknown };
  const detail = typeof body.detail === "string" ? body.detail : "Request failed";
  return NextResponse.json({ message: detail }, { status: upstreamResponse.status });
}

export async function GET(request: NextRequest) {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return NextResponse.json({ message: "API not configured" }, { status: 501 });
  }

  const accessToken = await getAccessToken();
  if (!accessToken) {
    return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
  }

  const orgId = request.nextUrl.searchParams.get("org_id")?.trim() ?? "";
  if (!orgId) {
    return NextResponse.json({ message: "org_id is required" }, { status: 400 });
  }

  try {
    const upstreamResponse = await fetch(`${apiBaseUrl}/api/v1/exports?org_id=${encodeURIComponent(orgId)}`, {
      method: "GET",
      headers: upstreamHeaders(accessToken),
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      console.error("api/exports proxy failed", {
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
    format?: unknown;
    from?: unknown;
    to?: unknown;
    include?: unknown;
  } | null;

  const orgId = typeof payload?.org_id === "string" ? payload.org_id.trim() : "";
  const format = typeof payload?.format === "string" ? payload.format.trim().toLowerCase() : "";
  const from = typeof payload?.from === "string" ? payload.from.trim() : null;
  const to = typeof payload?.to === "string" ? payload.to.trim() : null;
  const include = Array.isArray(payload?.include)
    ? payload?.include.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : null;

  if (!orgId || (format !== "pdf" && format !== "csv" && format !== "zip")) {
    return NextResponse.json({ message: "Invalid export payload" }, { status: 400 });
  }

  try {
    const upstreamResponse = await fetch(`${apiBaseUrl}/api/v1/exports`, {
      method: "POST",
      headers: upstreamHeaders(accessToken),
      body: JSON.stringify({
        org_id: orgId,
        format,
        from,
        to,
        include,
      }),
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      console.error("api/exports proxy failed", {
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
