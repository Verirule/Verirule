import { Section } from "@/src/components/marketing/Section";

const faqs = [
  {
    question: "Who is Verirule for?",
    answer: "Compliance, legal, and operations teams that need to monitor policy changes and maintain evidence for audits.",
  },
  {
    question: "Can we start on Free and upgrade later?",
    answer: "Yes. Free is designed for real usage and you can move to Pro or Business without data migration.",
  },
  {
    question: "How does Verirule support audits?",
    answer: "Tasks, evidence, approvals, and exports are linked in a timeline so auditors can verify what happened and when.",
  },
  {
    question: "Which integrations are available now?",
    answer: "Slack and Jira are available today. Additional integrations are planned based on customer demand.",
  },
  {
    question: "Where is our data hosted?",
    answer: "Data is hosted in managed cloud infrastructure with access controls, audit events, and encrypted transport.",
  },
] as const;

export function FAQ() {
  return (
    <Section>
      <div className="mb-8 max-w-3xl">
        <h2 className="text-3xl font-semibold text-white sm:text-4xl">Frequently asked questions</h2>
      </div>

      <div className="space-y-3">
        {faqs.map((faq) => (
          <details key={faq.question} className="rounded-xl border border-[#2b3f62] bg-[#111d34] p-5">
            <summary className="cursor-pointer list-none text-base font-semibold text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]">
              {faq.question}
            </summary>
            <p className="mt-3 text-sm text-[#b7c4dc] sm:text-base">{faq.answer}</p>
          </details>
        ))}
      </div>
    </Section>
  );
}
