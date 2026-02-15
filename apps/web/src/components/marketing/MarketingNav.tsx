"use client";

import Image from "next/image";
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
    <header className="sticky top-0 z-50 border-b border-[#2E7DB5] bg-[#082E4E]/95 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link
          href="/"
          className="inline-flex items-center gap-3 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#DEAD2D]"
        >
          <span className="vr-brand-chip h-12 w-12 sm:h-14 sm:w-14">
            <Image
              src="/logo.svg"
              alt="Verirule"
              width={320}
              height={84}
              className="h-full w-full object-contain"
              priority
            />
          </span>
        </Link>

        <nav aria-label="Primary" className="hidden items-center gap-7 md:flex">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-[#D7ECFF] transition-colors hover:text-[#DEAD2D] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#DEAD2D]"
            >
              {link.label}
            </a>
          ))}
          <Link
            href="/auth/login"
            className="text-sm font-medium text-[#D7ECFF] transition-colors hover:text-[#DEAD2D] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#DEAD2D]"
          >
            Sign in
          </Link>
          <Link
            href="/auth/sign-up"
            className="rounded-md bg-[#4BAD2E] px-4 py-2 text-sm font-semibold text-[#062A45] transition-colors hover:bg-[#59C239] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#DEAD2D]"
          >
            Get started
          </Link>
        </nav>

        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-[#2E7DB5] text-[#D7ECFF] md:hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#DEAD2D]"
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
        <nav id="mobile-nav" aria-label="Mobile" className="border-t border-[#2E7DB5] px-4 py-4 md:hidden">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-3">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setIsOpen(false)}
                className="rounded-md px-2 py-1 text-sm font-medium text-[#D7ECFF] transition-colors hover:text-[#DEAD2D] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#DEAD2D]"
              >
                {link.label}
              </a>
            ))}
            <Link
              href="/auth/login"
              onClick={() => setIsOpen(false)}
              className="rounded-md px-2 py-1 text-sm font-medium text-[#D7ECFF] transition-colors hover:text-[#DEAD2D] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#DEAD2D]"
            >
              Sign in
            </Link>
            <Link
              href="/auth/sign-up"
              onClick={() => setIsOpen(false)}
              className="rounded-md bg-[#4BAD2E] px-4 py-2 text-center text-sm font-semibold text-[#062A45] transition-colors hover:bg-[#59C239] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#DEAD2D]"
            >
              Get started
            </Link>
          </div>
        </nav>
      ) : null}
    </header>
  );
}
