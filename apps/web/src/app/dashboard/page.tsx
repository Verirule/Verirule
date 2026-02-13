import { createClient } from "@/lib/supabase/server";
import { OrgsPanel } from "@/src/components/dashboard/OrgsPanel";
import { ReadinessCard } from "@/src/components/dashboard/ReadinessCard";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { redirect } from "next/navigation";
import { connection } from "next/server";

export default async function DashboardPage() {
  await connection();

  const supabase = await createClient();
  const { data, error } = await supabase.auth.getSession();

  if (error || !data.session) {
    redirect("/auth/login");
  }

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage organization workspaces and onboarding from a single secure view.
        </p>
      </section>
      {process.env.VERIRULE_ENABLE_DEBUG_PAGES === "true" ? (
        <section className="rounded-lg border border-border/70 bg-card p-4">
          <h2 className="text-base font-semibold">Setup Control Center</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Validate Supabase, OAuth, Stripe billing, and API wiring.
          </p>
          <div className="mt-3">
            <Button asChild variant="outline" size="sm">
              <Link href="/dashboard/setup">Open setup checks</Link>
            </Button>
          </div>
        </section>
      ) : null}
      <ReadinessCard />
      <OrgsPanel />
    </div>
  );
}
