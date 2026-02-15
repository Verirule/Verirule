"use client";

import { LogoutButton } from "@/components/logout-button";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Activity,
  Bell,
  CircleDollarSign,
  ClipboardList,
  FileOutput,
  FlaskConical,
  Gauge,
  Inbox,
  LayoutTemplate,
  LayoutDashboard,
  ListChecks,
  Menu,
  RadioTower,
  SearchCheck,
  Settings,
  ShieldCheck,
  Users,
  Workflow,
  Zap,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { type ComponentType, type ReactNode, useEffect, useState } from "react";

type NavigationLink = {
  href: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  exact?: boolean;
  aliases?: string[];
};

type NavigationSection = {
  title: string;
  links: NavigationLink[];
};

const navigationSections: NavigationSection[] = [
  {
    title: "Workspace",
    links: [
      { href: "/dashboard", label: "Overview", icon: LayoutDashboard, exact: true },
      { href: "/dashboard/sources", label: "Sources", icon: RadioTower },
      { href: "/dashboard/templates", label: "Templates", icon: LayoutTemplate },
      { href: "/dashboard/research", label: "Research", icon: FlaskConical },
    ],
  },
  {
    title: "Operations",
    links: [
      { href: "/dashboard/findings", label: "Findings", icon: SearchCheck },
      { href: "/dashboard/controls", label: "Controls", icon: ShieldCheck },
      { href: "/dashboard/readiness", label: "Readiness", icon: Gauge },
      { href: "/dashboard/alerts", label: "Alerts", icon: Bell },
      { href: "/dashboard/inbox", label: "Inbox", icon: Inbox },
      { href: "/dashboard/tasks", label: "Tasks", icon: ListChecks },
      { href: "/dashboard/audit", label: "Audit", icon: ClipboardList },
      { href: "/dashboard/exports", label: "Exports", icon: FileOutput },
    ],
  },
  {
    title: "Settings",
    links: [
      { href: "/dashboard/settings", label: "Settings Home", icon: Settings },
      {
        href: "/dashboard/settings/billing",
        label: "Billing",
        icon: CircleDollarSign,
        aliases: ["/dashboard/billing"],
      },
      { href: "/dashboard/settings/members", label: "Members", icon: Users },
      { href: "/dashboard/settings/notifications", label: "Notifications", icon: Bell },
      { href: "/dashboard/settings/automation", label: "Automation", icon: Zap },
      { href: "/dashboard/settings/integrations", label: "Integrations", icon: Workflow },
      { href: "/dashboard/system", label: "System", icon: Activity },
    ],
  },
];

function isActivePath(pathname: string, link: NavigationLink): boolean {
  if (link.exact) {
    return pathname === link.href;
  }
  if (Array.isArray(link.aliases) && link.aliases.some((alias) => pathname === alias || pathname.startsWith(`${alias}/`))) {
    return true;
  }
  return pathname === link.href || pathname.startsWith(`${link.href}/`);
}

function SidebarLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const requestedOrgId = searchParams.get("org_id")?.trim() ?? "";
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const loadUnreadCount = async () => {
      try {
        const orgsResponse = await fetch("/api/orgs", { method: "GET", cache: "no-store" });
        if (!orgsResponse.ok) {
          if (!cancelled) {
            setUnreadCount(0);
          }
          return;
        }
        const orgBody = (await orgsResponse.json().catch(() => ({}))) as { orgs?: unknown };
        const orgRows = Array.isArray(orgBody.orgs)
          ? orgBody.orgs.filter((row): row is { id: string } => {
              if (!row || typeof row !== "object") {
                return false;
              }
              const org = row as Record<string, unknown>;
              return typeof org.id === "string";
            })
          : [];
        if (!orgRows.length) {
          if (!cancelled) {
            setUnreadCount(0);
          }
          return;
        }

        const selectedOrgId = orgRows.some((org) => org.id === requestedOrgId)
          ? requestedOrgId
          : orgRows[0].id;
        const inboxResponse = await fetch(
          `/api/orgs/${encodeURIComponent(selectedOrgId)}/notifications/inbox?limit=50`,
          {
            method: "GET",
            cache: "no-store",
          },
        );
        if (!inboxResponse.ok) {
          if (!cancelled) {
            setUnreadCount(0);
          }
          return;
        }
        const inboxBody = (await inboxResponse.json().catch(() => ({}))) as { events?: unknown };
        const events = Array.isArray(inboxBody.events)
          ? inboxBody.events.filter((row): row is { is_read?: unknown } => row !== null && typeof row === "object")
          : [];
        const unread = events.filter((event) => event.is_read !== true).length;
        if (!cancelled) {
          setUnreadCount(unread);
        }
      } catch {
        if (!cancelled) {
          setUnreadCount(0);
        }
      }
    };

    void loadUnreadCount();
    const intervalId = setInterval(() => {
      void loadUnreadCount();
    }, 45_000);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, [pathname, requestedOrgId]);

  return (
    <nav className="mt-6 space-y-5">
      {navigationSections.map((section) => (
        <div key={section.title}>
          <p className="mb-2 px-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">{section.title}</p>
          <div className="flex flex-col gap-1">
            {section.links.map((link) => {
              const isActive = isActivePath(pathname, link);
              const Icon = link.icon;

              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={onNavigate}
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
                    isActive
                      ? "bg-blue-600 font-medium text-white"
                      : "text-slate-600 hover:bg-blue-50 hover:text-slate-900",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span>{link.label}</span>
                  {link.href === "/dashboard/inbox" && unreadCount > 0 ? (
                    <span className="ml-auto rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                      {Math.min(unreadCount, 99)}
                    </span>
                  ) : null}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

export function DashboardShell({ children }: { children: ReactNode }) {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  return (
    <div className="vr-page min-h-screen bg-white">
      <header className="vr-surface sticky top-0 z-40 border-b border-gray-200 bg-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="lg:hidden"
              onClick={() => setMobileSidebarOpen((current) => !current)}
              aria-label="Toggle dashboard sidebar"
            >
              {mobileSidebarOpen ? <X /> : <Menu />}
            </Button>
            <Link href="/" className="flex items-center gap-3 font-semibold text-slate-900">
              <span className="vr-brand-chip h-11 w-11">
                <img src="/logo.svg" alt="Verirule" className="h-full w-full object-contain" />
              </span>
              <span className="text-xl font-bold tracking-tight">Verirule</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <LogoutButton />
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl">
        <aside
          className={cn(
            "vr-surface fixed inset-y-0 left-0 z-30 w-72 border-r border-gray-200 bg-white px-4 pb-6 pt-20 transition-transform duration-200 lg:sticky lg:top-16 lg:h-[calc(100vh-4rem)] lg:translate-x-0 lg:pt-6",
            mobileSidebarOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Navigation</p>
          <SidebarLinks onNavigate={() => setMobileSidebarOpen(false)} />
        </aside>

        {mobileSidebarOpen ? (
          <button
            type="button"
            aria-label="Close dashboard sidebar"
            className="fixed inset-0 z-20 bg-slate-900/20 lg:hidden"
            onClick={() => setMobileSidebarOpen(false)}
          />
        ) : null}

        <main className="w-full min-w-0 px-4 py-6 sm:px-6">{children}</main>
      </div>
    </div>
  );
}
