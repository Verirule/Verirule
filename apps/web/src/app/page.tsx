import Image from "next/image";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Footer } from "@/src/components/landing/Footer";
import { Nav } from "@/src/components/landing/Nav";

const pillars = [
  {
    title: "Monitor",
    text: "Track official regulatory sources with scheduled checks and reliable change detection.",
  },
  {
    title: "Operationalize",
    text: "Convert alerts into accountable tasks with ownership, due dates, and escalation context.",
  },
  {
    title: "Evidence",
    text: "Keep an audit-ready timeline of actions, comments, and linked artifacts.",
  },
] as const;

const outcomes = [
  "Faster response to critical policy updates",
  "Clear ownership and closure accountability",
  "Exportable records for audit and exam readiness",
] as const;

export default function Home() {
  return (
    <div className="min-h-screen bg-[linear-gradient(160deg,#f3faf6_0%,#ffffff_58%,#e5f5ec_100%)] text-[#0f3e2a]">
      <Nav />

      <main>
        <section id="results" className="border-b border-[#b4dcc5]/70">
          <div className="mx-auto grid max-w-6xl gap-8 px-4 py-14 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:py-20">
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 rounded-full border border-[#9fcfb4] bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-[#0b7a3f]">
                <Image src="/brand/icon.svg" alt="Verirule icon" width={20} height={20} className="h-5 w-5" />
                Regulatory Intelligence
              </div>

              <h1 className="text-4xl font-bold tracking-tight text-[#0b3a27] sm:text-5xl lg:text-6xl">
                Compliance operations that stay clear under scrutiny.
              </h1>

              <p className="max-w-2xl text-base leading-relaxed text-[#1f5a3f]/85 sm:text-lg">
                Verirule unifies regulatory monitoring, issue workflows, and evidence history so teams can act quickly and
                prove control effectiveness when it matters.
              </p>

              <div className="flex flex-wrap gap-3">
                <Button asChild size="lg" className="bg-[#0b7a3f] text-white hover:bg-[#086332]">
                  <Link href="/auth/sign-up">Create account</Link>
                </Button>
                <Button asChild size="lg" variant="outline" className="border-[#98ccb0] bg-white text-[#0f4b32] hover:bg-[#edf8f2]">
                  <Link href="/auth/login">Sign in</Link>
                </Button>
              </div>
            </div>

            <div className="relative rounded-3xl border-2 border-[#aed8bf] bg-white p-6 shadow-[0_18px_50px_rgba(14,67,43,0.15)] sm:p-8">
              <div className="absolute -top-4 right-5 rounded-full border border-[#97cfae] bg-[#eaf7f0] px-3 py-1 text-xs font-semibold text-[#0f6738]">
                2D Brand Panel
              </div>

              <Image
                src="/brand/logo.svg"
                alt="Verirule logo"
                width={620}
                height={620}
                className="mx-auto h-auto w-full max-w-[290px] object-contain"
                priority
              />

              <div className="mt-6 grid gap-2 text-sm text-[#1d5a3d]">
                {outcomes.map((item) => (
                  <div key={item} className="flex items-center gap-2 rounded-lg border border-[#d0eadb] bg-[#f6fcf9] px-3 py-2">
                    <span className="h-2 w-2 rounded-full bg-[#0b7a3f]" />
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="components" className="border-b border-[#b4dcc5]/70">
          <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6 lg:py-18">
            <div className="mb-8">
              <h2 className="text-3xl font-semibold text-[#0b3a27]">How Verirule Works</h2>
              <p className="mt-2 max-w-3xl text-sm text-[#1f5a3f]/80 sm:text-base">
                A focused 2D workflow architecture designed for regulated teams that need speed without sacrificing traceability.
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              {pillars.map((pillar) => (
                <article
                  key={pillar.title}
                  className="rounded-2xl border-2 border-[#c6e5d3] bg-white p-6 shadow-[0_6px_0_rgba(16,88,57,0.12)]"
                >
                  <h3 className="text-xl font-semibold text-[#0b3a27]">{pillar.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-[#1d543a]/85">{pillar.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="launch" className="border-b border-[#b4dcc5]/70">
          <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6 lg:py-18">
            <div className="rounded-3xl border-2 border-[#5aa679] bg-[#0d6338] px-6 py-8 text-white shadow-[0_10px_0_rgba(9,73,41,0.4)] sm:px-8">
              <div className="flex flex-wrap items-center justify-between gap-5">
                <div>
                  <h2 className="text-2xl font-semibold sm:text-3xl">Launch a clear compliance command center.</h2>
                  <p className="mt-2 max-w-2xl text-sm text-[#d4efdf] sm:text-base">
                    Use your Verirule workspace to keep decision trails, delivery states, and remediation records visible.
                  </p>
                </div>

                <Image src="/brand/icon.svg" alt="Verirule icon" width={86} height={86} className="h-[72px] w-[72px]" />
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                <Button asChild size="lg" className="bg-white text-[#0f4d32] hover:bg-[#ecf8f1]">
                  <Link href="/auth/sign-up">Create account</Link>
                </Button>
                <Button asChild size="lg" variant="outline" className="border-[#c3e4d2] bg-transparent text-white hover:bg-[#0a522f]">
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
