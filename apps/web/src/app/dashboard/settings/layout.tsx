"use client";

import { cn } from "@/lib/utils";
import {
  Bell,
  CircleDollarSign,
  Home,
  Settings,
  Users,
  Workflow,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

type SettingsLink = {
  href: string;
  label: string;
  icon: typeof Home;
  exact?: boolean;
};

const settingsLinks: SettingsLink[] = [
  { href: "/dashboard/settings", label: "Overview", icon: Home, exact: true },
  { href: "/dashboard/settings/billing", label: "Billing", icon: CircleDollarSign },
  { href: "/dashboard/settings/members", label: "Members", icon: Users },
  { href: "/dashboard/settings/notifications", label: "Notifications", icon: Bell },
  { href: "/dashboard/settings/integrations", label: "Integrations", icon: Workflow },
  { href: "/dashboard/settings/automation", label: "Automation", icon: Zap },
] as const;

function isActive(pathname: string, href: string, exact?: boolean): boolean {
  if (exact) {
    return pathname === href;
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function DashboardSettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-border/70 bg-card p-4 shadow-sm">
        <div className="mb-3 flex items-center gap-2">
          <Settings className="h-4 w-4 text-primary" />
          <p className="text-sm font-semibold">Settings Navigation</p>
        </div>
        <nav className="flex gap-2 overflow-x-auto pb-1">
          {settingsLinks.map((link) => {
            const Icon = link.icon;
            const active = isActive(pathname, link.href, link.exact);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "inline-flex h-9 items-center gap-2 whitespace-nowrap rounded-md border px-3 text-sm transition-colors",
                  active
                    ? "border-transparent text-[var(--vr-user-accent-foreground)]"
                    : "border-input hover:bg-accent",
                )}
                style={
                  active
                    ? {
                        backgroundColor: "var(--vr-user-accent)",
                      }
                    : undefined
                }
              >
                <Icon className="h-4 w-4" />
                {link.label}
              </Link>
            );
          })}
        </nav>
      </section>
      {children}
    </div>
  );
}
