import Link from "next/link";

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
    <div className="min-h-screen bg-white text-slate-900">
      <main className="mx-auto w-full max-w-4xl px-4 py-10 sm:px-6 sm:py-14">
        <header className="mb-8">
          <Link href="/" className="inline-flex items-center gap-3">
            <span className="inline-flex h-11 w-11 items-center justify-center rounded-md border border-gray-200 bg-slate-50 p-2">
              <img src="/logo.svg" alt="Verirule" className="h-full w-full object-contain" />
            </span>
            <span className="text-xl font-bold text-slate-900">Verirule</span>
          </Link>
          <h1 className="mt-6 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">{title}</h1>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 sm:text-base">{summary}</p>
          <p className="mt-2 text-xs uppercase tracking-[0.15em] text-slate-500">Last updated: {lastUpdated}</p>
        </header>

        <div className="space-y-4">
          {sections.map((section) => (
            <section key={section.heading} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-semibold text-slate-900">{section.heading}</h2>
              <div className="mt-3 space-y-2 text-sm leading-relaxed text-slate-700">
                {section.paragraphs.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </div>
            </section>
          ))}
        </div>

        <footer className="mt-8 text-sm text-slate-600">
          Questions about this document? Contact{" "}
          <a href="mailto:legal@verirule.com" className="text-blue-700 hover:underline">
            legal@verirule.com
          </a>
          .
        </footer>
      </main>
    </div>
  );
}
