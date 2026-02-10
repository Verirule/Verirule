import Link from "next/link";

import { Button } from "@/components/ui/button";
import { LogoMark } from "@/src/components/brand/LogoMark";
import { Footer } from "@/src/components/landing/Footer";

const trustItems = ["SOC 2", "GDPR", "ISO 27001", "Secure-by-design"];

const featureTiles = [
  {
    title: "Regulatory changes, tracked automatically.",
    text: "We monitor official regulatory sources across jurisdictions and detect changes the moment they happen.",
  },
  {
    title: "Legal text, translated into action.",
    text: "Dense regulatory updates are summarized into clear, actionable guidance your team can understand instantly.",
  },
  {
    title: "Every decision, defensibly logged.",
    text: "Alerts, tasks, evidence, and actions are recorded in a tamper-resistant audit trail—ready whenever you are.",
  },
];

const workflowSteps = [
  "Connect your organization",
  "Select regulatory sources",
  "Verirule monitors continuously",
  "Alerts trigger tasks and evidence",
  "You stay audit-ready",
];

export default function Home() {
  return (
    <div className="min-h-screen bg-[#0F172A] text-slate-100">
      <main>
        <section className="border-b border-slate-800">
          <div className="mx-auto w-full max-w-6xl px-4 pb-20 pt-8 sm:px-6 sm:pt-10 lg:pb-24">
            <div className="mb-16 flex items-center justify-between gap-4">
              <Link href="/" className="flex items-center gap-3">
                <LogoMark className="h-8 w-8 text-sky-400" />
                <span className="text-lg font-semibold tracking-tight text-white">Verirule</span>
              </Link>
              <div className="flex items-center gap-2">
                <Button
                  asChild
                  variant="outline"
                  className="border-slate-700 bg-transparent text-slate-100 hover:bg-slate-800"
                >
                  <Link href="/auth/login">Login</Link>
                </Button>
                <Button asChild className="bg-sky-400 text-slate-950 hover:bg-sky-300">
                  <Link href="/auth/sign-up">Get started</Link>
                </Button>
              </div>
            </div>

            <div className="grid gap-14 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
              <div className="space-y-6">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">RegTech Platform</p>
                <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                  Stay compliant without the manual grind.
                </h1>
                <p className="max-w-2xl text-base leading-relaxed text-slate-300 sm:text-lg">
                  Verirule continuously monitors global regulatory changes and alerts your team before compliance
                  drift becomes a risk. Built for modern, regulated businesses.
                </p>
                <div className="flex flex-wrap gap-3">
                  <Button asChild size="lg" className="bg-sky-400 text-slate-950 hover:bg-sky-300">
                    <Link href="/auth/sign-up">Get started free</Link>
                  </Button>
                  <Button
                    asChild
                    size="lg"
                    variant="outline"
                    className="border-slate-700 bg-transparent text-slate-100 hover:bg-slate-800"
                  >
                    <Link href="/dashboard">View live demo</Link>
                  </Button>
                </div>
              </div>

              <div className="grid gap-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
                <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Live Monitoring</p>
                  <p className="mt-2 text-sm text-slate-200">27 regulatory sources tracked continuously</p>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Risk Posture</p>
                  <p className="mt-2 text-sm text-slate-200">
                    Compliance drift prevented with early alerting and action workflows
                  </p>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Audit Confidence</p>
                  <p className="mt-2 text-sm text-emerald-400">Evidence attached across all active remediations</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="border-b border-slate-800">
          <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6">
            <p className="mb-3 text-xs uppercase tracking-[0.16em] text-slate-400">
              Trusted design. Enterprise security.
            </p>
            <div className="flex flex-wrap gap-2">
              {trustItems.map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs font-medium text-slate-200"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b border-slate-800">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6">
            <h2 className="mb-8 text-2xl font-semibold text-white sm:text-3xl">Bento Feature Grid</h2>
            <div className="grid gap-4 lg:grid-cols-3">
              <article className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-sky-300">
                  Automated Monitoring
                </p>
                <h3 className="text-xl font-semibold text-white">{featureTiles[0].title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-slate-300">{featureTiles[0].text}</p>
              </article>
              <article className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-sky-300">Plain-Language Impact</p>
                <h3 className="text-xl font-semibold text-white">{featureTiles[1].title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-slate-300">{featureTiles[1].text}</p>
              </article>
              <article className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-sky-300">Audit-Ready Alerts</p>
                <h3 className="text-xl font-semibold text-white">{featureTiles[2].title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-slate-300">{featureTiles[2].text}</p>
              </article>
            </div>
          </div>
        </section>

        <section className="border-b border-slate-800">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6">
            <h2 className="mb-8 text-2xl font-semibold text-white sm:text-3xl">How It Works</h2>
            <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {workflowSteps.map((step, index) => (
                <li key={step} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{index + 1}</p>
                  <p className="mt-2 text-sm text-slate-200">{step}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="border-b border-slate-800">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6">
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8">
              <h2 className="text-2xl font-semibold text-white sm:text-3xl">Always ready for the next audit.</h2>
              <p className="mt-4 max-w-3xl text-sm leading-relaxed text-slate-300 sm:text-base">
                Verirule creates a living compliance record—who acted, when, and why—so audits become verification,
                not firefighting.
              </p>
            </div>
          </div>
        </section>

        <section className="border-b border-slate-800">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6">
            <h2 className="text-2xl font-semibold text-white sm:text-3xl">Fits into the tools you already use.</h2>
            <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-sm text-slate-200">Slack</div>
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-sm text-slate-200">Jira</div>
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-sm text-slate-200">GitHub</div>
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-sm text-slate-200">
                Cloud platforms
              </div>
            </div>
          </div>
        </section>

        <section className="border-b border-slate-800">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-8 text-center">
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
