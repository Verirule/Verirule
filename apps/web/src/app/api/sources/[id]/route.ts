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
  console.error("api/sources/[id] proxy failed", { message });
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

function parseConfig(value: unknown): Record<string, unknown> | null {
  if (typeof value === "object" && value !== null && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

export async function PATCH(
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
  const sourceId = id?.trim() ?? "";
  if (!sourceId) {
    return NextResponse.json({ message: "Invalid source id" }, { status: 400 });
  }

  const payload = (await request.json().catch(() => null)) as {
    name?: unknown;
    url?: unknown;
    kind?: unknown;
    config?: unknown;
    title?: unknown;
    is_enabled?: unknown;
  } | null;

  const name = typeof payload?.name === "string" ? payload.name.trim() : null;
  const url = typeof payload?.url === "string" ? payload.url.trim() : null;
  const title = typeof payload?.title === "string" ? payload.title.trim() : null;
  const kind = payload?.kind === undefined ? null : parseKind(payload.kind);
  const config = payload?.config === undefined ? null : parseConfig(payload.config);
  const isEnabled = typeof payload?.is_enabled === "boolean" ? payload.is_enabled : null;

  if (payload?.kind !== undefined && !kind) {
    return NextResponse.json({ message: "Invalid source kind" }, { status: 400 });
  }
  if (payload?.config !== undefined && config === null) {
    return NextResponse.json({ message: "Invalid source config" }, { status: 400 });
  }
  if (!name && !url && !title && !kind && !config && isEnabled === null) {
    return NextResponse.json({ message: "No source fields to update" }, { status: 400 });
  }

  if (kind === "github_releases") {
    const repo = config?.repo;
    if (typeof repo !== "string" || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo)) {
      return NextResponse.json({ message: "GitHub repo must use owner/name format" }, { status: 400 });
    }
  }

  try {
    const upstreamResponse = await fetch(
      `${apiBaseUrl}/api/v1/sources/${encodeURIComponent(sourceId)}`,
      {
        method: "PATCH",
        headers: upstreamHeaders(accessToken),
        body: JSON.stringify({
          name,
          url,
          title,
          kind,
          config,
          is_enabled: isEnabled,
        }),
        cache: "no-store",
      },
    );

    if (!upstreamResponse.ok) {
      console.error("api/sources/[id] proxy failed", {
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
