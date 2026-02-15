import { Section } from "@/src/components/marketing/Section";

const pillars = [
  {
    title: "Monitoring",
    text: "Track regulatory sources on schedule and receive structured alerts when language changes materially.",
  },
  {
    title: "Plain language impact",
    text: "Translate legal updates into concise operational summaries so owners know what must change and why.",
  },
  {
    title: "Audit trail",
    text: "Capture decisions, evidence, and approvals in a tamper evident timeline that is ready for examiner review.",
  },
] as const;

export function PillarsBento() {
  return (
    <Section id="product">
      <div className="mb-8 max-w-3xl">
        <h2 className="text-3xl font-semibold text-white sm:text-4xl">Three pillars for continuous compliance.</h2>
        <p className="mt-3 text-base text-[#b6c4df]">
          Built to reduce ambiguity in day to day operations while preserving defensible records.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {pillars.map((pillar, index) => (
          <article
            key={pillar.title}
            className={[
              "rounded-xl border border-[#2b3f62] bg-[#111d34] p-6",
              index === 0 ? "md:row-span-2" : "",
            ]
              .join(" ")
              .trim()}
          >
            <h3 className="text-xl font-semibold text-white">{pillar.title}</h3>
            <p className="mt-3 text-sm leading-relaxed text-[#b7c4dc] sm:text-base">{pillar.text}</p>
          </article>
        ))}
      </div>
    </Section>
  );
}
