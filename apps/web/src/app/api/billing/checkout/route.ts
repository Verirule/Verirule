import { createClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";
import { getStripePriceIdForPlan } from "@/src/lib/billing";
import { getSiteUrl } from "@/src/lib/env";
import { getStripeServerClient } from "@/src/lib/stripe";

type CheckoutPlan = "pro" | "business";

type CheckoutPayload = {
  org_id?: unknown;
  plan?: unknown;
};

type OrgBillingCustomerRow = {
  stripe_customer_id: string | null;
};

function parsePayload(payload: CheckoutPayload | null): { orgId: string; plan: CheckoutPlan | null } {
  const orgId = typeof payload?.org_id === "string" ? payload.org_id.trim() : "";
  const plan = payload?.plan === "pro" || payload?.plan === "business" ? payload.plan : null;
  return { orgId, plan };
}

export async function POST(request: NextRequest) {
  const payload = (await request.json().catch(() => null)) as CheckoutPayload | null;
  const { orgId, plan } = parsePayload(payload);
  if (!orgId || !plan) {
    return NextResponse.json({ message: "Invalid checkout payload" }, { status: 400 });
  }

  const siteUrl = getSiteUrl(request);
  if (!siteUrl) {
    return NextResponse.json({ message: "NEXT_PUBLIC_SITE_URL is missing" }, { status: 500 });
  }

  const supabase = await createClient();
  const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
  if (sessionError || !sessionData.session?.user?.id) {
    return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
  }

  const user = sessionData.session.user;
  const userId = user.id;

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

  const { data: billingRow, error: billingError } = await supabase
    .from("orgs")
    .select("stripe_customer_id")
    .eq("id", orgId)
    .maybeSingle();
  if (billingError) {
    return NextResponse.json({ message: "Failed to load billing record" }, { status: 502 });
  }

  try {
    const stripe = getStripeServerClient();
    let customerId = (billingRow as OrgBillingCustomerRow | null)?.stripe_customer_id ?? null;
    if (!customerId) {
      const customer = await stripe.customers.create({
        email: user.email ?? undefined,
        metadata: {
          org_id: orgId,
          user_id: userId,
        },
      });
      customerId = customer.id;
    }

    const priceId = getStripePriceIdForPlan(plan);
    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      customer: customerId,
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${siteUrl}/dashboard/billing?success=1`,
      cancel_url: `${siteUrl}/dashboard/billing?canceled=1`,
      metadata: {
        org_id: orgId,
        user_id: userId,
      },
      subscription_data: {
        metadata: {
          org_id: orgId,
          user_id: userId,
        },
      },
    });

    if (!session.url) {
      return NextResponse.json({ message: "Stripe checkout session missing URL" }, { status: 502 });
    }

    return NextResponse.json({ url: session.url }, { status: 200 });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Failed to create Stripe checkout session";
    return NextResponse.json({ message }, { status: 500 });
  }
}
