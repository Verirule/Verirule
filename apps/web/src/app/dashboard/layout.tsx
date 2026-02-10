import { DashboardAuthGate } from "@/src/components/dashboard/DashboardAuthGate";
import { DashboardShell } from "@/src/components/dashboard/DashboardShell";
import { Suspense } from "react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Suspense fallback={<p className="px-4 py-6 text-sm text-muted-foreground">Loading dashboard...</p>}>
      <DashboardShell>
        <DashboardAuthGate>{children}</DashboardAuthGate>
      </DashboardShell>
    </Suspense>
  );
}
