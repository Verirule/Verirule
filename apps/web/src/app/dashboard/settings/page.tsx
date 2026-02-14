import Link from "next/link";

import { AccentThemePicker } from "@/src/components/theme/AccentThemePicker";

export default function DashboardSettingsPage() {
  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-border/70 bg-card p-6 shadow-sm">
        <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Manage workspace controls, personal preferences, and legal references.
        </p>
      </section>

      <AccentThemePicker />

      <section className="rounded-xl border border-border/70 bg-card p-6 shadow-sm">
        <h2 className="text-lg font-semibold tracking-tight">Billing</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Manage subscription plan, checkout, and self-serve billing portal access.
        </p>
        <Link
          href="/dashboard/billing"
          className="mt-4 inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium transition-colors hover:bg-accent"
        >
          Open Billing
        </Link>
      </section>

      <section className="rounded-xl border border-border/70 bg-card p-6 shadow-sm">
        <h2 className="text-lg font-semibold tracking-tight">Members</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Manage workspace membership roles, delegated admin access, and invitation workflows.
        </p>
        <Link
          href="/dashboard/settings/members"
          className="mt-4 inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium transition-colors hover:bg-accent"
        >
          Open Members
        </Link>
      </section>

      <section className="rounded-xl border border-border/70 bg-card p-6 shadow-sm">
        <h2 className="text-lg font-semibold tracking-tight">Automation</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Configure alert-to-task automation rules, severity thresholds, and checklist behavior.
        </p>
        <Link
          href="/dashboard/settings/automation"
          className="mt-4 inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium transition-colors hover:bg-accent"
        >
          Open Automation
        </Link>
      </section>

      <section className="rounded-xl border border-border/70 bg-card p-6 shadow-sm">
        <h2 className="text-lg font-semibold tracking-tight">Integrations</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Configure outgoing connectors such as Slack and Jira for routing and escalation workflows.
        </p>
        <Link
          href="/dashboard/settings/integrations"
          className="mt-4 inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium transition-colors hover:bg-accent"
        >
          Open Integrations
        </Link>
      </section>

      <section className="rounded-xl border border-border/70 bg-card p-6 shadow-sm">
        <h2 className="text-lg font-semibold tracking-tight">Legal</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Review Verirule legal terms and policies.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            href="/privacy"
            className="inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium transition-colors hover:bg-accent"
          >
            Privacy
          </Link>
          <Link
            href="/policy"
            className="inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium transition-colors hover:bg-accent"
          >
            Policy
          </Link>
          <Link
            href="/terms"
            className="inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium transition-colors hover:bg-accent"
          >
            Terms
          </Link>
          <Link
            href="/service"
            className="inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium transition-colors hover:bg-accent"
          >
            Service
          </Link>
        </div>
      </section>
    </div>
  );
}
