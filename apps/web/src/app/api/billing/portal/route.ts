import { createClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";
import { getSiteUrl } from "@/src/lib/env";
import { getStripeServerClient } from "@/src/lib/stripe";

type PortalPayload = {
  org_id?: unknown;
};

type OrgBillingCustomerRow = {
  stripe_customer_id: string | null;
};

export async function POST(request: NextRequest) {
  const payload = (await request.json().catch(() => null)) as PortalPayload | null;
  const orgId = typeof payload?.org_id === "string" ? payload.org_id.trim() : "";
  if (!orgId) {
    return NextResponse.json({ message: "Invalid portal payload" }, { status: 400 });
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

  const { data: billingRow, error: billingError } = await supabase
    .from("orgs")
    .select("stripe_customer_id")
    .eq("id", orgId)
    .maybeSingle();
  if (billingError) {
    return NextResponse.json({ message: "Failed to load billing record" }, { status: 502 });
  }

  const stripeCustomerId = (billingRow as OrgBillingCustomerRow | null)?.stripe_customer_id ?? null;
  if (!stripeCustomerId) {
    return NextResponse.json({ message: "No Stripe customer found for this workspace" }, { status: 400 });
  }

  try {
    const stripe = getStripeServerClient();
    const session = await stripe.billingPortal.sessions.create({
      customer: stripeCustomerId,
      return_url: `${siteUrl}/dashboard/settings/billing`,
    });
    return NextResponse.json({ url: session.url }, { status: 200 });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Failed to create Stripe billing portal session";
    return NextResponse.json({ message }, { status: 500 });
  }
}
