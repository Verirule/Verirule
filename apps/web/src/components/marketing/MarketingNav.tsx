"use client";

import Link from "next/link";
import { useState } from "react";

const navLinks = [
  { href: "#product", label: "Product" },
  { href: "#pricing", label: "Pricing" },
  { href: "#security", label: "Security" },
  { href: "#resources", label: "Resources" },
] as const;

export function MarketingNav() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-[#233656] bg-[#0a1424]">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="inline-flex items-center gap-3 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]">
          <img src="/logo.svg" alt="Verirule" className="h-8 w-auto" />
        </Link>

        <nav aria-label="Primary" className="hidden items-center gap-7 md:flex">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-[#d4def2] transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]"
            >
              {link.label}
            </a>
          ))}
          <Link
            href="/auth/login"
            className="text-sm font-medium text-[#d4def2] transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]"
          >
            Sign in
          </Link>
          <Link
            href="/auth/sign-up"
            className="rounded-md bg-[#3e6ef4] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#2f5dd9] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]"
          >
            Get started
          </Link>
        </nav>

        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-[#35507a] text-[#d4def2] md:hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]"
          onClick={() => setIsOpen((value) => !value)}
          aria-expanded={isOpen}
          aria-controls="mobile-nav"
          aria-label="Toggle navigation"
        >
          <span className="flex flex-col gap-1.5">
            <span className="h-0.5 w-4 bg-current" />
            <span className="h-0.5 w-4 bg-current" />
            <span className="h-0.5 w-4 bg-current" />
          </span>
        </button>
      </div>

      {isOpen ? (
        <nav id="mobile-nav" aria-label="Mobile" className="border-t border-[#233656] px-4 py-4 md:hidden">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-3">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setIsOpen(false)}
                className="rounded-md px-2 py-1 text-sm font-medium text-[#d4def2] transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]"
              >
                {link.label}
              </a>
            ))}
            <Link
              href="/auth/login"
              onClick={() => setIsOpen(false)}
              className="rounded-md px-2 py-1 text-sm font-medium text-[#d4def2] transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]"
            >
              Sign in
            </Link>
            <Link
              href="/auth/sign-up"
              onClick={() => setIsOpen(false)}
              className="rounded-md bg-[#3e6ef4] px-4 py-2 text-center text-sm font-semibold text-white transition-colors hover:bg-[#2f5dd9] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]"
            >
              Get started
            </Link>
          </div>
        </nav>
      ) : null}
    </header>
  );
}
