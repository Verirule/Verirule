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
    <nav className="sticky top-0 z-50 border-b border-[#C5E4D3] bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-3 font-semibold tracking-tight">
          <LogoMark className="h-7 w-7" />
          <span className="text-[#0B3A27]">Verirule</span>
        </Link>

        <div className="hidden items-center gap-6 text-sm md:flex">
          {sectionLinks.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-[#0D4C2F] transition-colors hover:text-[#006532]"
            >
              {item.label}
            </Link>
          ))}
          <Link href="/dashboard" className="text-[#0D4C2F] transition-colors hover:text-[#006532]">
            Dashboard
          </Link>
          <Link
            href="https://www.linkedin.com/company/verirule-xyz-0684273b0"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#0D4C2F] transition-colors hover:text-[#006532]"
          >
            LinkedIn
          </Link>
          <Link href="/auth/login" className="text-[#0D4C2F] transition-colors hover:text-[#006532]">
            Sign in
          </Link>
          <Button asChild size="sm" className="bg-[#006F34] text-white hover:bg-[#005E31]">
            <Link href="/auth/sign-up">Create account</Link>
          </Button>
        </div>

        <div className="flex items-center gap-2 md:hidden">
          <Button asChild size="sm" variant="outline" className="border-[#9CCCB2] bg-white text-[#0D4C2F] hover:bg-[#EDF7F1]">
            <Link href="/auth/login">Sign in</Link>
          </Button>
          {isOpen ? (
            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-[#9CCCB2]"
              onClick={() => setIsOpen(false)}
              aria-expanded="true"
              aria-controls="mobile-nav-panel"
              aria-label="Toggle navigation menu"
            >
              <span className="sr-only">Menu</span>
              <span className="flex flex-col gap-1.5">
                <span className="block h-0.5 w-4 bg-[#0D4C2F]" />
                <span className="block h-0.5 w-4 bg-[#0D4C2F]" />
                <span className="block h-0.5 w-4 bg-[#0D4C2F]" />
              </span>
            </button>
          ) : (
            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-[#9CCCB2]"
              onClick={() => setIsOpen(true)}
              aria-expanded="false"
              aria-controls="mobile-nav-panel"
              aria-label="Toggle navigation menu"
            >
              <span className="sr-only">Menu</span>
              <span className="flex flex-col gap-1.5">
                <span className="block h-0.5 w-4 bg-[#0D4C2F]" />
                <span className="block h-0.5 w-4 bg-[#0D4C2F]" />
                <span className="block h-0.5 w-4 bg-[#0D4C2F]" />
              </span>
            </button>
          )}
        </div>
      </div>

      {isOpen ? (
        <div id="mobile-nav-panel" className="border-t border-[#C5E4D3] bg-white px-4 py-4 md:hidden">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-3">
            {sectionLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-md px-2 py-1 text-sm text-[#0D4C2F] transition-colors hover:text-[#006532]"
                onClick={() => setIsOpen(false)}
              >
                {item.label}
              </Link>
            ))}
            <Link
              href="/dashboard"
              className="rounded-md px-2 py-1 text-sm text-[#0D4C2F] transition-colors hover:text-[#006532]"
              onClick={() => setIsOpen(false)}
            >
              Dashboard
            </Link>
            <Link
              href="https://www.linkedin.com/company/verirule-xyz-0684273b0"
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md px-2 py-1 text-sm text-[#0D4C2F] transition-colors hover:text-[#006532]"
              onClick={() => setIsOpen(false)}
            >
              LinkedIn
            </Link>
            <Link
              href="/auth/login"
              className="rounded-md px-2 py-1 text-sm text-[#0D4C2F] transition-colors hover:text-[#006532]"
              onClick={() => setIsOpen(false)}
            >
              Sign in
            </Link>
            <Button
              asChild
              className="mt-1 w-full bg-[#006F34] text-white hover:bg-[#005E31]"
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
