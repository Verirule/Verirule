import Link from "next/link";

import { Section } from "@/src/components/marketing/Section";

export function FinalCTA() {
  return (
    <Section>
      <div className="rounded-2xl border border-[#2E7DB5] bg-[#0A3A63] p-8 sm:p-10">
        <h2 className="max-w-2xl text-3xl font-semibold text-white sm:text-4xl">Build a compliance program your auditors can trust.</h2>
        <p className="mt-3 max-w-2xl text-base text-[#D4EAFF]">
          Start with a usable free plan, then scale into enterprise workflows without rebuilding your evidence process.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/auth/sign-up"
            className="rounded-md bg-[#1678C8] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#0F66AE] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8CC9FF]"
          >
            Get started
          </Link>
          <Link
            href="/auth/login"
            className="rounded-md border border-[#4C9AD3] bg-[#0B3154] px-5 py-3 text-sm font-semibold text-[#E7F5FF] transition-colors hover:border-[#83C5F8] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8CC9FF]"
          >
            Sign in
          </Link>
        </div>
      </div>
    </Section>
  );
}
