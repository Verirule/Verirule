import { createClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type PostgrestLikeError = {
  code?: string | null;
  details?: string | null;
  hint?: string | null;
  message?: string | null;
};

type SessionContext = {
  accessToken: string;
  supabase: Awaited<ReturnType<typeof createClient>>;
};

const FAST_API_TIMEOUT_MS = 3500;

function getApiBaseUrl(): string | null {
  const raw = process.env.VERIRULE_API_URL?.trim();
  if (!raw || /['"\s]/.test(raw)) {
    return null;
  }

  try {
    const parsed = new URL(raw);
    return parsed.toString().replace(/\/$/, "");
  } catch {
    return null;
  }
}

function extractEnvVarNames(input: string): string[] {
  const matches = input.match(
    /\b(?:NEXT_PUBLIC_[A-Z0-9_]+|SUPABASE_[A-Z0-9_]+|STRIPE_[A-Z0-9_]+|VERIRULE_[A-Z0-9_]+)\b/g,
  );
  if (!matches) {
    return [];
  }
  return Array.from(new Set(matches));
}

function isRlsOrMembershipError(error: PostgrestLikeError): boolean {
  const merged = `${error.message ?? ""} ${error.details ?? ""} ${error.hint ?? ""}`.toLowerCase();
  return (
    error.code === "42501" ||
    merged.includes("row-level security") ||
    merged.includes("permission denied") ||
    merged.includes("not a member")
  );
}

function apiError(
  status: number,
  message: string,
  code: string,
  extra?: Record<string, unknown>,
): NextResponse {
  return NextResponse.json({ message, code, ...(extra ?? {}) }, { status });
}

function toOrgRecord(value: unknown): OrgRecord | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const row = value as Record<string, unknown>;
  if (
    typeof row.id !== "string" ||
    typeof row.name !== "string" ||
    typeof row.created_at !== "string"
  ) {
    return null;
  }

  return {
    id: row.id,
    name: row.name,
    created_at: row.created_at,
  };
}

function logProxyFailure(label: string, error: unknown): void {
  const message = error instanceof Error ? error.message : "Unknown error";
  console.error(label, { message });
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

async function getSessionContext(): Promise<
  { context: SessionContext; response: null } | { context: null; response: NextResponse }
> {
  let supabase: Awaited<ReturnType<typeof createClient>>;
  try {
    supabase = await createClient();
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Supabase env not configured";
    const missing = extractEnvVarNames(message);
    return {
      context: null,
      response: apiError(500, "Missing required environment variables", "env_missing", {
        missing,
      }),
    };
  }

  const { data, error } = await supabase.auth.getSession();
  if (error || !data.session?.access_token) {
    return {
      context: null,
      response: apiError(401, "Sign in again", "unauthorized"),
    };
  }

  return {
    context: { supabase, accessToken: data.session.access_token },
    response: null,
  };
}

async function tryFastApiOrgsRequest(
  method: "GET" | "POST",
  accessToken: string,
  payload?: Record<string, unknown>,
): Promise<NextResponse | null> {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    return null;
  }

  try {
    const health = await fetchWithTimeout(
      `${apiBaseUrl}/healthz`,
      {
        method: "GET",
        cache: "no-store",
      },
      2000,
    );

    if (!health.ok) {
      return null;
    }
  } catch (error: unknown) {
    logProxyFailure("api/orgs health check failed", error);
    return null;
  }

  try {
    const upstream = await fetchWithTimeout(
      `${apiBaseUrl}/api/v1/orgs`,
      {
        method,
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: payload ? JSON.stringify(payload) : undefined,
        cache: "no-store",
      },
      FAST_API_TIMEOUT_MS,
    );

    if (!upstream.ok) {
      console.error("api/orgs upstream failed", { status: upstream.status });
      return null;
    }

    const body = (await upstream.json().catch(() => ({}))) as unknown;
    return NextResponse.json(body, { status: 200 });
  } catch (error: unknown) {
    logProxyFailure("api/orgs upstream failed", error);
    return null;
  }
}

function mapPostgrestFailure(error: PostgrestLikeError, fallbackMessage: string): NextResponse {
  if (isRlsOrMembershipError(error)) {
    return apiError(403, "No access to orgs; verify membership", "rls_denied");
  }

  const detail =
    typeof error.message === "string" && error.message.trim().length > 0
      ? error.message
      : fallbackMessage;
  return apiError(502, detail, "supabase_error");
}

async function listOrgsFromSupabase(
  supabase: Awaited<ReturnType<typeof createClient>>,
): Promise<NextResponse> {
  const { data, error } = await supabase
    .from("orgs")
    .select("id,name,created_at")
    .order("created_at", { ascending: false });

  if (error) {
    return mapPostgrestFailure(error, "Failed to fetch organizations");
  }

  const orgs = Array.isArray(data)
    ? data.map((row) => toOrgRecord(row)).filter((row): row is OrgRecord => row !== null)
    : [];

  return NextResponse.json({ orgs }, { status: 200 });
}

async function createOrgInSupabase(
  supabase: Awaited<ReturnType<typeof createClient>>,
  name: string,
): Promise<NextResponse> {
  const normalizedName = name.trim();
  if (normalizedName.length < 2 || normalizedName.length > 80) {
    return apiError(400, "Workspace name must be between 2 and 80 characters", "invalid_payload");
  }

  const { data, error } = await supabase.rpc("create_org", { p_name: normalizedName });
  if (error) {
    return mapPostgrestFailure(error, "Failed to create organization");
  }

  if (typeof data !== "string" || !data) {
    return apiError(502, "Invalid create organization response", "supabase_error");
  }

  const { data: orgRow } = await supabase
    .from("orgs")
    .select("id,name,created_at")
    .eq("id", data)
    .maybeSingle();

  const created = toOrgRecord(orgRow);
  return NextResponse.json({ id: data, org: created }, { status: 201 });
}

export async function GET() {
  const { context, response } = await getSessionContext();
  if (response) {
    return response;
  }

  const fastApiResponse = await tryFastApiOrgsRequest("GET", context.accessToken);
  if (fastApiResponse) {
    return fastApiResponse;
  }

  return listOrgsFromSupabase(context.supabase);
}

export async function POST(request: NextRequest) {
  const payload = (await request.json().catch(() => null)) as { name?: unknown } | null;
  const name = typeof payload?.name === "string" ? payload.name : "";
  if (!name.trim()) {
    return apiError(400, "Invalid org payload", "invalid_payload");
  }

  const { context, response } = await getSessionContext();
  if (response) {
    return response;
  }

  const fastApiResponse = await tryFastApiOrgsRequest("POST", context.accessToken, {
    name: name.trim(),
  });
  if (fastApiResponse) {
    return fastApiResponse;
  }

  return createOrgInSupabase(context.supabase, name);
}
