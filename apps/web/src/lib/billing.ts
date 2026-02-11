export type BillingPlan = "free" | "pro" | "business";

export const FREE_SOURCE_LIMIT = 5;

export type BillingStatusResponse = {
  plan: BillingPlan;
  status: string | null;
  current_period_end: string | null;
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
  canUseScheduledRuns: boolean;
  maxSources: number | null;
  prioritySupport: boolean;
};

export function getPlanFeatures(plan: BillingPlan): PlanFeatures {
  if (plan === "business") {
    return {
      canUseIntegrations: true,
      canUseScheduledRuns: true,
      maxSources: null,
      prioritySupport: true,
    };
  }

  if (plan === "pro") {
    return {
      canUseIntegrations: true,
      canUseScheduledRuns: true,
      maxSources: null,
      prioritySupport: false,
    };
  }

  return {
    canUseIntegrations: false,
    canUseScheduledRuns: false,
    maxSources: FREE_SOURCE_LIMIT,
    prioritySupport: false,
  };
}
