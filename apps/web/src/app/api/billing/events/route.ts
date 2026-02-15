import { createClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";

function getApiBaseUrl(): string | null {
  const raw = process.env.VERIRULE_API_URL?.trim();
  if (!raw || /['"\s]/.test(raw)) {
    return null;
  }
  try {
    return new URL(raw).toString().replace(/\/$/, "");
  } catch {
    return null;
  }
}

type BillingEventRecord = {
  id: string;
  org_id: string;
  stripe_event_id: string;
  event_type: string;
  created_at: string;
  processed_at: string | null;
  status: "received" | "processed" | "failed";
  error: string | null;
};

function normalizeEventRow(value: unknown, orgId: string): BillingEventRecord | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const row = value as Record<string, unknown>;
  if (
    typeof row.id !== "string" ||
    typeof row.stripe_event_id !== "string" ||
    typeof row.event_type !== "string" ||
    typeof row.created_at !== "string"
  ) {
    return null;
  }
  const status =
    row.status === "processed" || row.status === "failed" || row.status === "received"
      ? row.status
      : "received";
  return {
    id: row.id,
    org_id: typeof row.org_id === "string" ? row.org_id : orgId,
    stripe_event_id: row.stripe_event_id,
    event_type: row.event_type,
    created_at: row.created_at,
    processed_at: typeof row.processed_at === "string" ? row.processed_at : null,
    status,
    error: typeof row.error === "string" ? row.error : null,
  };
}

function upstreamErrorMessage(payload: unknown): string {
  if (payload && typeof payload === "object") {
    const row = payload as Record<string, unknown>;
    if (typeof row.message === "string" && row.message.trim()) {
      return row.message;
    }
    if (typeof row.detail === "string" && row.detail.trim()) {
      return row.detail;
    }
  }
  return "Request failed";
}

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

export async function GET(request: NextRequest) {
  const orgId = request.nextUrl.searchParams.get("org_id")?.trim() ?? "";
  if (!orgId) {
    return NextResponse.json({ message: "org_id is required" }, { status: 400 });
  }

  const limitRaw = request.nextUrl.searchParams.get("limit")?.trim();
  const parsedLimit = Number(limitRaw);
  const limit = Number.isInteger(parsedLimit) && parsedLimit > 0 ? Math.min(parsedLimit, 100) : 25;

  const supabase = await createClient();
  const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
  if (sessionError || !sessionData.session?.access_token || !sessionData.session.user.id) {
    return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
  }

  const { data: memberRow, error: memberError } = await supabase
    .from("org_members")
    .select("org_id")
    .eq("org_id", orgId)
    .eq("user_id", sessionData.session.user.id)
    .maybeSingle();
  if (memberError) {
    return NextResponse.json({ message: "Failed to verify workspace membership" }, { status: 502 });
  }
  if (!memberRow) {
    return NextResponse.json({ message: "Forbidden" }, { status: 403 });
  }

  const apiBaseUrl = getApiBaseUrl();
  try {
    if (apiBaseUrl) {
      const upstreamResponse = await fetchWithTimeout(
        `${apiBaseUrl}/api/v1/orgs/${encodeURIComponent(orgId)}/billing/events?limit=${limit}`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${sessionData.session.access_token}`,
            "Content-Type": "application/json",
          },
          cache: "no-store",
        },
        10_000,
      );
      const upstreamJson = (await upstreamResponse.json().catch(() => ({}))) as Record<string, unknown>;
      if (upstreamResponse.ok) {
        const events = Array.isArray(upstreamJson.events)
          ? upstreamJson.events
              .map((row) => normalizeEventRow(row, orgId))
              .filter((row): row is BillingEventRecord => row !== null)
          : [];
        return NextResponse.json({ events }, { status: 200 });
      }

      if (upstreamResponse.status < 500) {
        return NextResponse.json(
          { message: upstreamErrorMessage(upstreamJson) },
          { status: upstreamResponse.status },
        );
      }

      console.warn("api/billing/events using supabase fallback", {
        org_id: orgId,
        upstream_status: upstreamResponse.status,
      });
    }
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown";
    console.warn("api/billing/events upstream failed; using supabase fallback", {
      org_id: orgId,
      message,
    });
  }

  const { data: eventRows, error: eventsError } = await supabase
    .from("billing_events")
    .select("id,org_id,stripe_event_id,event_type,created_at,processed_at,status,error")
    .eq("org_id", orgId)
    .order("created_at", { ascending: false })
    .limit(limit);
  if (eventsError) {
    return NextResponse.json({ message: "Failed to load billing events" }, { status: 502 });
  }

  const events = Array.isArray(eventRows)
    ? eventRows
        .map((row) => normalizeEventRow(row, orgId))
        .filter((row): row is BillingEventRecord => row !== null)
    : [];
  return NextResponse.json({ events }, { status: 200 });
}
