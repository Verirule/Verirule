import { SetupControlCenter } from "@/src/components/dashboard/SetupControlCenter";
import { notFound } from "next/navigation";

export default function DashboardSetupPage() {
  if (process.env.VERIRULE_ENABLE_DEBUG_PAGES !== "true") {
    notFound();
  }

  return <SetupControlCenter />;
}
