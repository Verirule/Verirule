import { Section } from "@/src/components/marketing/Section";

export function Integrations() {
  return (
    <Section id="resources">
      <div className="mb-8 max-w-3xl">
        <h2 className="text-3xl font-semibold text-white sm:text-4xl">Integrations</h2>
        <p className="mt-3 text-base text-[#b6c4df]">Push compliance work into the tools your team already uses.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <article className="rounded-xl border border-[#2b3f62] bg-[#111d34] p-6">
          <h3 className="text-xl font-semibold text-white">Slack</h3>
          <p className="mt-3 text-sm text-[#b7c4dc] sm:text-base">
            Deliver alerts and reminders to channel workflows with direct links back to records.
          </p>
        </article>
        <article className="rounded-xl border border-[#2b3f62] bg-[#111d34] p-6">
          <h3 className="text-xl font-semibold text-white">Jira</h3>
          <p className="mt-3 text-sm text-[#b7c4dc] sm:text-base">
            Create and sync remediation tasks while preserving traceability to source findings.
          </p>
        </article>
        <article className="rounded-xl border border-dashed border-[#3f5a84] bg-[#0f1a2f] p-6">
          <h3 className="text-xl font-semibold text-white">More coming</h3>
          <p className="mt-3 text-sm text-[#b7c4dc] sm:text-base">
            Additional workflow and ticketing integrations are in active development.
          </p>
        </article>
      </div>
    </Section>
  );
}
