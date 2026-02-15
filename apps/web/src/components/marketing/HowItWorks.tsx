import { Section } from "@/src/components/marketing/Section";

const steps = [
  {
    title: "Connect sources",
    text: "Select jurisdictions and source feeds you care about. Verirule runs checks and records each run.",
  },
  {
    title: "Assign response",
    text: "Route impact summaries into team workflows with owners, due dates, and status controls.",
  },
  {
    title: "Prove completion",
    text: "Attach evidence, approvals, and comments. Export a complete record when audits or exams begin.",
  },
] as const;

export function HowItWorks() {
  return (
    <Section>
      <div className="mb-8 max-w-3xl">
        <h2 className="text-3xl font-semibold text-white sm:text-4xl">How it works</h2>
        <p className="mt-3 text-base text-[#b6c4df]">A clear workflow from change detection to signed off evidence.</p>
      </div>

      <ol className="grid gap-4 md:grid-cols-3">
        {steps.map((step, index) => (
          <li key={step.title} className="rounded-xl border border-[#2b3f62] bg-[#111d34] p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[#9db6e8]">Step {index + 1}</p>
            <h3 className="mt-2 text-xl font-semibold text-white">{step.title}</h3>
            <p className="mt-3 text-sm leading-relaxed text-[#b7c4dc] sm:text-base">{step.text}</p>
          </li>
        ))}
      </ol>
    </Section>
  );
}
