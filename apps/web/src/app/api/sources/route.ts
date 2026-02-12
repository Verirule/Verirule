import { createClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";

type SourceKind = "html" | "rss" | "pdf" | "github_releases";

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
  console.error("api/sources proxy failed", { message });
}

function parseKind(value: unknown): SourceKind | null {
  if (
    value === "html" ||
    value === "rss" ||
    value === "pdf" ||
    value === "github_releases"
  ) {
    return value;
  }
  return null;
}

function parseConfig(value: unknown): Record<string, unknown> {
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
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
    const upstreamResponse = await fetch(
      `${apiBaseUrl}/api/v1/sources?org_id=${encodeURIComponent(orgId)}`,
      {
        method: "GET",
        headers: upstreamHeaders(accessToken),
        cache: "no-store",
      },
    );

    if (!upstreamResponse.ok) {
      console.error("api/sources proxy failed", {
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
    name?: unknown;
    kind?: unknown;
    config?: unknown;
    title?: unknown;
    url?: unknown;
  } | null;

  const orgId = typeof payload?.org_id === "string" ? payload.org_id.trim() : "";
  const name = typeof payload?.name === "string" ? payload.name.trim() : "";
  const kind = parseKind(payload?.kind);
  const url = typeof payload?.url === "string" ? payload.url.trim() : "";
  const config = parseConfig(payload?.config);
  const title = typeof payload?.title === "string" ? payload.title.trim() : null;

  if (!orgId || !name || !kind || !url) {
    return NextResponse.json({ message: "Invalid source payload" }, { status: 400 });
  }

  if (kind === "github_releases") {
    const repo = config.repo;
    if (typeof repo !== "string" || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo)) {
      return NextResponse.json({ message: "GitHub repo must use owner/name format" }, { status: 400 });
    }
  }

  try {
    const upstreamResponse = await fetch(`${apiBaseUrl}/api/v1/sources`, {
      method: "POST",
      headers: upstreamHeaders(accessToken),
      body: JSON.stringify({ org_id: orgId, name, kind, url, config, title }),
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      console.error("api/sources proxy failed", {
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
