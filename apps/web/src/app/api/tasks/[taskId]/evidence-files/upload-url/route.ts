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

async function upstreamErrorResponse(upstreamResponse: Response) {
  if (upstreamResponse.status === 502) {
    return NextResponse.json({ message: "Upstream API error" }, { status: 502 });
  }
  const body = (await upstreamResponse.json().catch(() => ({}))) as { detail?: unknown };
  const detail = typeof body.detail === "string" ? body.detail : "Request failed";
  return NextResponse.json({ message: detail }, { status: upstreamResponse.status });
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ taskId: string }> },
) {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return NextResponse.json({ message: "API not configured" }, { status: 501 });
  }

  const accessToken = await getAccessToken();
  if (!accessToken) {
    return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
  }

  const { taskId } = await context.params;
  const trimmedTaskId = taskId?.trim() ?? "";
  if (!trimmedTaskId) {
    return NextResponse.json({ message: "Invalid task id" }, { status: 400 });
  }

  const payload = (await request.json().catch(() => null)) as
    | {
        org_id?: unknown;
        filename?: unknown;
        content_type?: unknown;
        byte_size?: unknown;
      }
    | null;
  const orgId = typeof payload?.org_id === "string" ? payload.org_id.trim() : "";
  const filename = typeof payload?.filename === "string" ? payload.filename.trim() : "";
  const contentType = typeof payload?.content_type === "string" ? payload.content_type.trim() : null;
  const byteSize = typeof payload?.byte_size === "number" ? payload.byte_size : null;
  if (!orgId || !filename || !byteSize || byteSize <= 0) {
    return NextResponse.json({ message: "Invalid upload payload" }, { status: 400 });
  }

  try {
    const upstreamResponse = await fetch(
      `${apiBaseUrl}/api/v1/tasks/${encodeURIComponent(trimmedTaskId)}/evidence-files/upload-url`,
      {
        method: "POST",
        headers: upstreamHeaders(accessToken),
        body: JSON.stringify({
          org_id: orgId,
          filename,
          content_type: contentType,
          byte_size: byteSize,
        }),
        cache: "no-store",
      },
    );

    if (!upstreamResponse.ok) {
      console.error("api/tasks/[taskId]/evidence-files/upload-url proxy failed", {
        message: `upstream status ${upstreamResponse.status}`,
      });
      return upstreamErrorResponse(upstreamResponse);
    }

    const body = (await upstreamResponse.json().catch(() => ({}))) as unknown;
    return NextResponse.json(body, { status: 200 });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : undefined;
    console.error("api/tasks/[taskId]/evidence-files/upload-url proxy failed", { message });
    return NextResponse.json({ message: "Upstream API error" }, { status: 502 });
  }
}
