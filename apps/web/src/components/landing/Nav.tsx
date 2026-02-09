"use client";

import { Button } from "@/components/ui/button";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

const sectionLinks = [
  { href: "#how", label: "How it works" },
  { href: "#features", label: "Features" },
  { href: "#pricing", label: "Pricing" },
  { href: "#security", label: "Security" },
  { href: "#faq", label: "FAQ" },
];

export function Nav() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 border-b border-border/60 bg-background/90 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-3 font-semibold tracking-tight">
          <Image src="/brand/logo.svg" alt="Verirule logo" width={28} height={28} />
          <span>Verirule</span>
        </Link>

        <div className="hidden items-center gap-6 text-sm md:flex">
          {sectionLinks.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-muted-foreground transition-colors hover:text-foreground"
            >
              {item.label}
            </Link>
          ))}
          <Link href="/auth/login" className="text-muted-foreground transition-colors hover:text-foreground">
            Login
          </Link>
          <Button asChild size="sm">
            <Link href="/auth/sign-up">Get started</Link>
          </Button>
        </div>

        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-border md:hidden"
          onClick={() => setIsOpen((value) => !value)}
          aria-expanded={isOpen}
          aria-controls="mobile-nav-panel"
          aria-label="Toggle navigation menu"
        >
          <span className="sr-only">Menu</span>
          <span className="flex flex-col gap-1.5">
            <span className="block h-0.5 w-4 bg-foreground" />
            <span className="block h-0.5 w-4 bg-foreground" />
            <span className="block h-0.5 w-4 bg-foreground" />
          </span>
        </button>
      </div>

      {isOpen ? (
        <div id="mobile-nav-panel" className="border-t border-border/60 bg-background px-4 py-4 md:hidden">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-3">
            {sectionLinks.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-md px-2 py-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
                onClick={() => setIsOpen(false)}
              >
                {item.label}
              </Link>
            ))}
            <Link
              href="/auth/login"
              className="rounded-md px-2 py-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
              onClick={() => setIsOpen(false)}
            >
              Login
            </Link>
            <Button asChild className="mt-1 w-full" onClick={() => setIsOpen(false)}>
              <Link href="/auth/sign-up">Get started</Link>
            </Button>
          </div>
        </div>
      ) : null}
    </nav>
  );
}
