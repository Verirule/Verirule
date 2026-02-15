import Link from "next/link";

import { Section } from "@/src/components/marketing/Section";

export function Hero() {
  return (
    <Section className="border-t-0" containerClassName="grid gap-12 py-14 sm:py-16 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:py-20">
      <div className="space-y-7">
        <p className="inline-flex rounded-md border border-[#345179] bg-[#111f36] px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-[#c7d8fb]">
          Enterprise Compliance Operations
        </p>
        <h1 className="text-4xl font-semibold leading-tight text-white sm:text-5xl">
          Compliance monitoring with an audit-ready record from day one.
        </h1>
        <p className="max-w-2xl text-base leading-relaxed text-[#b6c4df] sm:text-lg">
          Verirule helps teams detect regulatory changes, explain impact in plain language, and prove every action with
          signed, traceable evidence.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/auth/sign-up"
            className="rounded-md bg-[#3e6ef4] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#2f5dd9] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]"
          >
            Get started free
          </Link>
          <a
            href="#pricing"
            className="rounded-md border border-[#3a5277] bg-[#0e1a2f] px-5 py-3 text-sm font-semibold text-[#d9e4fb] transition-colors hover:border-[#6285c6] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]"
          >
            View pricing
          </a>
        </div>
        <p className="text-sm text-[#9fb2d4]">Trusted by teams that need clear ownership, durable evidence, and exam-ready exports.</p>
      </div>

      <div className="rounded-xl border border-[#2b3f62] bg-[#0f1b31] p-4 sm:p-5">
        <div className="rounded-lg border border-[#365179] bg-[#132341]">
          <div className="flex items-center justify-between border-b border-[#2e4569] px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#bcd0f1]">Compliance Dashboard</p>
            <span className="rounded-full border border-[#3d5b88] px-2 py-0.5 text-xs text-[#d6e4ff]">Live monitoring</span>
          </div>

          <div className="grid gap-3 p-4 sm:grid-cols-3">
            <div className="rounded-md border border-[#2e4569] bg-[#10203a] p-3">
              <p className="text-xs text-[#a2b6da]">Controls monitored</p>
              <p className="mt-2 text-2xl font-semibold text-white">248</p>
            </div>
            <div className="rounded-md border border-[#2e4569] bg-[#10203a] p-3">
              <p className="text-xs text-[#a2b6da]">Open items</p>
              <p className="mt-2 text-2xl font-semibold text-white">12</p>
            </div>
            <div className="rounded-md border border-[#2e4569] bg-[#10203a] p-3">
              <p className="text-xs text-[#a2b6da]">Evidence SLA</p>
              <p className="mt-2 text-2xl font-semibold text-white">99.3%</p>
            </div>
          </div>

          <div className="space-y-2 border-t border-[#2e4569] p-4">
            <div className="flex items-center justify-between rounded-md border border-[#2e4569] bg-[#10203a] px-3 py-2">
              <p className="text-sm text-[#dee8fa]">FINRA notice mapped to policy control set</p>
              <span className="text-xs text-[#9fb2d4]">Assigned</span>
            </div>
            <div className="flex items-center justify-between rounded-md border border-[#2e4569] bg-[#10203a] px-3 py-2">
              <p className="text-sm text-[#dee8fa]">Reviewer comments signed and stored</p>
              <span className="text-xs text-[#9fb2d4]">Captured</span>
            </div>
            <div className="flex items-center justify-between rounded-md border border-[#2e4569] bg-[#10203a] px-3 py-2">
              <p className="text-sm text-[#dee8fa]">Export package generated for Q1 audit</p>
              <span className="text-xs text-[#9fb2d4]">Ready</span>
            </div>
          </div>
        </div>
      </div>
    </Section>
  );
}
