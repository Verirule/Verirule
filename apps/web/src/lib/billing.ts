export type BillingPlan = "free" | "pro" | "business";
export type BillingPlanStatus = "active" | "past_due" | "canceled" | "trialing";

export const FREE_SOURCE_LIMIT = 3;

export type BillingEntitlements = {
  plan: BillingPlan;
  integrations_enabled: boolean;
  exports_enabled: boolean;
  scheduling_enabled: boolean;
  max_sources: number | null;
  max_exports_per_month: number | null;
  max_integrations: number | null;
  max_members: number | null;
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
  maxMembers: number | null;
};

const DEFAULT_PRO_DISPLAY_PRICE = "£19";
const DEFAULT_BUSINESS_DISPLAY_PRICE = "£49";

function readDisplayPrice(raw: string | undefined): string | null {
  const value = raw?.trim();
  return value ? value : null;
}

export function getPlanDisplayPrice(plan: BillingPlan): string | null {
  if (plan === "free") {
    return "£0";
  }

  if (plan === "pro") {
    return readDisplayPrice(process.env.NEXT_PUBLIC_PRICE_PRO_DISPLAY) ?? DEFAULT_PRO_DISPLAY_PRICE;
  }

  return readDisplayPrice(process.env.NEXT_PUBLIC_PRICE_BUSINESS_DISPLAY) ?? DEFAULT_BUSINESS_DISPLAY_PRICE;
}

function formatLimit(value: number | null): string {
  return value === null ? "Unlimited" : String(value);
}

export function getPlanIncludedItems(plan: BillingPlan): string[] {
  const features = getPlanFeatures(plan);
  const integrationsText = features.canUseIntegrations
    ? `Integrations: up to ${formatLimit(features.maxIntegrations)}`
    : "Integrations: not included";

  return [
    `Sources: up to ${formatLimit(features.maxSources)}`,
    `Members: up to ${formatLimit(features.maxMembers)}`,
    `Exports per month: up to ${formatLimit(features.maxExportsPerMonth)}`,
    integrationsText,
    `Scheduled runs: ${features.canUseScheduledRuns ? "included" : "not included"}`,
  ];
}

export function getPlanFeatures(plan: BillingPlan): PlanFeatures {
  if (plan === "business") {
    return {
      canUseIntegrations: true,
      canUseExports: true,
      canUseScheduledRuns: true,
      maxSources: 100,
      maxExportsPerMonth: 500,
      maxIntegrations: 50,
      maxMembers: 100,
    };
  }

  if (plan === "pro") {
    return {
      canUseIntegrations: true,
      canUseExports: true,
      canUseScheduledRuns: true,
      maxSources: 25,
      maxExportsPerMonth: 500,
      maxIntegrations: 10,
      maxMembers: 25,
    };
  }

  return {
    canUseIntegrations: false,
    canUseExports: true,
    canUseScheduledRuns: true,
    maxSources: FREE_SOURCE_LIMIT,
    maxExportsPerMonth: 1,
    maxIntegrations: 0,
    maxMembers: 5,
  };
}
