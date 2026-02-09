const features = [
  {
    title: "Monitoring feeds",
    description: "Track selected regulators, standards bodies, and policy sources without manual polling.",
  },
  {
    title: "Change diffs",
    description: "See what changed between versions so reviewers focus on net-new obligations first.",
  },
  {
    title: "Org workspaces",
    description: "Run separate tenant workspaces with isolated ownership, workflows, and evidence.",
  },
  {
    title: "Alert routing",
    description: "Send high-signal updates to legal, compliance, and product owners with clear urgency.",
  },
  {
    title: "Audit trail",
    description: "Keep timestamped actions, assignees, and rationale in one timeline for later audits.",
  },
  {
    title: "Policy packs (future)",
    description: "Apply curated controls and templates for faster rollout across common frameworks.",
  },
];

export function FeatureGrid() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {features.map((feature) => (
        <article key={feature.title} className="rounded-2xl border bg-card/70 p-6">
          <h3 className="text-base font-semibold">{feature.title}</h3>
          <p className="mt-2 text-sm text-muted-foreground">{feature.description}</p>
        </article>
      ))}
    </div>
  );
}
