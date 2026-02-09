import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export async function DashboardAuthGate({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getSession();

  if (error || !data.session) {
    redirect("/auth/login");
  }

  return <>{children}</>;
}
