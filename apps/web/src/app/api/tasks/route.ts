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
  console.error("api/tasks proxy failed", { message });
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
    const upstreamResponse = await fetch(`${apiBaseUrl}/api/v1/tasks?org_id=${encodeURIComponent(orgId)}`, {
      method: "GET",
      headers: upstreamHeaders(accessToken),
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      console.error("api/tasks proxy failed", {
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
    title?: unknown;
    alert_id?: unknown;
    finding_id?: unknown;
    due_at?: unknown;
  } | null;

  const orgId = typeof payload?.org_id === "string" ? payload.org_id.trim() : "";
  const title = typeof payload?.title === "string" ? payload.title.trim() : "";
  const alertId = typeof payload?.alert_id === "string" ? payload.alert_id.trim() : null;
  const findingId = typeof payload?.finding_id === "string" ? payload.finding_id.trim() : null;
  const dueAt = typeof payload?.due_at === "string" ? payload.due_at.trim() : null;

  if (!orgId || !title) {
    return NextResponse.json({ message: "Invalid task payload" }, { status: 400 });
  }

  try {
    const upstreamResponse = await fetch(`${apiBaseUrl}/api/v1/tasks`, {
      method: "POST",
      headers: upstreamHeaders(accessToken),
      body: JSON.stringify({
        org_id: orgId,
        title,
        alert_id: alertId,
        finding_id: findingId,
        due_at: dueAt,
      }),
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      console.error("api/tasks proxy failed", {
        message: `upstream status ${upstreamResponse.status}`,
      });
      const body = (await upstreamResponse.json().catch(() => ({}))) as { detail?: unknown };
      const detail = typeof body.detail === "string" ? body.detail : "Upstream API error";
      return NextResponse.json({ message: detail }, { status: upstreamResponse.status });
    }

    const body = (await upstreamResponse.json().catch(() => ({}))) as unknown;
    return NextResponse.json(body, { status: 200 });
  } catch (error: unknown) {
    logProxyError(error);
    return NextResponse.json({ message: "Upstream API error" }, { status: 502 });
  }
}
