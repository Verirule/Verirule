import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Footer } from "@/src/components/landing/Footer";
import { Nav } from "@/src/components/landing/Nav";
import { getPlanDisplayPrice, getPlanIncludedItems, type BillingPlan } from "@/src/lib/billing";
import Link from "next/link";

const platformHighlights = [
  {
    title: "Control Tracking",
    description: "Map controls to evidence tasks, owners, and due dates in one workspace.",
  },
  {
    title: "Continuous Monitoring",
    description: "Monitor sources and route findings into operational workflows.",
  },
  {
    title: "Audit Evidence",
    description: "Store activity history, task proof, and exports for reviews and audits.",
  },
];

const workflowSteps = [
  "Create or import workspace controls",
  "Route findings to owners and due dates",
  "Collect evidence and monitor status",
  "Export audit-ready history and reports",
];

const plans: Array<{ plan: BillingPlan; name: string; cta: string }> = [
  { plan: "free", name: "Free", cta: "Start free" },
  { plan: "pro", name: "Pro", cta: "Choose Pro" },
  { plan: "business", name: "Business", cta: "Choose Business" },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <Nav />
      <main>
        <section className="border-b border-gray-200 bg-white">
          <div className="mx-auto grid w-full max-w-6xl gap-8 px-4 py-14 sm:px-6 md:grid-cols-2 md:items-center md:py-20">
            <div>
              <Badge variant="secondary" className="mb-4">
                Compliance Operations Platform
              </Badge>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
                Keep compliance work organized, visible, and audit-ready.
              </h1>
              <p className="mt-4 max-w-xl text-base text-slate-600">
                Verirule centralizes controls, findings, readiness tracking, and evidence workflows for teams that need
                dependable execution.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Button asChild>
                  <Link href="/auth/sign-up">Create account</Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href="/auth/login">Sign in</Link>
                </Button>
              </div>
            </div>
            <div className="rounded-xl border border-gray-200 bg-slate-50 p-5 shadow-sm">
              <div className="rounded-lg border border-gray-200 bg-white p-4">
                <div className="mb-3 flex items-center gap-3">
                  <span className="inline-flex h-12 w-12 items-center justify-center rounded-md border border-gray-200 bg-white p-2">
                    <img src="/logo.svg" alt="Verirule logo" className="h-full w-full object-contain" />
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">Workspace Health</p>
                    <p className="text-xs text-slate-500">Operational status snapshot</p>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center text-sm">
                  <div className="rounded-md border border-gray-200 bg-white p-3">
                    <p className="text-lg font-semibold text-blue-700">24</p>
                    <p className="text-xs text-slate-500">Controls</p>
                  </div>
                  <div className="rounded-md border border-gray-200 bg-white p-3">
                    <p className="text-lg font-semibold text-blue-700">7</p>
                    <p className="text-xs text-slate-500">Open Tasks</p>
                  </div>
                  <div className="rounded-md border border-gray-200 bg-white p-3">
                    <p className="text-lg font-semibold text-blue-700">92%</p>
                    <p className="text-xs text-slate-500">Readiness</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="platform" className="border-b border-gray-200 bg-white">
          <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Platform</h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              A practical operating layer for controls, findings, and evidence work.
            </p>
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              {platformHighlights.map((item) => (
                <article key={item.title} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                  <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-md bg-blue-50 text-blue-700">
                    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true" fill="none" stroke="currentColor">
                      <path d="M4 7h16M4 12h16M4 17h10" strokeWidth="1.8" strokeLinecap="round" />
                    </svg>
                  </div>
                  <h3 className="text-base font-semibold text-slate-900">{item.title}</h3>
                  <p className="mt-2 text-sm text-slate-600">{item.description}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="workflow" className="border-b border-gray-200 bg-slate-50">
          <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Workflow</h2>
            <ol className="mt-6 grid gap-3 md:grid-cols-2">
              {workflowSteps.map((step, index) => (
                <li key={step} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Step {index + 1}</p>
                  <p className="mt-1 text-sm text-slate-700">{step}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="pricing" className="bg-white">
          <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Pricing</h2>
            <p className="mt-2 text-sm text-slate-600">Simple plans for teams with clear monthly pricing.</p>
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              {plans.map((plan) => (
                <article key={plan.name} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                  <h3 className="text-base font-semibold text-slate-900">{plan.name}</h3>
                  {getPlanDisplayPrice(plan.plan) ? (
                    <p className="mt-3 text-3xl font-semibold text-slate-900">
                      {getPlanDisplayPrice(plan.plan)}
                      <span className="ml-1 text-sm font-medium text-slate-500">/mo</span>
                    </p>
                  ) : (
                    <p className="mt-3 text-2xl font-semibold text-slate-900">{plan.name}</p>
                  )}
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
