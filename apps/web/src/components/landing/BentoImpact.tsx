const tiles = [
  {
    title: "Automated Monitoring",
    description:
      "Continuously watch regulatory sources and standards updates across your selected jurisdictions.",
  },
  {
    title: "Plain-language Translation",
    description:
      "Convert dense policy updates into concise impact notes product, legal, and operations can all act on.",
  },
  {
    title: "Auditable Alerts",
    description:
      "Route changes with severity, ownership, and rationale so every escalation stays reviewable.",
  },
];

export function BentoImpact() {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <article className="vr-surface rounded-2xl border border-border/70 p-6 lg:col-span-2">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Impact at a glance</p>
        <h3 className="mt-3 text-2xl font-semibold tracking-tight">{tiles[0].title}</h3>
        <p className="mt-3 max-w-2xl text-sm text-muted-foreground">{tiles[0].description}</p>
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-border/70 bg-background/80 p-3">
            <p className="text-xs text-muted-foreground">Sources tracked</p>
            <p className="mt-1 text-xl font-semibold">120+</p>
          </div>
          <div className="rounded-xl border border-border/70 bg-background/80 p-3">
            <p className="text-xs text-muted-foreground">Average scan cycle</p>
            <p className="mt-1 text-xl font-semibold">15 min</p>
          </div>
          <div className="rounded-xl border border-border/70 bg-background/80 p-3">
            <p className="text-xs text-muted-foreground">High-signal findings</p>
            <p className="mt-1 text-xl font-semibold">Ranked by risk</p>
          </div>
        </div>
      </article>

      <div className="grid gap-4">
        <article className="vr-surface rounded-2xl border border-border/70 p-5">
          <h3 className="text-lg font-semibold">{tiles[1].title}</h3>
          <p className="mt-2 text-sm text-muted-foreground">{tiles[1].description}</p>
        </article>
        <article className="vr-surface rounded-2xl border border-border/70 p-5">
          <h3 className="text-lg font-semibold">{tiles[2].title}</h3>
          <p className="mt-2 text-sm text-muted-foreground">{tiles[2].description}</p>
        </article>
      </div>
    </div>
  );
}
