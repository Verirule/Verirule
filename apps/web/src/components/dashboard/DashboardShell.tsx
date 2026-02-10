"use client";

import { LogoMark } from "@/src/components/brand/LogoMark";
import { ThemeToggle } from "@/src/components/theme/ThemeToggle";
import { LogoutButton } from "@/components/logout-button";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Bell, ClipboardList, LayoutDashboard, ListChecks, Menu, RadioTower, Settings, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const navigationLinks = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/sources", label: "Sources", icon: RadioTower },
  { href: "/dashboard/alerts", label: "Alerts", icon: Bell },
  { href: "/dashboard/tasks", label: "Tasks", icon: ListChecks },
  { href: "/dashboard/audit", label: "Audit", icon: ClipboardList },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

function SidebarLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav className="mt-6 flex flex-col gap-1">
      {navigationLinks.map((link) => {
        const isActive = pathname === link.href;
        const Icon = link.icon;
        return (
          <Link
            key={link.href}
            href={link.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
              isActive
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-foreground",
            )}
          >
            <Icon className="h-4 w-4" />
            <span>{link.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export function DashboardShell({ children }: { children: React.ReactNode }) {
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
              <LogoMark className="h-6 w-6 text-slate-900 dark:text-white" />
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
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
            Workspace
          </p>
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
