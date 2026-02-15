"use client";

import { useCallback, useEffect, useState } from "react";
import {
  FREE_SOURCE_LIMIT,
  type BillingEntitlements,
  type BillingPlanStatus,
  getPlanFeatures,
  type BillingPlan,
  type BillingStatusResponse,
  type PlanFeatures,
} from "@/src/lib/billing";

type PlanState = BillingStatusResponse & {
  features: PlanFeatures;
};

type UsePlanResult = {
  orgId: string | null;
  plan: BillingPlan;
  status: BillingPlanStatus;
  currentPeriodEnd: string | null;
  entitlements: BillingEntitlements;
  features: PlanFeatures;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const statusPromiseCache = new Map<string, Promise<BillingStatusResponse>>();

function normalizeStatus(payload: unknown): BillingStatusResponse {
  const row = (payload ?? {}) as Partial<BillingStatusResponse>;
  const plan: BillingPlan =
    row.plan === "pro" || row.plan === "business" || row.plan === "free" ? row.plan : "free";
  const legacyStatus = (payload as { status?: unknown } | null)?.status;
  const planStatus: BillingPlanStatus =
    row.plan_status === "past_due" ||
    row.plan_status === "canceled" ||
    row.plan_status === "trialing" ||
    row.plan_status === "active"
      ? row.plan_status
      : legacyStatus === "past_due" ||
          legacyStatus === "canceled" ||
          legacyStatus === "trialing" ||
          legacyStatus === "active"
        ? legacyStatus
      : "active";

  const fallbackFeatures = getPlanFeatures(plan);
  const entitlements: BillingEntitlements = {
    plan,
    integrations_enabled:
      typeof row.entitlements?.integrations_enabled === "boolean"
        ? row.entitlements.integrations_enabled
        : fallbackFeatures.canUseIntegrations,
    exports_enabled:
      typeof row.entitlements?.exports_enabled === "boolean"
        ? row.entitlements.exports_enabled
        : fallbackFeatures.canUseExports,
    scheduling_enabled:
      typeof row.entitlements?.scheduling_enabled === "boolean"
        ? row.entitlements.scheduling_enabled
        : fallbackFeatures.canUseScheduledRuns,
    max_sources:
      typeof row.entitlements?.max_sources === "number" || row.entitlements?.max_sources === null
        ? row.entitlements.max_sources
        : fallbackFeatures.maxSources,
    max_exports_per_month:
      typeof row.entitlements?.max_exports_per_month === "number" ||
      row.entitlements?.max_exports_per_month === null
        ? row.entitlements.max_exports_per_month
        : fallbackFeatures.maxExportsPerMonth,
    max_integrations:
      typeof row.entitlements?.max_integrations === "number" || row.entitlements?.max_integrations === null
        ? row.entitlements.max_integrations
        : fallbackFeatures.maxIntegrations,
    max_members:
      typeof row.entitlements?.max_members === "number" || row.entitlements?.max_members === null
        ? row.entitlements.max_members
        : fallbackFeatures.maxMembers,
  };

  return {
    org_id: typeof row.org_id === "string" ? row.org_id : "",
    plan,
    plan_status: planStatus,
    stripe_customer_id: typeof row.stripe_customer_id === "string" ? row.stripe_customer_id : null,
    stripe_subscription_id:
      typeof row.stripe_subscription_id === "string" ? row.stripe_subscription_id : null,
    current_period_end:
      typeof row.current_period_end === "string" ? row.current_period_end : null,
    entitlements,
  };
}

async function fetchPlanStatus(orgId: string, forceRefresh = false): Promise<BillingStatusResponse> {
  if (!forceRefresh && statusPromiseCache.has(orgId)) {
    return statusPromiseCache.get(orgId) as Promise<BillingStatusResponse>;
  }

  const pending = fetch(`/api/billing?org_id=${encodeURIComponent(orgId)}`, {
    method: "GET",
    cache: "no-store",
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error("Failed to load billing status");
      }
      return normalizeStatus(await response.json().catch(() => ({})));
    })
    .catch((error: unknown) => {
      statusPromiseCache.delete(orgId);
      throw error;
    });

  statusPromiseCache.set(orgId, pending);
  return pending;
}

const FREE_PLAN_STATE: PlanState = {
  org_id: "",
  plan: "free",
  plan_status: "active",
  stripe_customer_id: null,
  stripe_subscription_id: null,
  current_period_end: null,
  entitlements: {
    plan: "free",
    integrations_enabled: false,
    exports_enabled: true,
    scheduling_enabled: true,
    max_sources: FREE_SOURCE_LIMIT,
    max_exports_per_month: 1,
    max_integrations: 0,
    max_members: 5,
  },
  features: getPlanFeatures("free"),
};

export function usePlan(orgId: string): UsePlanResult {
  const [state, setState] = useState<PlanState>(FREE_PLAN_STATE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (forceRefresh = false) => {
      if (!orgId) {
        setState(FREE_PLAN_STATE);
        setError(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const result = await fetchPlanStatus(orgId, forceRefresh);
        const features: PlanFeatures = {
          canUseIntegrations: result.entitlements.integrations_enabled,
          canUseExports: result.entitlements.exports_enabled,
          canUseScheduledRuns: result.entitlements.scheduling_enabled,
          maxSources: result.entitlements.max_sources,
          maxExportsPerMonth: result.entitlements.max_exports_per_month,
          maxIntegrations: result.entitlements.max_integrations,
          maxMembers: result.entitlements.max_members,
        };
        setState({
          ...result,
          features,
        });
      } catch {
        setState(FREE_PLAN_STATE);
        setError("Unable to load billing plan.");
      } finally {
        setLoading(false);
      }
    },
    [orgId],
  );

  useEffect(() => {
    void load();
  }, [load]);

  return {
    orgId: state.org_id || null,
    plan: state.plan,
    status: state.plan_status,
    currentPeriodEnd: state.current_period_end,
    entitlements: state.entitlements,
    features: state.features,
    loading,
    error,
    refresh: async () => load(true),
  };
}
