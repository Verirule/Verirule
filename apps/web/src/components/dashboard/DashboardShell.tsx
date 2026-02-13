"use client";

import { LogoMark } from "@/src/components/brand/LogoMark";
import { ThemeToggle } from "@/src/components/theme/ThemeToggle";
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
  LayoutTemplate,
  LayoutDashboard,
  ListChecks,
  Menu,
  RadioTower,
  SearchCheck,
  Settings,
  ShieldCheck,
  Workflow,
  Zap,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ComponentType, type ReactNode, useState } from "react";

type NavigationLink = {
  href: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  exact?: boolean;
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
      { href: "/dashboard/alerts", label: "Alerts", icon: Bell },
      { href: "/dashboard/tasks", label: "Tasks", icon: ListChecks },
      { href: "/dashboard/audit", label: "Audit", icon: ClipboardList },
      { href: "/dashboard/exports", label: "Exports", icon: FileOutput },
      { href: "/dashboard/system", label: "System", icon: Activity },
    ],
  },
  {
    title: "Admin",
    links: [
      { href: "/dashboard/settings", label: "Settings", icon: Settings },
      { href: "/dashboard/billing", label: "Billing", icon: CircleDollarSign },
      { href: "/dashboard/settings/automation", label: "Automation", icon: Zap },
      { href: "/dashboard/settings/integrations", label: "Integrations", icon: Workflow },
    ],
  },
];

function isActivePath(pathname: string, link: NavigationLink): boolean {
  if (link.exact) {
    return pathname === link.href;
  }
  return pathname === link.href || pathname.startsWith(`${link.href}/`);
}

function SidebarLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

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
                      ? "font-medium"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground",
                  )}
                  style={
                    isActive
                      ? {
                          backgroundColor: "var(--vr-user-accent)",
                          color: "var(--vr-user-accent-foreground)",
                        }
                      : undefined
                  }
                >
                  <Icon className="h-4 w-4" />
                  <span>{link.label}</span>
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
    <div className="vr-page min-h-screen bg-background">
      <header className="vr-surface sticky top-0 z-40 border-b border-border/60 bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
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
            <Link href="/" className="flex items-center gap-2 font-semibold">
              <LogoMark className="h-6 w-6" />
              <span>Verirule</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <LogoutButton />
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl">
        <aside
          className={cn(
            "vr-surface fixed inset-y-0 left-0 z-30 w-72 border-r border-border/70 bg-background px-4 pb-6 pt-20 transition-transform duration-200 lg:sticky lg:top-14 lg:h-[calc(100vh-3.5rem)] lg:translate-x-0 lg:pt-6",
            mobileSidebarOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Navigation</p>
          <SidebarLinks onNavigate={() => setMobileSidebarOpen(false)} />
        </aside>

        {mobileSidebarOpen ? (
          <button
            type="button"
            aria-label="Close dashboard sidebar"
            className="fixed inset-0 z-20 bg-black/40 lg:hidden"
            onClick={() => setMobileSidebarOpen(false)}
          />
        ) : null}

        <main className="w-full min-w-0 px-4 py-6 sm:px-6">{children}</main>
      </div>
    </div>
  );
}
