import Link from "next/link";

import { Section } from "@/src/components/marketing/Section";

export function Hero() {
  return (
    <Section className="border-t-0" containerClassName="grid gap-12 py-14 sm:py-16 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:py-20">
      <div className="space-y-7">
        <p className="inline-flex rounded-md border border-[#3B86C2] bg-[#0A3658] px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-[#D7ECFF]">
          Enterprise Compliance Operations
        </p>
        <h1 className="text-4xl font-semibold leading-tight text-[#F4FBFF] sm:text-5xl">
          Compliance monitoring with an audit ready record from day one.
        </h1>
        <p className="max-w-2xl text-base leading-relaxed text-[#CFE6FA] sm:text-lg">
          Verirule helps teams detect regulatory changes, explain impact in plain language, and prove every action with
          signed, traceable evidence.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/auth/sign-up"
            className="rounded-md bg-[#1678C8] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#0F66AE] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8CC9FF]"
          >
            Get started free
          </Link>
          <a
            href="#pricing"
            className="rounded-md border border-[#4C9AD3] bg-[#0B3A62] px-5 py-3 text-sm font-semibold text-[#EAF6FF] transition-colors hover:border-[#83C5F8] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8CC9FF]"
          >
            View pricing
          </a>
        </div>
        <p className="text-sm text-[#BFDCF6]">Trusted by teams that need clear ownership, durable evidence, and exam ready exports.</p>
      </div>

      <div className="rounded-xl border border-[#2A77AE] bg-[#09345A] p-4 sm:p-5">
        <div className="rounded-lg border border-[#2C86BF] bg-[#0A416E]">
          <div className="flex items-center justify-between border-b border-[#2A77AE] px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#D8EEFF]">Compliance Command Center</p>
            <span className="rounded-full border border-[#4A99D3] bg-[#164B77] px-2 py-0.5 text-xs text-[#E3F5FF]">Live view</span>
          </div>

          <div className="grid gap-3 p-4 sm:grid-cols-2">
            <div className="rounded-md border border-[#2A77AE] bg-[#0B365C] p-3">
              <p className="text-xs text-[#BDDDF8]">Controls monitored</p>
              <p className="mt-2 text-2xl font-semibold text-white">248</p>
            </div>
            <div className="rounded-md border border-[#2A77AE] bg-[#0B365C] p-3">
              <p className="text-xs text-[#BDDDF8]">Open items</p>
              <p className="mt-2 text-2xl font-semibold text-[#BEE3FF]">12</p>
            </div>
            <div className="rounded-md border border-[#2A77AE] bg-[#0B365C] p-3">
              <p className="text-xs text-[#BDDDF8]">Evidence coverage</p>
              <p className="mt-2 text-2xl font-semibold text-[#9ED4FF]">99.3%</p>
            </div>
            <div className="rounded-md border border-[#2A77AE] bg-[#0B365C] p-3">
              <p className="text-xs text-[#BDDDF8]">Average closure</p>
              <p className="mt-2 text-2xl font-semibold text-[#D8EEFF]">2.1 days</p>
            </div>
          </div>

          <div className="grid gap-3 border-t border-[#2A77AE] p-4 sm:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-md border border-[#2A77AE] bg-[#0B365C] p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#BBDCF7]">Coverage By Framework</p>
              <div className="mt-3 space-y-2">
                <div>
                  <div className="mb-1 flex items-center justify-between text-xs text-[#D9EEFF]">
                    <span>SOC 2</span>
                    <span>96%</span>
                  </div>
                  <div className="h-2 rounded-full bg-[#13466F]">
                    <div className="h-2 rounded-full bg-[#66B9F4]" style={{ width: "96%" }} />
                  </div>
                </div>
                <div>
                  <div className="mb-1 flex items-center justify-between text-xs text-[#D9EEFF]">
                    <span>ISO 27001</span>
                    <span>91%</span>
                  </div>
                  <div className="h-2 rounded-full bg-[#13466F]">
                    <div className="h-2 rounded-full bg-[#66B9F4]" style={{ width: "91%" }} />
                  </div>
                </div>
              </div>
            </div>
            <div className="space-y-2 rounded-md border border-[#2A77AE] bg-[#0B365C] p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#BBDCF7]">Priority Queue</p>
              <div className="flex items-center justify-between rounded-md border border-[#2A77AE] bg-[#0A3256] px-2.5 py-2">
                <p className="text-xs text-[#E6F5FF]">FINRA notice mapped to controls</p>
                <span className="rounded-full bg-[#174D77] px-2 py-0.5 text-[11px] text-[#D8EEFF]">Assigned</span>
              </div>
              <div className="flex items-center justify-between rounded-md border border-[#2A77AE] bg-[#0A3256] px-2.5 py-2">
                <p className="text-xs text-[#E6F5FF]">Reviewer approvals captured</p>
                <span className="rounded-full bg-[#174D77] px-2 py-0.5 text-[11px] text-[#D8EEFF]">Stored</span>
              </div>
              <div className="flex items-center justify-between rounded-md border border-[#2A77AE] bg-[#0A3256] px-2.5 py-2">
                <p className="text-xs text-[#E6F5FF]">Export package generated for Q1 audit</p>
                <span className="rounded-full bg-[#174D77] px-2 py-0.5 text-[11px] text-[#D8EEFF]">Ready</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Section>
  );
}
