import { Section } from "@/src/components/marketing/Section";

const controls = [
  {
    title: "Row-level security (RLS)",
    text: "Organization data is isolated with policy-enforced access controls in the data layer.",
  },
  {
    title: "Signed URLs",
    text: "Evidence files are delivered through time-bound signed URLs to limit exposure and replay risk.",
  },
  {
    title: "Audit events",
    text: "User actions are recorded with timestamps and actor identity for compliance investigations.",
  },
  {
    title: "Least privilege",
    text: "Role-based access supports separation of duties and controlled review workflows.",
  },
] as const;

export function SecurityTrust() {
  return (
    <Section id="security">
      <div className="mb-8 max-w-3xl">
        <h2 className="text-3xl font-semibold text-white sm:text-4xl">Security and trust</h2>
        <p className="mt-3 text-base text-[#b6c4df]">
          Verirule is designed for teams that need controlled access, defensible records, and reliable exports.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {controls.map((control) => (
          <article key={control.title} className="rounded-xl border border-[#2b3f62] bg-[#111d34] p-6">
            <h3 className="text-xl font-semibold text-white">{control.title}</h3>
            <p className="mt-3 text-sm text-[#b7c4dc] sm:text-base">{control.text}</p>
          </article>
        ))}
      </div>
    </Section>
  );
}
