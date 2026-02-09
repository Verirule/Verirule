const steps = [
  {
    title: "Define coverage",
    description: "Pick jurisdictions, standards, and product areas that matter to your business.",
  },
  {
    title: "Review diffs",
    description: "Receive concise updates with side-by-side change context and priority hints.",
  },
  {
    title: "Route decisions",
    description: "Assign owners, attach rationale, and maintain an auditable history of actions.",
  },
];

export function HowItWorks() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {steps.map((step, index) => (
        <article key={step.title} className="rounded-2xl border bg-card/70 p-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-full border text-sm font-semibold">
            {index + 1}
          </div>
          <h3 className="mt-4 text-base font-semibold">{step.title}</h3>
          <p className="mt-2 text-sm text-muted-foreground">{step.description}</p>
        </article>
      ))}
    </div>
  );
}
