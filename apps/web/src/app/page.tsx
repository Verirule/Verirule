import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Footer } from "@/src/components/landing/Footer";
import { Nav } from "@/src/components/landing/Nav";
import { getPlanDisplayPrice, getPlanIncludedItems, type BillingPlan } from "@/src/lib/billing";

const capabilities = [
  {
    title: "Control Register",
    description: "Define controls, owners, evidence requirements, and review cadence in one place.",
    bullets: ["Control ownership", "Status and due dates", "Framework mapping"],
  },
  {
    title: "Monitoring and Findings",
    description: "Track monitored sources, detect change, and convert findings into action quickly.",
    bullets: ["Source scheduling", "Finding lifecycle", "Severity-driven workflows"],
  },
  {
    title: "Task and Evidence Operations",
    description: "Run remediation tasks with attached evidence so completion is verifiable, not assumed.",
    bullets: ["Task assignments", "Evidence uploads", "SLA reminders"],
  },
  {
    title: "Audit Readiness",
    description: "Generate exports and maintain operational history for external review and internal assurance.",
    bullets: ["Audit timeline", "Export packs", "Readiness snapshots"],
  },
];

const implementationPlan = [
  {
    phase: "Phase 1: Foundation",
    detail: "Set up workspace structure, roles, and baseline controls.",
  },
  {
    phase: "Phase 2: Automation",
    detail: "Enable monitoring, findings, alerts, and task assignment workflows.",
  },
  {
    phase: "Phase 3: Evidence Discipline",
    detail: "Standardize proof collection and resolution criteria across teams.",
  },
  {
    phase: "Phase 4: Audit Execution",
    detail: "Run readiness checks and produce exports on demand.",
  },
];

const outcomes = [
  "Clear accountability for every control and remediation action",
  "Shorter time from finding detection to verified closure",
  "Consistent evidence quality across teams and cycles",
  "Faster audit preparation with less manual reconciliation",
];

const plans: Array<{ plan: BillingPlan; name: string; cta: string; note: string }> = [
  { plan: "free", name: "Free", cta: "Start free", note: "For teams validating the workflow" },
  { plan: "pro", name: "Pro", cta: "Choose Pro", note: "For active compliance operations" },
  { plan: "business", name: "Business", cta: "Choose Business", note: "For multi-team governance at scale" },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <Nav />
      <main>
        <section className="border-b border-gray-200 bg-gradient-to-b from-blue-50 to-white">
          <div className="mx-auto grid w-full max-w-6xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-2 md:items-center md:py-20">
            <div>
              <Badge variant="secondary" className="mb-4">
                Compliance Operations Software
              </Badge>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
                Verirule helps compliance teams run real operations, not spreadsheets.
              </h1>
              <p className="mt-5 max-w-xl text-base leading-7 text-slate-700">
                Build a structured operating system for controls, findings, remediation, and evidence. Keep execution
                transparent for leadership and audit-ready for reviewers.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Button asChild>
                  <Link href="/auth/sign-up">Create workspace</Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href="/auth/login">Sign in</Link>
                </Button>
              </div>
            </div>

            <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-4">
                <span className="inline-flex h-20 w-20 items-center justify-center rounded-xl border border-gray-200 bg-white p-3">
                  <img src="/logo.svg" alt="Verirule logo" className="h-full w-full object-contain" />
                </span>
                <div>
                  <p className="text-lg font-semibold text-slate-900">Operational Clarity</p>
                  <p className="text-sm text-slate-600">One system for daily execution and external assurance.</p>
                </div>
              </div>
              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-gray-200 bg-slate-50 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Governance</p>
                  <p className="mt-1 text-sm text-slate-700">Roles, ownership, and decision history in context.</p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-slate-50 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Execution</p>
                  <p className="mt-1 text-sm text-slate-700">Actionable tasking tied directly to findings.</p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-slate-50 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Evidence</p>
                  <p className="mt-1 text-sm text-slate-700">Proof attached to work, ready for review.</p>
                </div>
                <div className="rounded-lg border border-gray-200 bg-slate-50 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Audit</p>
                  <p className="mt-1 text-sm text-slate-700">Exports and timelines without manual assembly.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="capabilities" className="border-b border-gray-200 bg-white">
          <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">Core Capabilities</h2>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">
              Each capability is designed to reduce operational friction while improving traceability across the full
              compliance lifecycle.
            </p>
            <div className="mt-7 grid gap-4 md:grid-cols-2">
              {capabilities.map((item) => (
                <article key={item.title} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                  <h3 className="text-lg font-semibold text-slate-900">{item.title}</h3>
                  <p className="mt-2 text-sm text-slate-700">{item.description}</p>
                  <ul className="mt-3 space-y-1.5 text-sm text-slate-600">
                    {item.bullets.map((line) => (
                      <li key={line} className="flex items-start gap-2">
                        <span className="mt-1 inline-block h-1.5 w-1.5 rounded-full bg-blue-600" />
                        <span>{line}</span>
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="implementation" className="border-b border-gray-200 bg-slate-50">
          <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
              Recommended Implementation Plan
            </h2>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">
              Start with structure, then automate the high-friction points. This path works well for teams moving from
              ad-hoc compliance tracking to a repeatable operating model.
            </p>
            <ol className="mt-7 grid gap-3 md:grid-cols-2">
              {implementationPlan.map((step, index) => (
                <li key={step.phase} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">
                    Step {index + 1}
                  </p>
                  <p className="mt-1 text-base font-semibold text-slate-900">{step.phase}</p>
                  <p className="mt-1 text-sm text-slate-700">{step.detail}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="outcomes" className="border-b border-gray-200 bg-white">
          <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">Operational Outcomes</h2>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">
              Teams adopting Verirule typically focus on these outcomes to improve control confidence and execution
              speed.
            </p>
            <div className="mt-6 grid gap-3 md:grid-cols-2">
              {outcomes.map((item) => (
                <div key={item} className="flex items-start gap-3 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                  <span className="mt-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full bg-blue-100 text-blue-700">
                    <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="currentColor" aria-hidden="true">
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 0 1 0 1.414l-7.25 7.25a1 1 0 0 1-1.414 0l-3.25-3.25a1 1 0 0 1 1.414-1.414l2.543 2.543 6.543-6.543a1 1 0 0 1 1.414 0Z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </span>
                  <p className="text-sm text-slate-700">{item}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="pricing" className="bg-white">
          <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">Pricing</h2>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">
              Transparent monthly pricing with limits aligned to real product entitlements.
            </p>
            <div className="mt-7 grid gap-4 md:grid-cols-3">
              {plans.map((plan) => (
                <article key={plan.name} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                  <h3 className="text-base font-semibold text-slate-900">{plan.name}</h3>
                  <p className="mt-1 text-xs text-slate-500">{plan.note}</p>
                  <p className="mt-3 text-3xl font-semibold text-slate-900">
                    {getPlanDisplayPrice(plan.plan)}
                    <span className="ml-1 text-sm font-medium text-slate-500">/mo</span>
                  </p>
                  <ul className="mt-3 space-y-1 text-sm text-slate-600">
                    {getPlanIncludedItems(plan.plan).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                  <Button asChild className="mt-5 w-full">
                    <Link href="/auth/sign-up">{plan.cta}</Link>
                  </Button>
                </article>
              ))}
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
