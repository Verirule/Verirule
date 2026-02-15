"use client";

import { Button } from "@/components/ui/button";
import Link from "next/link";
import { useState } from "react";

const sectionLinks = [
  { href: "#capabilities", label: "Capabilities" },
  { href: "#implementation", label: "Implementation" },
  { href: "#outcomes", label: "Outcomes" },
  { href: "#pricing", label: "Pricing" },
];

export function Nav() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 border-b border-gray-200 bg-white">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-3 text-slate-900">
          <span className="inline-flex h-14 w-14 items-center justify-center rounded-lg border border-gray-200 bg-white p-2">
            <img src="/logo.svg" alt="Verirule" className="h-full w-full object-contain" />
          </span>
          <span className="text-xl font-semibold">Verirule</span>
        </Link>

        <div className="hidden items-center gap-6 text-sm md:flex">
          {sectionLinks.map((item) => (
            <Link key={item.href} href={item.href} className="font-medium text-slate-700 hover:text-blue-700">
              {item.label}
            </Link>
          ))}
          <Link href="/auth/login" className="font-medium text-slate-700 hover:text-blue-700">
            Sign in
          </Link>
          <Button asChild size="sm">
            <Link href="/auth/sign-up">Create account</Link>
          </Button>
        </div>

        <div className="flex items-center gap-2 md:hidden">
          <Button asChild size="sm" variant="outline">
            <Link href="/auth/login">Sign in</Link>
          </Button>
          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gray-300 text-slate-700"
            onClick={() => setIsOpen((current) => !current)}
            aria-expanded={isOpen}
            aria-controls="mobile-nav-panel"
            aria-label="Toggle navigation menu"
          >
            <span className="flex flex-col gap-1.5">
              <span className="block h-0.5 w-4 bg-slate-700" />
              <span className="block h-0.5 w-4 bg-slate-700" />
              <span className="block h-0.5 w-4 bg-slate-700" />
            </span>
          </button>
        </div>
      </div>

      {isOpen ? (
        <div id="mobile-nav-panel" className="border-t border-gray-200 bg-white px-4 py-4 md:hidden">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-2">
            {sectionLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-md px-2 py-1.5 text-sm font-medium text-slate-700 hover:bg-blue-50 hover:text-blue-700"
                onClick={() => setIsOpen(false)}
              >
                {item.label}
              </Link>
            ))}
            <Button asChild className="mt-1 w-full" onClick={() => setIsOpen(false)}>
              <Link href="/auth/sign-up">Create account</Link>
            </Button>
          </div>
        </div>
      ) : null}
    </nav>
  );
}
