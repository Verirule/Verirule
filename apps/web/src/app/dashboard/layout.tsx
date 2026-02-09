import { DashboardAuthGate } from "@/src/components/dashboard/DashboardAuthGate";
import { DashboardShell } from "@/src/components/dashboard/DashboardShell";
import { Suspense } from "react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <DashboardShell>
      <Suspense fallback={<p className="text-sm text-muted-foreground">Loading dashboard...</p>}>
        <DashboardAuthGate>{children}</DashboardAuthGate>
      </Suspense>
    </DashboardShell>
  );
}
