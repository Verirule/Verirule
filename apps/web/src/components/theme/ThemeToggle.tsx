"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useMemo, useState } from "react";

type ThemeToggleProps = {
  className?: string;
};

export function ThemeToggle({ className }: ThemeToggleProps) {
  const [mounted, setMounted] = useState(false);
  const { resolvedTheme, setTheme } = useTheme();

  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = useMemo(() => resolvedTheme === "dark", [resolvedTheme]);
  const nextTheme = isDark ? "light" : "dark";

  if (!mounted) {
    return (
      <button
        type="button"
        className={
          className ??
          "inline-flex h-9 items-center rounded-md border border-border px-3 text-xs font-medium text-muted-foreground"
        }
        aria-hidden
      >
        Theme
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setTheme(nextTheme)}
      className={
        className ??
        "inline-flex h-9 items-center gap-2 rounded-md border border-border bg-background px-3 text-xs font-medium text-foreground transition-colors hover:bg-accent"
      }
      aria-label={`Switch to ${nextTheme} theme`}
      title={`Switch to ${nextTheme} theme`}
    >
      {isDark ? <Sun className="h-3.5 w-3.5" aria-hidden /> : <Moon className="h-3.5 w-3.5" aria-hidden />}
      <span>{isDark ? "Light" : "Dark"}</span>
    </button>
  );
}
