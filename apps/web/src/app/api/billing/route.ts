import { createClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";
import type { BillingPlan, BillingPlanStatus } from "@/src/lib/billing";
import { getPlanFeatures } from "@/src/lib/billing";

type BillingRow = {
  id: string;
  plan: BillingPlan | null;
  plan_status: BillingPlanStatus | null;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  current_period_end: string | null;
};

type BillingPayload = {
  org_id: string;
  plan: BillingPlan;
  plan_status: BillingPlanStatus;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  current_period_end: string | null;
  entitlements: {
    plan: BillingPlan;
    integrations_enabled: boolean;
    exports_enabled: boolean;
    scheduling_enabled: boolean;
    max_sources: number | null;
    max_exports_per_month: number | null;
    max_integrations: number | null;
    max_members: number | null;
  };
};

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

function normalizePlan(value: unknown): BillingPlan {
  if (value === "pro" || value === "business" || value === "free") {
    return value;
  }
  return "free";
}

function normalizePlanStatus(value: unknown): BillingPlanStatus {
  if (value === "past_due" || value === "canceled" || value === "trialing" || value === "active") {
    return value;
  }
  return "active";
}

function toBillingPayload(orgId: string, value: Partial<BillingPayload> | BillingRow | null): BillingPayload {
  const payload = (value ?? {}) as Partial<BillingPayload> &
    Partial<BillingRow> & {
      status?: unknown;
    };
  const plan = normalizePlan(payload.plan);
  const planStatus = normalizePlanStatus(
    payload.plan_status ?? payload.status,
  );
  const features = getPlanFeatures(plan);

  return {
    org_id: typeof payload.org_id === "string" && payload.org_id ? payload.org_id : orgId,
    plan,
    plan_status: planStatus,
    stripe_customer_id:
      typeof payload.stripe_customer_id === "string" ? payload.stripe_customer_id : null,
    stripe_subscription_id:
      typeof payload.stripe_subscription_id === "string" ? payload.stripe_subscription_id : null,
    current_period_end:
      typeof payload.current_period_end === "string" ? payload.current_period_end : null,
    entitlements: {
      plan,
      integrations_enabled:
        typeof payload.entitlements?.integrations_enabled === "boolean"
          ? payload.entitlements.integrations_enabled
          : features.canUseIntegrations,
      exports_enabled:
        typeof payload.entitlements?.exports_enabled === "boolean"
          ? payload.entitlements.exports_enabled
          : features.canUseExports,
      scheduling_enabled:
        typeof payload.entitlements?.scheduling_enabled === "boolean"
          ? payload.entitlements.scheduling_enabled
          : features.canUseScheduledRuns,
      max_sources:
        typeof payload.entitlements?.max_sources === "number" || payload.entitlements?.max_sources === null
          ? payload.entitlements.max_sources
          : features.maxSources,
      max_exports_per_month:
        typeof payload.entitlements?.max_exports_per_month === "number" ||
        payload.entitlements?.max_exports_per_month === null
          ? payload.entitlements.max_exports_per_month
          : features.maxExportsPerMonth,
      max_integrations:
        typeof payload.entitlements?.max_integrations === "number" ||
        payload.entitlements?.max_integrations === null
          ? payload.entitlements.max_integrations
          : features.maxIntegrations,
      max_members:
        typeof payload.entitlements?.max_members === "number" || payload.entitlements?.max_members === null
          ? payload.entitlements.max_members
          : features.maxMembers,
    },
  };
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

export async function GET(request: NextRequest) {
  const orgId = request.nextUrl.searchParams.get("org_id")?.trim() ?? "";
  if (!orgId) {
    return NextResponse.json({ message: "org_id is required" }, { status: 400 });
  }

  const supabase = await createClient();
  const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
  if (sessionError || !sessionData.session?.access_token || !sessionData.session.user.id) {
    return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
  }

  const accessToken = sessionData.session.access_token;
  const userId = sessionData.session.user.id;

  const { data: memberRow, error: memberError } = await supabase
    .from("org_members")
    .select("org_id")
    .eq("org_id", orgId)
    .eq("user_id", userId)
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
        `${apiBaseUrl}/api/v1/orgs/${encodeURIComponent(orgId)}/billing`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          cache: "no-store",
        },
        10_000,
      );

      const upstreamJson = (await upstreamResponse.json().catch(() => ({}))) as Record<string, unknown>;
      if (upstreamResponse.ok) {
        return NextResponse.json(toBillingPayload(orgId, upstreamJson), { status: 200 });
      }

      if (upstreamResponse.status < 500) {
        return NextResponse.json(
          { message: upstreamErrorMessage(upstreamJson) },
          { status: upstreamResponse.status },
        );
      }

      console.warn("api/billing using supabase fallback", {
        org_id: orgId,
        upstream_status: upstreamResponse.status,
      });
    }
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "unknown";
    console.warn("api/billing upstream failed; using supabase fallback", {
      org_id: orgId,
      message,
    });
  }

  const { data: billingRow, error: billingError } = await supabase
    .from("orgs")
    .select("id,plan,plan_status,stripe_customer_id,stripe_subscription_id,current_period_end")
    .eq("id", orgId)
    .maybeSingle();
  if (billingError) {
    return NextResponse.json({ message: "Failed to load billing status" }, { status: 502 });
  }

  const payload = toBillingPayload(orgId, (billingRow as BillingRow | null) ?? null);
  return NextResponse.json(payload, { status: 200 });
}
