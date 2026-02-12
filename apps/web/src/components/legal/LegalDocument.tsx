import Link from "next/link";

import { LogoMark } from "@/src/components/brand/LogoMark";

type LegalSection = {
  heading: string;
  paragraphs: readonly string[];
};

type LegalDocumentProps = {
  title: string;
  summary: string;
  lastUpdated: string;
  sections: readonly LegalSection[];
};

export function LegalDocument({ title, summary, lastUpdated, sections }: LegalDocumentProps) {
  return (
    <div className="min-h-screen bg-[#0F172A] text-slate-100">
      <main className="mx-auto w-full max-w-4xl px-4 py-10 sm:px-6 sm:py-14">
        <header className="mb-8">
          <Link href="/" className="inline-flex items-center gap-2">
            <LogoMark className="h-7 w-7" />
            <span className="font-semibold text-white">Verirule</span>
          </Link>
          <h1 className="mt-6 text-3xl font-semibold tracking-tight text-white sm:text-4xl">{title}</h1>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-300 sm:text-base">{summary}</p>
          <p className="mt-2 text-xs uppercase tracking-[0.15em] text-slate-400">Last updated: {lastUpdated}</p>
        </header>

        <div className="space-y-4">
          {sections.map((section) => (
            <section key={section.heading} className="rounded-xl border border-slate-800 bg-slate-900/70 p-6">
              <h2 className="text-xl font-semibold text-white">{section.heading}</h2>
              <div className="mt-3 space-y-2 text-sm leading-relaxed text-slate-300">
                {section.paragraphs.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </div>
            </section>
          ))}
        </div>

        <footer className="mt-8 text-sm text-slate-400">
          Questions about this document? Contact{" "}
          <a href="mailto:legal@verirule.com" className="text-[#38BDF8] hover:underline">
            legal@verirule.com
          </a>
          .
        </footer>
      </main>
    </div>
  );
}
