import { Section } from "@/src/components/marketing/Section";

export function Workflows() {
  return (
    <Section>
      <div className="mb-8 max-w-3xl">
        <h2 className="text-3xl font-semibold text-white sm:text-4xl">Audit-ready workflows</h2>
        <p className="mt-3 text-base text-[#b6c4df]">
          Keep tasks, evidence, and exports connected so control execution is easy to inspect.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <article className="rounded-xl border border-[#2b3f62] bg-[#111d34] p-6">
          <h3 className="text-xl font-semibold text-white">Tasks</h3>
          <ul className="mt-3 space-y-2 text-sm text-[#b7c4dc] sm:text-base">
            <li>Assign owners and due dates by control.</li>
            <li>Track status with clear accountability.</li>
            <li>Escalate overdue work with full context.</li>
          </ul>
        </article>
        <article className="rounded-xl border border-[#2b3f62] bg-[#111d34] p-6">
          <h3 className="text-xl font-semibold text-white">Evidence</h3>
          <ul className="mt-3 space-y-2 text-sm text-[#b7c4dc] sm:text-base">
            <li>Store files and comments with signed URLs.</li>
            <li>Preserve timestamps and decision history.</li>
            <li>Separate access by organization and role.</li>
          </ul>
        </article>
        <article className="rounded-xl border border-[#2b3f62] bg-[#111d34] p-6">
          <h3 className="text-xl font-semibold text-white">Exports</h3>
          <ul className="mt-3 space-y-2 text-sm text-[#b7c4dc] sm:text-base">
            <li>Create auditor-ready packages on demand.</li>
            <li>Include related tasks and evidence records.</li>
            <li>Keep a reproducible chain of what was delivered.</li>
          </ul>
        </article>
      </div>
    </Section>
  );
}
