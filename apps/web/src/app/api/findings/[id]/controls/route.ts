import { createClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";

type ControlConfidence = "low" | "medium" | "high";

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
  console.error("api/findings/[id]/controls proxy failed", { message });
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

function parseConfidence(value: unknown): ControlConfidence | null {
  if (value === "low" || value === "medium" || value === "high") {
    return value;
  }
  return null;
}

export async function GET(
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
  const findingId = id?.trim() ?? "";
  if (!findingId) {
    return NextResponse.json({ message: "Invalid finding id" }, { status: 400 });
  }

  const orgId = request.nextUrl.searchParams.get("org_id")?.trim() ?? "";
  if (!orgId) {
    return NextResponse.json({ message: "org_id is required" }, { status: 400 });
  }

  try {
    const upstreamResponse = await fetch(
      `${apiBaseUrl}/api/v1/findings/${encodeURIComponent(findingId)}/controls?org_id=${encodeURIComponent(orgId)}`,
      {
        method: "GET",
        headers: upstreamHeaders(accessToken),
        cache: "no-store",
      },
    );

    if (!upstreamResponse.ok) {
      console.error("api/findings/[id]/controls proxy failed", {
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
  const findingId = id?.trim() ?? "";
  if (!findingId) {
    return NextResponse.json({ message: "Invalid finding id" }, { status: 400 });
  }

  const payload = (await request.json().catch(() => null)) as {
    org_id?: unknown;
    control_id?: unknown;
    confidence?: unknown;
  } | null;
  const orgId = typeof payload?.org_id === "string" ? payload.org_id.trim() : "";
  const controlId = typeof payload?.control_id === "string" ? payload.control_id.trim() : "";
  const confidence = parseConfidence(payload?.confidence ?? "medium");

  if (!orgId || !controlId || !confidence) {
    return NextResponse.json({ message: "Invalid finding control payload" }, { status: 400 });
  }

  try {
    const upstreamResponse = await fetch(
      `${apiBaseUrl}/api/v1/findings/${encodeURIComponent(findingId)}/controls`,
      {
        method: "POST",
        headers: upstreamHeaders(accessToken),
        body: JSON.stringify({
          org_id: orgId,
          control_id: controlId,
          confidence,
        }),
        cache: "no-store",
      },
    );

    if (!upstreamResponse.ok) {
      console.error("api/findings/[id]/controls proxy failed", {
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

