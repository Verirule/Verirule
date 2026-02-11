import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Footer } from "@/src/components/landing/Footer";
import { Nav } from "@/src/components/landing/Nav";

const systemComponents = [
  {
    title: "Source Intake",
    text: "Connect official publications, supervisory notices, and policy feeds by jurisdiction.",
  },
  {
    title: "Change Detection",
    text: "Track document updates and material deltas with a consistent monitoring schedule.",
  },
  {
    title: "Issue Workflow",
    text: "Route alerts into tasks with ownership, due dates, and linked remediation evidence.",
  },
  {
    title: "Evidence Record",
    text: "Maintain a full event log of actions, comments, and supporting artifacts.",
  },
] as const;

const integrationItems = [
  {
    name: "Slack",
    text: "Send approved alerts to operating channels for controlled triage.",
  },
  {
    name: "Jira",
    text: "Create remediation tickets mapped to the originating finding and status history.",
  },
] as const;

const audience = [
  {
    title: "Compliance Teams",
    text: "Maintain policy oversight across jurisdictions without manual source tracking.",
  },
  {
    title: "Risk and Controls",
    text: "Connect findings to accountable actions and monitor closure quality.",
  },
  {
    title: "Legal Operations",
    text: "Review source changes with context and preserve decision traceability.",
  },
  {
    title: "Internal Audit",
    text: "Access a complete record of who did what, when, and under which policy scope.",
  },
] as const;

export default function Home() {
  return (
    <div className="min-h-screen bg-[#F4F8FF] text-[#0F274D]">
      <Nav />

      <main>
        <section className="border-b border-blue-200/80">
          <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:py-24">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-700">Regulatory Operations Platform</p>
            <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight text-[#0B2B59] sm:text-5xl lg:text-6xl">
              Regulatory change management with full audit traceability.
            </h1>
            <p className="mt-6 max-w-3xl text-base leading-relaxed text-blue-900/80 sm:text-lg">
              Verirule helps regulated organizations monitor source changes, assign remediation, and maintain a reliable
              evidence trail for audit and supervisory review.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg" className="bg-blue-700 text-white hover:bg-blue-800">
                <Link href="/auth/sign-up">Create account</Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="border-blue-300 bg-white text-blue-800 hover:bg-blue-50"
              >
                <Link href="/auth/login">Sign in</Link>
              </Button>
            </div>
          </div>
        </section>

        <section id="problem" className="border-b border-blue-200/80">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <h2 className="text-2xl font-semibold text-[#0B2B59] sm:text-3xl">Problem</h2>
            <p className="mt-4 max-w-4xl text-sm leading-relaxed text-blue-900/80 sm:text-base">
              Regulatory updates are distributed across many official sources and often reviewed through ad hoc spreadsheets,
              email chains, and disconnected ticketing workflows. That creates delayed response, weak ownership, and limited
              evidence when audit or examination requests arrive.
            </p>
          </div>
        </section>

        <section id="components" className="border-b border-blue-200/80">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <h2 className="text-2xl font-semibold text-[#0B2B59] sm:text-3xl">System Components</h2>
            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              {systemComponents.map((item, index) => (
                <article
                  key={item.title}
                  className={`rounded-xl border p-6 ${
                    index % 2 === 0 ? "border-blue-200 bg-white" : "border-blue-200 bg-blue-50/70"
                  }`}
                >
                  <h3 className="text-lg font-semibold text-[#0B2B59]">{item.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-blue-900/80">{item.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="audit-ready" className="border-b border-blue-200/80">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <h2 className="text-2xl font-semibold text-[#0B2B59] sm:text-3xl">Audit-Ready</h2>
            <p className="mt-4 max-w-4xl text-sm leading-relaxed text-blue-900/80 sm:text-base">
              Every monitored change, workflow action, status update, and linked artifact is recorded with timestamps and actor context.
              Teams can provide a defensible operating record without reconstructing evidence from multiple systems.
            </p>
          </div>
        </section>

        <section id="integrations" className="border-b border-blue-200/80">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <h2 className="text-2xl font-semibold text-[#0B2B59] sm:text-3xl">Integrations</h2>
            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              {integrationItems.map((item) => (
                <article key={item.name} className="rounded-xl border border-blue-200 bg-white p-6">
                  <h3 className="text-lg font-semibold text-[#0B2B59]">{item.name}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-blue-900/80">{item.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="who-its-for" className="border-b border-blue-200/80">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <h2 className="text-2xl font-semibold text-[#0B2B59] sm:text-3xl">Who It&apos;s For</h2>
            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              {audience.map((item) => (
                <article key={item.title} className="rounded-xl border border-blue-200 bg-white p-6">
                  <h3 className="text-lg font-semibold text-[#0B2B59]">{item.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-blue-900/80">{item.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b border-blue-200/80">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-20">
            <div className="rounded-2xl border border-blue-300 bg-gradient-to-r from-blue-700 to-blue-600 p-8 sm:p-10">
              <h2 className="text-2xl font-semibold text-white sm:text-3xl">Operate with a consistent compliance record.</h2>
              <p className="mt-3 max-w-3xl text-sm leading-relaxed text-blue-100 sm:text-base">
                Start with a workspace, connect sources, and establish traceable workflows for monitored regulatory change.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Button asChild size="lg" className="bg-white text-blue-800 hover:bg-blue-50">
                  <Link href="/auth/sign-up">Create account</Link>
                </Button>
                <Button
                  asChild
                  size="lg"
                  variant="outline"
                  className="border-blue-200 bg-transparent text-white hover:bg-blue-800/40"
                >
                  <Link href="/dashboard">Open dashboard</Link>
                </Button>
              </div>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
