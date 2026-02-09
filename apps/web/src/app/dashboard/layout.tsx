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
        {children}
      </Suspense>
    </DashboardShell>
  );
}
