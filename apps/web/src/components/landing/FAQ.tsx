const faqs = [
  {
    question: "How quickly are policy changes detected?",
    answer:
      "Detection speed depends on source cadence, but updates are generally processed shortly after publication.",
  },
  {
    question: "Can I keep legal and product teams in separate workflows?",
    answer: "Yes. Workspaces and routing rules let each team receive only the updates relevant to their scope.",
  },
  {
    question: "Do you provide legal advice?",
    answer:
      "No. Verirule provides monitoring and workflow support; legal interpretation remains with your internal or external counsel.",
  },
  {
    question: "Is there an API for integrations?",
    answer: "Yes. The platform is API-first, with authenticated endpoints for claims and organization data.",
  },
  {
    question: "Can we start small and scale later?",
    answer: "Yes. Many teams begin with a narrow policy scope and expand coverage once routing is established.",
  },
];

export function FAQ() {
  return (
    <div className="space-y-3">
      {faqs.map((item) => (
        <details key={item.question} className="group rounded-xl border bg-card/70 px-5 py-4">
          <summary className="cursor-pointer list-none pr-6 text-sm font-semibold">
            {item.question}
            <span className="float-right text-muted-foreground transition-transform group-open:rotate-45">+</span>
          </summary>
          <p className="mt-3 text-sm text-muted-foreground">{item.answer}</p>
        </details>
      ))}
    </div>
  );
}
