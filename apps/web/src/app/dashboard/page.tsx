import { createClient } from "@/lib/supabase/server";
import { OrgsPanel } from "@/src/components/dashboard/OrgsPanel";
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
      <OrgsPanel />
    </div>
  );
}
