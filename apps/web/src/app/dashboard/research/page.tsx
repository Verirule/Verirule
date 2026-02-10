import Link from "next/link";

const researchCards = [
  {
    title: "Jurisdiction Watchlist",
    description: "Track upcoming consultations, notices, and enforcement updates by region.",
    actionHref: "/dashboard/sources",
    actionLabel: "Manage Sources",
  },
  {
    title: "Impact Analysis Queue",
    description: "Review newly detected regulatory changes and prioritize legal impact assessment.",
    actionHref: "/dashboard/findings",
    actionLabel: "Open Findings",
  },
  {
    title: "Evidence Review",
    description: "Validate attached evidence quality before remediation tasks are closed.",
    actionHref: "/dashboard/tasks",
    actionLabel: "Open Tasks",
  },
] as const;

export default function DashboardResearchPage() {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Research</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Organize discovery work and follow-up analysis before issues escalate into compliance risk.
        </p>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {researchCards.map((card) => (
          <article key={card.title} className="rounded-xl border border-border/70 bg-card p-5 shadow-sm">
            <h2 className="text-base font-semibold">{card.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{card.description}</p>
            <Link
              href={card.actionHref}
              className="mt-4 inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium transition-colors hover:bg-accent"
            >
              {card.actionLabel}
            </Link>
          </article>
        ))}
      </section>
    </div>
  );
}
