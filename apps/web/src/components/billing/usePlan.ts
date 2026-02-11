"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getPlanFeatures,
  type BillingPlan,
  type BillingStatusResponse,
  type PlanFeatures,
} from "@/src/lib/billing";

type PlanState = BillingStatusResponse & {
  features: PlanFeatures;
};

type UsePlanResult = {
  plan: BillingPlan;
  status: string | null;
  currentPeriodEnd: string | null;
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
  return {
    plan,
    status: typeof row.status === "string" ? row.status : null,
    current_period_end:
      typeof row.current_period_end === "string" ? row.current_period_end : null,
  };
}

async function fetchPlanStatus(orgId: string, forceRefresh = false): Promise<BillingStatusResponse> {
  if (!forceRefresh && statusPromiseCache.has(orgId)) {
    return statusPromiseCache.get(orgId) as Promise<BillingStatusResponse>;
  }

  const pending = fetch(`/api/billing/status?org_id=${encodeURIComponent(orgId)}`, {
    method: "GET",
    cache: "no-store",
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error("Failed to load billing status");
    }
    return normalizeStatus(await response.json().catch(() => ({})));
  });

  statusPromiseCache.set(orgId, pending);
  return pending;
}

const FREE_PLAN_STATE: PlanState = {
  plan: "free",
  status: "inactive",
  current_period_end: null,
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
        setState({
          ...result,
          features: getPlanFeatures(result.plan),
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
    plan: state.plan,
    status: state.status,
    currentPeriodEnd: state.current_period_end,
    features: state.features,
    loading,
    error,
    refresh: async () => load(true),
  };
}
