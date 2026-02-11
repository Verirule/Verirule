"use client";

import { LogoMark } from "@/src/components/brand/LogoMark";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { useState } from "react";

const sectionLinks = [
  { href: "#problem", label: "Problem" },
  { href: "#components", label: "System Components" },
  { href: "#audit-ready", label: "Audit-Ready" },
  { href: "#integrations", label: "Integrations" },
  { href: "#who-its-for", label: "Who It's For" },
];

export function Nav() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-800/80 bg-[#0A1527]/95 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-3 font-semibold tracking-tight">
          <LogoMark className="h-7 w-7 text-slate-200" />
          <span className="text-slate-100">Verirule</span>
        </Link>

        <div className="hidden items-center gap-6 text-sm md:flex">
          {sectionLinks.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-slate-300 transition-colors hover:text-white"
            >
              {item.label}
            </Link>
          ))}
          <Link href="/dashboard" className="text-slate-300 transition-colors hover:text-white">
            Dashboard
          </Link>
          <Link href="/auth/login" className="text-slate-300 transition-colors hover:text-white">
            Sign in
          </Link>
          <Button asChild size="sm" className="bg-slate-100 text-slate-950 hover:bg-white">
            <Link href="/auth/sign-up">Create account</Link>
          </Button>
        </div>

        <div className="flex items-center gap-2 md:hidden">
          <Button asChild size="sm" variant="outline" className="border-slate-700 bg-transparent text-slate-200">
            <Link href="/auth/login">Sign in</Link>
          </Button>
          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-700"
            onClick={() => setIsOpen((value) => !value)}
            aria-expanded={isOpen}
            aria-controls="mobile-nav-panel"
            aria-label="Toggle navigation menu"
          >
            <span className="sr-only">Menu</span>
            <span className="flex flex-col gap-1.5">
              <span className="block h-0.5 w-4 bg-slate-200" />
              <span className="block h-0.5 w-4 bg-slate-200" />
              <span className="block h-0.5 w-4 bg-slate-200" />
            </span>
          </button>
        </div>
      </div>

      {isOpen ? (
        <div id="mobile-nav-panel" className="border-t border-slate-800/80 bg-[#0A1527] px-4 py-4 md:hidden">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-3">
            {sectionLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-md px-2 py-1 text-sm text-slate-300 transition-colors hover:text-white"
                onClick={() => setIsOpen(false)}
              >
                {item.label}
              </Link>
            ))}
            <Link
              href="/dashboard"
              className="rounded-md px-2 py-1 text-sm text-slate-300 transition-colors hover:text-white"
              onClick={() => setIsOpen(false)}
            >
              Dashboard
            </Link>
            <Link
              href="/auth/login"
              className="rounded-md px-2 py-1 text-sm text-slate-300 transition-colors hover:text-white"
              onClick={() => setIsOpen(false)}
            >
              Sign in
            </Link>
            <Button
              asChild
              className="mt-1 w-full bg-slate-100 text-slate-950 hover:bg-white"
              onClick={() => setIsOpen(false)}
            >
              <Link href="/auth/sign-up">Create account</Link>
            </Button>
          </div>
        </div>
      ) : null}
    </nav>
  );
}
