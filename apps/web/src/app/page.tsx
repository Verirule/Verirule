import Link from "next/link";

import { LogoMark } from "@/src/components/brand/LogoMark";
import { Footer } from "@/src/components/landing/Footer";
import { Button } from "@/components/ui/button";

const trustItems = ["SOC 2", "GDPR", "ISO 27001", "Secure-by-design"];

const featureTiles = [
  {
    eyebrow: "Automated Monitoring",
    title: "Regulatory changes, tracked automatically.",
    text: "We monitor official regulatory sources across jurisdictions and detect changes the moment they happen.",
    className: "lg:col-span-2",
  },
  {
    eyebrow: "Plain-Language Impact",
    title: "Legal text, translated into action.",
    text: "Dense regulatory updates are summarized into clear, actionable guidance your team can understand instantly.",
    className: "lg:row-span-2",
  },
  {
    eyebrow: "Audit-Ready Alerts",
    title: "Every decision, defensibly logged.",
    text: "Alerts, tasks, evidence, and actions are recorded in a tamper-resistant audit trail, ready whenever you are.",
    className: "",
  },
];

const workflowSteps = [
  "Connect your organization",
  "Select regulatory sources",
  "Verirule monitors continuously",
  "Alerts trigger tasks and evidence",
  "You stay audit-ready",
];

const integrations = [
  { name: "Slack", icon: "S" },
  { name: "Jira", icon: "J" },
  { name: "GitHub", icon: "G" },
  { name: "Cloud platforms", icon: "C" },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-[#0F172A] text-slate-100">
      <main>
        <section className="border-b border-slate-800/80">
          <div className="mx-auto w-full max-w-6xl px-4 pb-24 pt-8 sm:px-6 sm:pt-10 lg:pb-28">
            <div className="mb-20 flex items-center justify-between gap-4">
              <Link href="/" className="flex items-center gap-3">
                <LogoMark className="h-8 w-8 text-[#38BDF8]" />
                <span className="text-lg font-semibold tracking-tight text-white">Verirule</span>
              </Link>
              <div className="flex items-center gap-2">
                <Button
                  asChild
                  variant="outline"
                  className="border-slate-700 bg-transparent text-slate-100 hover:bg-slate-800/80"
                >
                  <Link href="/auth/login">Login</Link>
                </Button>
                <Button asChild className="bg-[#38BDF8] text-slate-950 hover:bg-sky-300">
                  <Link href="/auth/sign-up">Get started free</Link>
                </Button>
              </div>
            </div>

            <div className="grid gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">RegTech Platform</p>
                <h1 className="mt-4 max-w-2xl text-4xl font-semibold tracking-tight text-white sm:text-5xl lg:text-6xl">
                  Stay compliant without the manual grind.
                </h1>
                <p className="mt-6 max-w-2xl text-base leading-relaxed text-slate-300 sm:text-lg">
                  Verirule continuously monitors global regulatory changes and alerts your team before compliance
                  drift becomes a risk. Built for modern, regulated businesses.
                </p>
                <div className="mt-8 flex flex-wrap gap-3">
                  <Button asChild size="lg" className="bg-[#38BDF8] text-slate-950 hover:bg-sky-300">
                    <Link href="/auth/sign-up">Get started free</Link>
                  </Button>
                  <Button
                    asChild
                    size="lg"
                    variant="outline"
                    className="border-slate-700 bg-transparent text-slate-100 hover:bg-slate-800/80"
                  >
                    <Link href="/dashboard">View live demo</Link>
                  </Button>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-6 shadow-[0_20px_40px_rgba(2,6,23,0.45)]">
                <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/70 p-5">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Control Center</p>
                  <div className="space-y-3">
                    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                      <p className="text-sm text-slate-200">Monitoring active across 27 official sources</p>
                    </div>
                    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                      <p className="text-sm text-slate-200">3 high-priority updates routed to compliance owners</p>
                    </div>
                    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                      <p className="text-sm text-[#10B981]">Audit evidence synced to every completed task</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="border-b border-slate-800/80">
          <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Trusted design. Enterprise security.</p>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-slate-200">
              {trustItems.map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 text-xs font-medium"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b border-slate-800/80">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <h2 className="text-2xl font-semibold text-white sm:text-3xl">Bento Feature Grid</h2>
            <div className="mt-8 grid gap-4 lg:grid-cols-3">
              {featureTiles.map((tile) => (
                <article
                  key={tile.title}
                  className={`rounded-2xl border border-slate-800 bg-slate-900/70 p-6 ${tile.className}`.trim()}
                >
                  <p className="text-xs font-semibold uppercase tracking-[0.15em] text-[#38BDF8]">{tile.eyebrow}</p>
                  <h3 className="mt-3 text-xl font-semibold text-white">{tile.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-slate-300">{tile.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b border-slate-800/80">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <h2 className="text-2xl font-semibold text-white sm:text-3xl">How It Works</h2>
            <ol className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {workflowSteps.map((step, index) => (
                <li key={step} className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">{index + 1}</p>
                  <p className="mt-2 text-sm text-slate-200">{step}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="border-b border-slate-800/80">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-8 sm:p-10">
              <h2 className="text-2xl font-semibold text-white sm:text-3xl">Always ready for the next audit.</h2>
              <p className="mt-4 max-w-3xl text-sm leading-relaxed text-slate-300 sm:text-base">
                Verirule creates a living compliance record: who acted, when, and why, so audits become verification,
                not firefighting.
              </p>
            </div>
          </div>
        </section>

        <section className="border-b border-slate-800/80">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <h2 className="text-2xl font-semibold text-white sm:text-3xl">Fits into the tools you already use.</h2>
            <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {integrations.map((integration) => (
                <div
                  key={integration.name}
                  className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/70 p-4"
                >
                  <span className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-700 text-xs font-semibold text-slate-300">
                    {integration.icon}
                  </span>
                  <span className="text-sm text-slate-200">{integration.name}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b border-slate-800/80">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-8 text-center sm:p-10">
              <h2 className="text-3xl font-semibold text-white">Compliance, without chaos.</h2>
              <div className="mt-6 flex justify-center">
                <Button asChild size="lg" className="bg-[#10B981] text-slate-950 hover:bg-emerald-400">
                  <Link href="/auth/sign-up">Create your account</Link>
                </Button>
              </div>
              <p className="mt-3 text-sm text-slate-400">No credit card required.</p>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
