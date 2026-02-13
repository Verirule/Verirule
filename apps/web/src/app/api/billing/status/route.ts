import { createClient } from "@/lib/supabase/server";
import { NextRequest, NextResponse } from "next/server";
import type { BillingPlan } from "@/src/lib/billing";

type BillingRow = {
  plan: BillingPlan;
  plan_status: string | null;
  current_period_end: string | null;
};

export async function GET(request: NextRequest) {
  const orgId = request.nextUrl.searchParams.get("org_id")?.trim() ?? "";
  if (!orgId) {
    return NextResponse.json({ message: "org_id is required" }, { status: 400 });
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
    .select("plan, plan_status, current_period_end")
    .eq("id", orgId)
    .maybeSingle();

  if (billingError) {
    return NextResponse.json({ message: "Failed to load billing status" }, { status: 502 });
  }

  return NextResponse.json(
    {
      plan: (billingRow as BillingRow | null)?.plan ?? "free",
      status: (billingRow as BillingRow | null)?.plan_status ?? "active",
      current_period_end: (billingRow as BillingRow | null)?.current_period_end ?? null,
    },
    { status: 200 },
  );
}
