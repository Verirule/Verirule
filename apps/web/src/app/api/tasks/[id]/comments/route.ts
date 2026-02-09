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
  console.error("api/tasks/[id]/comments proxy failed", { message });
}

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return NextResponse.json({ message: "API not configured" }, { status: 501 });
  }

  const accessToken = await getAccessToken();
  if (!accessToken) {
    return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
  }

  const { id } = await context.params;
  const taskId = id?.trim() ?? "";
  if (!taskId) {
    return NextResponse.json({ message: "Invalid task id" }, { status: 400 });
  }

  try {
    const upstreamResponse = await fetch(
      `${apiBaseUrl}/api/v1/tasks/${encodeURIComponent(taskId)}/comments`,
      {
        method: "GET",
        headers: upstreamHeaders(accessToken),
        cache: "no-store",
      },
    );

    if (!upstreamResponse.ok) {
      console.error("api/tasks/[id]/comments proxy failed", {
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

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return NextResponse.json({ message: "API not configured" }, { status: 501 });
  }

  const accessToken = await getAccessToken();
  if (!accessToken) {
    return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
  }

  const { id } = await context.params;
  const taskId = id?.trim() ?? "";
  if (!taskId) {
    return NextResponse.json({ message: "Invalid task id" }, { status: 400 });
  }

  const payload = (await request.json().catch(() => null)) as { body?: unknown } | null;
  const bodyText = typeof payload?.body === "string" ? payload.body.trim() : "";
  if (!bodyText) {
    return NextResponse.json({ message: "Invalid comment payload" }, { status: 400 });
  }

  try {
    const upstreamResponse = await fetch(
      `${apiBaseUrl}/api/v1/tasks/${encodeURIComponent(taskId)}/comments`,
      {
        method: "POST",
        headers: upstreamHeaders(accessToken),
        body: JSON.stringify({ body: bodyText }),
        cache: "no-store",
      },
    );

    if (!upstreamResponse.ok) {
      console.error("api/tasks/[id]/comments proxy failed", {
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
