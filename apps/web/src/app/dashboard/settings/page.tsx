import Link from "next/link";

export default function DashboardSettingsPage() {
  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-border/70 bg-card p-6 shadow-sm">
        <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Workspace settings and team preferences.
        </p>
      </section>
      <section className="rounded-xl border border-border/70 bg-card p-6 shadow-sm">
        <h2 className="text-lg font-semibold tracking-tight">Integrations</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Configure outgoing connectors such as Slack for alert routing.
        </p>
        <Link
          href="/dashboard/settings/integrations"
          className="mt-4 inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium"
        >
          Open Integrations
        </Link>
      </section>
    </div>
  );
}
