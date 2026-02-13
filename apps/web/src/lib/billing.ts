export type BillingPlan = "free" | "pro" | "business";
export type BillingPlanStatus = "active" | "past_due" | "canceled" | "trialing";

export const FREE_SOURCE_LIMIT = 5;

export type BillingEntitlements = {
  plan: BillingPlan;
  integrations_enabled: boolean;
  exports_enabled: boolean;
  scheduling_enabled: boolean;
  max_sources: number | null;
  max_exports_per_month: number | null;
  max_integrations: number | null;
};

export type BillingStatusResponse = {
  org_id: string;
  plan: BillingPlan;
  plan_status: BillingPlanStatus;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  current_period_end: string | null;
  entitlements: BillingEntitlements;
};

export function getPlanFromPriceId(priceId: string | null | undefined): BillingPlan {
  const proPriceId = process.env.STRIPE_PRICE_PRO?.trim();
  const businessPriceId = process.env.STRIPE_PRICE_BUSINESS?.trim();

  if (priceId && businessPriceId && priceId === businessPriceId) {
    return "business";
  }
  if (priceId && proPriceId && priceId === proPriceId) {
    return "pro";
  }
  return "free";
}

export function getStripePriceIdForPlan(plan: Exclude<BillingPlan, "free">): string {
  const proPriceId = process.env.STRIPE_PRICE_PRO?.trim();
  const businessPriceId = process.env.STRIPE_PRICE_BUSINESS?.trim();

  if (plan === "pro") {
    if (!proPriceId) {
      throw new Error("STRIPE_PRICE_PRO is missing");
    }
    return proPriceId;
  }

  if (!businessPriceId) {
    throw new Error("STRIPE_PRICE_BUSINESS is missing");
  }
  return businessPriceId;
}

export type PlanFeatures = {
  canUseIntegrations: boolean;
  canUseExports: boolean;
  canUseScheduledRuns: boolean;
  maxSources: number | null;
  maxExportsPerMonth: number | null;
  maxIntegrations: number | null;
};

export function getPlanFeatures(plan: BillingPlan): PlanFeatures {
  if (plan === "business") {
    return {
      canUseIntegrations: true,
      canUseExports: true,
      canUseScheduledRuns: true,
      maxSources: null,
      maxExportsPerMonth: null,
      maxIntegrations: null,
    };
  }

  if (plan === "pro") {
    return {
      canUseIntegrations: true,
      canUseExports: true,
      canUseScheduledRuns: true,
      maxSources: null,
      maxExportsPerMonth: 500,
      maxIntegrations: 10,
    };
  }

  return {
    canUseIntegrations: false,
    canUseExports: false,
    canUseScheduledRuns: false,
    maxSources: FREE_SOURCE_LIMIT,
    maxExportsPerMonth: 5,
    maxIntegrations: 0,
  };
}
