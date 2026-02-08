import { Button } from "@/components/ui/button";
import Image from "next/image";
import Link from "next/link";

const howItWorks = [
  {
    title: "Connect your scope",
    description:
      "Define the jurisdictions, frameworks, and products you need to track so alerts stay relevant.",
  },
  {
    title: "Monitor regulatory change",
    description:
      "Verirule continuously watches source updates and flags changes that may impact your obligations.",
  },
  {
    title: "Review and act",
    description:
      "Route structured alerts to owners, keep evidence, and close the loop with an audit-ready history.",
  },
];

const reasons = [
  {
    title: "Signal over noise",
    description: "Prioritized change alerts with clear summaries and impact context for fast triage.",
  },
  {
    title: "Built for accountability",
    description: "Trace decisions with event history, ownership, and status from detection to resolution.",
  },
  {
    title: "Fast onboarding",
    description: "Start with key domains first, then expand coverage as your compliance program matures.",
  },
  {
    title: "API-friendly workflow",
    description: "Integrate alerts into internal tools and ticketing systems without manual copy and paste.",
  },
];

const pricing = [
  {
    name: "Free",
    price: "$0",
    bullets: ["Single workspace", "Core alerts", "Community support"],
  },
  {
    name: "Pro",
    price: "$99/mo",
    bullets: ["Multiple monitored domains", "Advanced alert routing", "Audit log exports"],
  },
  {
    name: "Business",
    price: "Custom",
    bullets: ["Team roles and approvals", "Priority support", "Custom onboarding"],
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <nav className="sticky top-0 z-20 border-b border-border/70 bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-3 font-semibold tracking-tight">
            <Image src="/brand/logo.svg" alt="Verirule logo" width={28} height={28} />
            <span>Verirule</span>
          </Link>
          <div className="flex items-center gap-5 text-sm text-muted-foreground">
            <Link href="#pricing" className="hover:text-foreground transition-colors">
              Pricing
            </Link>
            <Link href="#security" className="hover:text-foreground transition-colors">
              Security
            </Link>
            <Link href="/auth/login" className="hover:text-foreground transition-colors">
              Login
            </Link>
          </div>
        </div>
      </nav>

      <section className="mx-auto w-full max-w-6xl px-4 pb-16 pt-14 sm:px-6 sm:pt-20">
        <div className="rounded-3xl border border-border/80 bg-card p-8 shadow-sm sm:p-12">
          <p className="text-sm font-medium text-muted-foreground">AI compliance monitoring and change alerts</p>
          <h1 className="mt-3 max-w-3xl text-3xl font-bold tracking-tight sm:text-5xl">
            Stay ahead of regulatory change without manual monitoring.
          </h1>
          <p className="mt-5 max-w-2xl text-base text-muted-foreground sm:text-lg">
            Verirule helps teams detect policy updates, assess impact, and track response actions in one workflow.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild>
              <Link href="/auth/sign-up">Get started</Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/auth/login">Sign in</Link>
            </Button>
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">How it works</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {howItWorks.map((item, index) => (
            <article key={item.title} className="rounded-2xl border bg-card p-6">
              <p className="text-xs font-semibold text-muted-foreground">Step {index + 1}</p>
              <h3 className="mt-2 text-lg font-semibold">{item.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Why Verirule</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {reasons.map((item) => (
            <article key={item.title} className="rounded-2xl border bg-card p-6">
              <h3 className="text-lg font-semibold">{item.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="pricing" className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Pricing</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {pricing.map((tier) => (
            <article key={tier.name} className="rounded-2xl border bg-card p-6">
              <h3 className="text-lg font-semibold">{tier.name}</h3>
              <p className="mt-1 text-xl font-bold">{tier.price}</p>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                {tier.bullets.map((bullet) => (
                  <li key={bullet}>- {bullet}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section id="security" className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
        <div className="rounded-2xl border bg-card p-6 sm:p-8">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Security and trust</h2>
          <p className="mt-4 max-w-3xl text-sm text-muted-foreground sm:text-base">
            Verirule is designed with practical controls including row-level security, audit logs, and least-privilege
            access patterns. We focus on transparent controls and reviewable workflows so teams can make informed
            compliance decisions.
          </p>
        </div>
      </section>

      <footer className="mx-auto w-full max-w-6xl border-t border-border/70 px-4 py-8 sm:px-6">
        <div className="flex flex-col gap-3 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <a href="https://discord.gg/" target="_blank" rel="noreferrer" className="hover:text-foreground transition-colors">
              Discord
            </a>
            <a href="https://x.com/verirule" target="_blank" rel="noreferrer" className="hover:text-foreground transition-colors">
              X
            </a>
          </div>
          <p>Copyright 2026 Verirule. All rights reserved.</p>
        </div>
      </footer>
    </main>
  );
}
