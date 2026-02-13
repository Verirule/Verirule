import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";
import { getPlanFromPriceId, type BillingPlan } from "@/src/lib/billing";
import { getStripeServerClient } from "@/src/lib/stripe";

type BillingSyncPayload = {
  orgId: string;
  plan: BillingPlan;
  customerId: string | null;
  subscriptionId: string | null;
  status: string | null;
  currentPeriodEnd: string | null;
};

type RequiredEnv = {
  webhookSecret: string;
  serviceRoleKey: string;
  supabaseUrl: string;
};

function getRequiredServerEnv(): RequiredEnv {
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

function supabaseHeaders(env: RequiredEnv, json = false): HeadersInit {
  return {
    Authorization: `Bearer ${env.serviceRoleKey}`,
    apikey: env.serviceRoleKey,
    Accept: "application/json",
    ...(json ? { "Content-Type": "application/json" } : {}),
  };
}

function sanitizeErrorMessage(error: unknown): string {
  const raw = error instanceof Error ? error.message : "Webhook processing failed";
  return raw.replace(/\s+/g, " ").trim().slice(0, 200);
}

function formatPeriodEnd(periodEndSeconds: number | null | undefined): string | null {
  if (!periodEndSeconds || Number.isNaN(periodEndSeconds)) {
    return null;
  }
  return new Date(periodEndSeconds * 1000).toISOString();
}

function normalizePlanStatus(status: string | null | undefined): "active" | "past_due" | "canceled" | "trialing" {
  if (status === "past_due" || status === "canceled" || status === "trialing" || status === "active") {
    return status;
  }
  return "active";
}

function getCustomerId(customer: string | Stripe.Customer | Stripe.DeletedCustomer | null): string | null {
  if (!customer) return null;
  if (typeof customer === "string") return customer;
  return customer.id ?? null;
}

function getSubscriptionId(subscription: string | Stripe.Subscription | null): string | null {
  if (!subscription) return null;
  if (typeof subscription === "string") return subscription;
  return subscription.id ?? null;
}

function getPriceIdFromSubscription(subscription: Stripe.Subscription): string | null {
  const firstItem = subscription.items.data[0];
  return firstItem?.price?.id ?? null;
}

function getPeriodEndFromSubscription(subscription: Stripe.Subscription): number | null {
  const firstItem = subscription.items.data[0];
  return typeof firstItem?.current_period_end === "number" ? firstItem.current_period_end : null;
}

async function fetchOrgIdByField(
  field: "stripe_customer_id" | "stripe_subscription_id",
  value: string,
  env: RequiredEnv,
): Promise<string | null> {
  const params = new URLSearchParams({
    select: "id",
    [field]: `eq.${value}`,
    limit: "1",
  });

  const response = await fetch(`${env.supabaseUrl}/rest/v1/orgs?${params.toString()}`, {
    method: "GET",
    headers: supabaseHeaders(env),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed lookup for ${field}: ${response.status}`);
  }

  const rows = (await response.json().catch(() => [])) as Array<{ id?: unknown }>;
  const orgId = rows[0]?.id;
  return typeof orgId === "string" && orgId ? orgId : null;
}

async function resolveOrgId(
  directOrgId: string | null,
  customerId: string | null,
  subscriptionId: string | null,
  env: RequiredEnv,
): Promise<string | null> {
  if (directOrgId) return directOrgId;
  if (subscriptionId) {
    const orgIdFromSubscription = await fetchOrgIdByField("stripe_subscription_id", subscriptionId, env);
    if (orgIdFromSubscription) return orgIdFromSubscription;
  }
  if (customerId) {
    return fetchOrgIdByField("stripe_customer_id", customerId, env);
  }
  return null;
}

async function upsertOrgBilling(env: RequiredEnv, payload: BillingSyncPayload): Promise<void> {
  const response = await fetch(
    `${env.supabaseUrl}/rest/v1/orgs?id=eq.${encodeURIComponent(payload.orgId)}`,
    {
      method: "PATCH",
      headers: {
        ...supabaseHeaders(env, true),
        Prefer: "return=minimal",
      },
      body: JSON.stringify({
        stripe_customer_id: payload.customerId,
        stripe_subscription_id: payload.subscriptionId,
        plan: payload.plan,
        plan_status: normalizePlanStatus(payload.status),
        current_period_end: payload.currentPeriodEnd,
      }),
      cache: "no-store",
    },
  );

  if (!response.ok) {
    const responseBody = await response.text().catch(() => "");
    throw new Error(`org billing update failed: ${response.status} ${responseBody}`.trim());
  }
}

async function insertBillingEvent(
  env: RequiredEnv,
  payload: { orgId: string; eventId: string; eventType: string },
): Promise<"inserted" | "duplicate"> {
  const response = await fetch(`${env.supabaseUrl}/rest/v1/billing_events`, {
    method: "POST",
    headers: {
      ...supabaseHeaders(env, true),
      Prefer: "return=minimal",
    },
    body: JSON.stringify({
      org_id: payload.orgId,
      stripe_event_id: payload.eventId,
      event_type: payload.eventType,
      status: "received",
    }),
    cache: "no-store",
  });

  if (response.ok) {
    return "inserted";
  }
  if (response.status === 409) {
    return "duplicate";
  }

  const responseBody = await response.text().catch(() => "");
  throw new Error(`billing event insert failed: ${response.status} ${responseBody}`.trim());
}

async function updateBillingEventStatus(
  env: RequiredEnv,
  payload: {
    orgId: string;
    eventId: string;
    status: "processed" | "failed";
    error: string | null;
  },
): Promise<void> {
  const params = new URLSearchParams({
    org_id: `eq.${payload.orgId}`,
    stripe_event_id: `eq.${payload.eventId}`,
  });
  const response = await fetch(`${env.supabaseUrl}/rest/v1/billing_events?${params.toString()}`, {
    method: "PATCH",
    headers: {
      ...supabaseHeaders(env, true),
      Prefer: "return=minimal",
    },
    body: JSON.stringify({
      status: payload.status,
      processed_at: new Date().toISOString(),
      error: payload.error,
    }),
    cache: "no-store",
  });

  if (!response.ok) {
    const responseBody = await response.text().catch(() => "");
    throw new Error(`billing event update failed: ${response.status} ${responseBody}`.trim());
  }
}

function syncLog(event: Stripe.Event, orgId: string | null, state: "processed" | "duplicate" | "skipped" | "failed") {
  console.info("stripe webhook billing sync", {
    eventId: event.id,
    eventType: event.type,
    orgId,
    state,
  });
}

async function buildSyncPayload(
  event: Stripe.Event,
  stripe: Stripe,
  env: RequiredEnv,
): Promise<BillingSyncPayload | null> {
  if (event.type === "checkout.session.completed") {
    const session = event.data.object as Stripe.Checkout.Session;
    const customerId = getCustomerId(session.customer);
    const subscriptionId = getSubscriptionId(session.subscription);
    const metadataOrgId =
      typeof session.metadata?.org_id === "string" ? session.metadata.org_id : null;

    let plan: BillingPlan = "free";
    let status: string | null = null;
    let currentPeriodEnd: string | null = null;
    let orgId: string | null = metadataOrgId;

    if (subscriptionId) {
      const subscription = (await stripe.subscriptions.retrieve(subscriptionId)) as Stripe.Subscription;
      const metadataOrgFromSubscription =
        typeof subscription.metadata?.org_id === "string" ? subscription.metadata.org_id : null;
      orgId = await resolveOrgId(metadataOrgFromSubscription ?? orgId, customerId, subscriptionId, env);
      const priceId = getPriceIdFromSubscription(subscription);
      plan = getPlanFromPriceId(priceId);
      status = subscription.status ?? null;
      currentPeriodEnd = formatPeriodEnd(getPeriodEndFromSubscription(subscription));
    } else {
      orgId = await resolveOrgId(orgId, customerId, subscriptionId, env);
    }

    if (!orgId) return null;
    return {
      orgId,
      plan,
      customerId,
      subscriptionId,
      status,
      currentPeriodEnd,
    };
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
    if (!orgId) return null;

    const priceId = getPriceIdFromSubscription(subscription);
    return {
      orgId,
      plan: event.type === "customer.subscription.deleted" ? "free" : getPlanFromPriceId(priceId),
      customerId,
      subscriptionId,
      status: event.type === "customer.subscription.deleted" ? "canceled" : subscription.status ?? null,
      currentPeriodEnd: formatPeriodEnd(getPeriodEndFromSubscription(subscription)),
    };
  }

  return null;
}

export async function POST(request: NextRequest) {
  let env: RequiredEnv;
  try {
    env = getRequiredServerEnv();
  } catch (error: unknown) {
    const message = sanitizeErrorMessage(error);
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
    const message = sanitizeErrorMessage(error);
    return NextResponse.json({ message }, { status: 400 });
  }

  let syncPayload: BillingSyncPayload | null = null;
  try {
    syncPayload = await buildSyncPayload(event, stripe, env);
    if (!syncPayload) {
      syncLog(event, null, "skipped");
      return NextResponse.json({ ok: true }, { status: 200 });
    }

    const insertResult = await insertBillingEvent(env, {
      orgId: syncPayload.orgId,
      eventId: event.id,
      eventType: event.type,
    });
    if (insertResult === "duplicate") {
      syncLog(event, syncPayload.orgId, "duplicate");
      return NextResponse.json({ ok: true }, { status: 200 });
    }

    await upsertOrgBilling(env, syncPayload);
    await updateBillingEventStatus(env, {
      orgId: syncPayload.orgId,
      eventId: event.id,
      status: "processed",
      error: null,
    });
    syncLog(event, syncPayload.orgId, "processed");
    return NextResponse.json({ ok: true }, { status: 200 });
  } catch (error: unknown) {
    if (syncPayload?.orgId) {
      try {
        await updateBillingEventStatus(env, {
          orgId: syncPayload.orgId,
          eventId: event.id,
          status: "failed",
          error: sanitizeErrorMessage(error),
        });
      } catch {
        // Best-effort update for failed state; do not throw from this block.
      }
      syncLog(event, syncPayload.orgId, "failed");
    } else {
      syncLog(event, null, "failed");
    }
    return NextResponse.json({ message: sanitizeErrorMessage(error) }, { status: 500 });
  }
}
