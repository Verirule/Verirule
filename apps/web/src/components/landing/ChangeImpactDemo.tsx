"use client";

import { useMemo, useState } from "react";

type UpdateOption = {
  id: string;
  title: string;
  before: string;
  after: string;
};

const updates: UpdateOption[] = [
  {
    id: "eu-ai-risk",
    title: "EU AI Act: risk control wording updated",
    before: "Manual review required for all model updates before release.",
    after:
      "High-risk model updates require evidence-backed signoff; low-risk updates can follow monitored change controls.",
  },
  {
    id: "uk-operational-resilience",
    title: "UK operational resilience reporting window changed",
    before: "Incident summaries were compiled monthly for compliance ops.",
    after:
      "Critical incident summaries must be routed within 24 hours, with weekly board-level rollups retained.",
  },
  {
    id: "nydfs-third-party",
    title: "NYDFS third-party oversight language expanded",
    before: "Vendor risk attestations were tracked quarterly by procurement.",
    after:
      "Third-party attestations require mapped control evidence and escalation owners for unresolved gaps.",
  },
];

export function ChangeImpactDemo() {
  const [selected, setSelected] = useState(updates[0].id);

  const active = useMemo(() => updates.find((item) => item.id === selected) ?? updates[0], [selected]);

  return (
    <article className="vr-surface rounded-2xl border border-border/70 p-5 sm:p-6">
      <div className="mb-5">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Interactive demo</p>
        <h3 className="mt-2 text-xl font-semibold tracking-tight">Change Impact</h3>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Regulatory updates</p>
          {updates.map((item) => {
            const isActive = item.id === active.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setSelected(item.id)}
                className={`w-full rounded-xl border px-3 py-3 text-left text-sm transition-colors ${
                  isActive
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border/70 bg-background/70 text-foreground hover:bg-accent"
                }`}
              >
                {item.title}
              </button>
            );
          })}
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
          <section className="rounded-xl border border-border/70 bg-background/80 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Before</p>
            <p className="mt-2 text-sm text-muted-foreground">{active.before}</p>
          </section>
          <section className="rounded-xl border border-border/70 bg-background/80 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">After</p>
            <p className="mt-2 text-sm">{active.after}</p>
          </section>
        </div>
      </div>
    </article>
  );
}
