import Link from "next/link";
import {
  Bell,
  CircleDollarSign,
  FileText,
  Palette,
  Shield,
  Users,
  Workflow,
  Zap,
} from "lucide-react";

import { AccentThemePicker } from "@/src/components/theme/AccentThemePicker";

export default function DashboardSettingsPage() {
  const workspaceTools = [
    {
      href: "/dashboard/settings/billing",
      title: "Billing",
      description: "Plans, checkout, invoices, and self-serve billing portal access.",
      icon: CircleDollarSign,
    },
    {
      href: "/dashboard/settings/members",
      title: "Members",
      description: "Workspace access, role delegation, and invite lifecycle controls.",
      icon: Users,
    },
    {
      href: "/dashboard/settings/notifications",
      title: "Notifications",
      description: "Org routing rules and personal email preference management.",
      icon: Bell,
    },
    {
      href: "/dashboard/settings/automation",
      title: "Automation",
      description: "Alert-to-task rules, severity thresholds, and evidence checklist defaults.",
      icon: Zap,
    },
    {
      href: "/dashboard/settings/integrations",
      title: "Integrations",
      description: "Slack and Jira connectors for escalation and execution workflows.",
      icon: Workflow,
    },
  ] as const;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-border/70 bg-card p-6 shadow-sm">
        <h1 className="text-xl font-semibold tracking-tight">Settings Center</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Clear entry points for billing, access, notifications, automation, and integrations.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {workspaceTools.map((tool) => {
          const Icon = tool.icon;
          return (
            <Link
              key={tool.href}
              href={tool.href}
              className="rounded-xl border border-border/70 bg-card p-5 shadow-sm transition-colors hover:bg-accent"
            >
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4 text-primary" />
                <h2 className="text-base font-semibold tracking-tight">{tool.title}</h2>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{tool.description}</p>
            </Link>
          );
        })}
      </section>

      <section className="rounded-xl border border-border/70 bg-card p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <Palette className="h-4 w-4 text-primary" />
          <h2 className="text-lg font-semibold tracking-tight">Appearance</h2>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          Personalize accent preferences without changing shared workspace data.
        </p>
      </section>
      <AccentThemePicker />

      <section className="rounded-xl border border-border/70 bg-card p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-primary" />
          <h2 className="text-lg font-semibold tracking-tight">Legal</h2>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          Review Verirule legal terms and policies.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            href="/privacy"
            className="inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium transition-colors hover:bg-accent"
          >
            <FileText className="mr-2 h-4 w-4" />
            Privacy
          </Link>
          <Link
            href="/policy"
            className="inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium transition-colors hover:bg-accent"
          >
            <FileText className="mr-2 h-4 w-4" />
            Policy
          </Link>
          <Link
            href="/terms"
            className="inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium transition-colors hover:bg-accent"
          >
            <FileText className="mr-2 h-4 w-4" />
            Terms
          </Link>
          <Link
            href="/service"
            className="inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium transition-colors hover:bg-accent"
          >
            <FileText className="mr-2 h-4 w-4" />
            Service
          </Link>
        </div>
      </section>
    </div>
  );
}
