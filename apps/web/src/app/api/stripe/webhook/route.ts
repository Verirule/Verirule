import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";
import { getPlanFromPriceId, type BillingPlan } from "@/src/lib/billing";
import { getStripeServerClient } from "@/src/lib/stripe";

type BillingSyncPayload = {
  orgId: string;
  plan: BillingPlan;
  customerId: string | null;
  subscriptionId: string | null;
  priceId: string | null;
  status: string | null;
  currentPeriodEnd: string | null;
};

function getRequiredServerEnv() {
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET?.trim();
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY?.trim();
  const supabaseUrl =
    process.env.SUPABASE_URL?.trim() ?? process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();

  if (!webhookSecret) {
    throw new Error("STRIPE_WEBHOOK_SECRET is missing");
  }
  if (!serviceRoleKey) {
    throw new Error("SUPABASE_SERVICE_ROLE_KEY is missing");
  }
  if (!supabaseUrl) {
    throw new Error("SUPABASE_URL or NEXT_PUBLIC_SUPABASE_URL is missing");
  }

  return { webhookSecret, serviceRoleKey, supabaseUrl: supabaseUrl.replace(/\/$/, "") };
}

function formatPeriodEnd(periodEndSeconds: number | null | undefined): string | null {
  if (!periodEndSeconds || Number.isNaN(periodEndSeconds)) {
    return null;
  }
  return new Date(periodEndSeconds * 1000).toISOString();
}

function getCustomerId(customer: string | Stripe.Customer | Stripe.DeletedCustomer | null): string | null {
  if (!customer) return null;
  if (typeof customer === "string") return customer;
  return customer.id ?? null;
}

function getSubscriptionId(
  subscription: string | Stripe.Subscription | null,
): string | null {
  if (!subscription) return null;
  if (typeof subscription === "string") return subscription;
  return subscription.id ?? null;
}

async function fetchOrgIdByField(
  field: "stripe_customer_id" | "stripe_subscription_id",
  value: string,
  env: ReturnType<typeof getRequiredServerEnv>,
): Promise<string | null> {
  const params = new URLSearchParams({
    select: "org_id",
    [field]: `eq.${value}`,
    limit: "1",
  });

  const response = await fetch(`${env.supabaseUrl}/rest/v1/org_billing?${params.toString()}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${env.serviceRoleKey}`,
      apikey: env.serviceRoleKey,
      Accept: "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed lookup for ${field}: ${response.status}`);
  }

  const rows = (await response.json().catch(() => [])) as Array<{ org_id?: unknown }>;
  const orgId = rows[0]?.org_id;
  return typeof orgId === "string" && orgId ? orgId : null;
}

async function resolveOrgId(
  directOrgId: string | null,
  customerId: string | null,
  subscriptionId: string | null,
  env: ReturnType<typeof getRequiredServerEnv>,
): Promise<string | null> {
  if (directOrgId) {
    return directOrgId;
  }
  if (subscriptionId) {
    const orgIdFromSubscription = await fetchOrgIdByField(
      "stripe_subscription_id",
      subscriptionId,
      env,
    );
    if (orgIdFromSubscription) {
      return orgIdFromSubscription;
    }
  }
  if (customerId) {
    return fetchOrgIdByField("stripe_customer_id", customerId, env);
  }
  return null;
}

async function callSetOrgPlan(
  env: ReturnType<typeof getRequiredServerEnv>,
  payload: BillingSyncPayload,
): Promise<void> {
  const response = await fetch(`${env.supabaseUrl}/rest/v1/rpc/set_org_plan`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.serviceRoleKey}`,
      apikey: env.serviceRoleKey,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      p_org_id: payload.orgId,
      p_plan: payload.plan,
      p_customer_id: payload.customerId,
      p_subscription_id: payload.subscriptionId,
      p_price_id: payload.priceId,
      p_status: payload.status,
      p_current_period_end: payload.currentPeriodEnd,
    }),
  });

  if (!response.ok) {
    const responseBody = await response.text().catch(() => "");
    throw new Error(`set_org_plan failed: ${response.status} ${responseBody}`.trim());
  }
}

function getPriceIdFromSubscription(subscription: Stripe.Subscription): string | null {
  const firstItem = subscription.items.data[0];
  return firstItem?.price?.id ?? null;
}

function getPeriodEndFromSubscription(subscription: Stripe.Subscription): number | null {
  const firstItem = subscription.items.data[0];
  return typeof firstItem?.current_period_end === "number" ? firstItem.current_period_end : null;
}

function syncLog(eventType: string, orgId: string | null, status: string | null) {
  console.info("stripe webhook billing sync", {
    eventType,
    orgId,
    status,
  });
}

export async function POST(request: NextRequest) {
  let env: ReturnType<typeof getRequiredServerEnv>;
  try {
    env = getRequiredServerEnv();
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Webhook configuration error";
    return NextResponse.json({ message }, { status: 500 });
  }

  const signature = request.headers.get("stripe-signature");
  if (!signature) {
    return NextResponse.json({ message: "Missing Stripe signature" }, { status: 400 });
  }

  const body = await request.text();
  const stripe = getStripeServerClient();

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(body, signature, env.webhookSecret);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Invalid webhook signature";
    return NextResponse.json({ message }, { status: 400 });
  }

  try {
    if (event.type === "checkout.session.completed") {
      const session = event.data.object as Stripe.Checkout.Session;
      const customerId = getCustomerId(session.customer);
      const subscriptionId = getSubscriptionId(session.subscription);
      const sessionMetadata = session.metadata ?? {};
      const metadataOrgId =
        typeof sessionMetadata.org_id === "string" ? sessionMetadata.org_id : null;

      let plan: BillingPlan = "free";
      let status: string | null = null;
      let currentPeriodEnd: string | null = null;
      let priceId: string | null = null;
      let orgId: string | null = metadataOrgId;

      if (subscriptionId) {
        const subscription = (await stripe.subscriptions.retrieve(
          subscriptionId,
        )) as unknown as Stripe.Subscription;
        const metadataOrgFromSubscription =
          typeof subscription.metadata?.org_id === "string"
            ? subscription.metadata.org_id
            : null;
        orgId = await resolveOrgId(metadataOrgFromSubscription ?? orgId, customerId, subscriptionId, env);
        priceId = getPriceIdFromSubscription(subscription);
        plan = getPlanFromPriceId(priceId);
        status = subscription.status ?? null;
        currentPeriodEnd = formatPeriodEnd(getPeriodEndFromSubscription(subscription));
      } else {
        orgId = await resolveOrgId(orgId, customerId, subscriptionId, env);
      }

      if (!orgId) {
        syncLog(event.type, null, status);
        return NextResponse.json({ ok: true }, { status: 200 });
      }

      await callSetOrgPlan(env, {
        orgId,
        plan,
        customerId,
        subscriptionId,
        priceId,
        status,
        currentPeriodEnd,
      });
      syncLog(event.type, orgId, status);
      return NextResponse.json({ ok: true }, { status: 200 });
    }

    if (
      event.type === "customer.subscription.created" ||
      event.type === "customer.subscription.updated" ||
      event.type === "customer.subscription.deleted"
    ) {
      const subscription = event.data.object as Stripe.Subscription;
      const customerId = getCustomerId(subscription.customer);
      const subscriptionId = subscription.id;
      const metadataOrgId =
        typeof subscription.metadata?.org_id === "string" ? subscription.metadata.org_id : null;
      const orgId = await resolveOrgId(metadataOrgId, customerId, subscriptionId, env);
      const priceId = getPriceIdFromSubscription(subscription);
      const status = subscription.status ?? null;
      const currentPeriodEnd = formatPeriodEnd(getPeriodEndFromSubscription(subscription));
      const plan: BillingPlan =
        event.type === "customer.subscription.deleted" ? "free" : getPlanFromPriceId(priceId);

      if (!orgId) {
        syncLog(event.type, null, status);
        return NextResponse.json({ ok: true }, { status: 200 });
      }

      await callSetOrgPlan(env, {
        orgId,
        plan,
        customerId,
        subscriptionId,
        priceId,
        status,
        currentPeriodEnd,
      });
      syncLog(event.type, orgId, status);
      return NextResponse.json({ ok: true }, { status: 200 });
    }

    return NextResponse.json({ ok: true }, { status: 200 });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Webhook processing failed";
    return NextResponse.json({ message }, { status: 500 });
  }
}
