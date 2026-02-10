const trustBadges = ["SOC 2-ready", "GDPR-aligned", "ISO 27001-mapped"];

const integrationChips = ["Slack", "Jira", "GitHub", "AWS"];

export function TrustBar() {
  return (
    <section className="mx-auto w-full max-w-6xl px-4 pb-10 sm:px-6">
      <div className="vr-surface rounded-2xl border border-border/70 p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-2">
          {trustBadges.map((badge) => (
            <span
              key={badge}
              className="inline-flex items-center rounded-full border border-border/70 bg-background/70 px-3 py-1 text-xs font-medium text-foreground"
            >
              {badge}
            </span>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          {integrationChips.map((chip) => (
            <span
              key={chip}
              className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-background px-3 py-1 text-xs text-muted-foreground"
            >
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden />
              {chip}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
