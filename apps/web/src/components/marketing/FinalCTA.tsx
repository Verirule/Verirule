import Link from "next/link";

import { Section } from "@/src/components/marketing/Section";

export function FinalCTA() {
  return (
    <Section>
      <div className="rounded-2xl border border-[#3b5d97] bg-[#112447] p-8 sm:p-10">
        <h2 className="max-w-2xl text-3xl font-semibold text-white sm:text-4xl">Build a compliance program your auditors can trust.</h2>
        <p className="mt-3 max-w-2xl text-base text-[#c3d4f4]">
          Start with a usable free plan, then scale into enterprise workflows without rebuilding your evidence process.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/auth/sign-up"
            className="rounded-md bg-[#3e6ef4] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#2f5dd9] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]"
          >
            Get started
          </Link>
          <Link
            href="/auth/login"
            className="rounded-md border border-[#5778af] bg-[#14294f] px-5 py-3 text-sm font-semibold text-[#d9e4fb] transition-colors hover:border-[#84a2d4] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]"
          >
            Sign in
          </Link>
        </div>
      </div>
    </Section>
  );
}
