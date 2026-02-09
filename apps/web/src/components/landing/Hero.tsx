import { Button } from "@/components/ui/button";
import Link from "next/link";

export function Hero() {
  return (
    <section className="mx-auto w-full max-w-6xl px-4 pb-16 pt-14 sm:px-6 sm:pt-20 lg:pb-24">
      <div className="grid items-center gap-12 lg:grid-cols-2">
        <div className="space-y-6">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Regulatory Intelligence Platform
          </p>
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
            Cut compliance noise.
            <br />
            Keep every change reviewable.
          </h1>
          <p className="max-w-xl text-base text-muted-foreground sm:text-lg">
            Verirule tracks policy and regulatory updates, highlights what changed, and helps teams route
            decisions with a clean audit trail.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Button asChild size="lg">
              <Link href="/auth/sign-up">Get started</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="#pricing">View pricing</Link>
            </Button>
          </div>
        </div>

        <div className="relative mx-auto h-[320px] w-full max-w-md lg:h-[360px]">
          <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-slate-100 via-background to-background shadow-sm dark:from-slate-900/30" />
          <div className="absolute left-8 top-10 w-[82%] -rotate-6 rounded-2xl border bg-card/90 p-4 shadow-md">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Policy update</p>
            <h3 className="mt-2 text-sm font-medium">California Privacy Rights Act</h3>
            <p className="mt-1 text-xs text-muted-foreground">Scope changed for third-party processors.</p>
          </div>
          <div className="absolute right-6 top-24 w-[84%] rotate-3 rounded-2xl border bg-card/95 p-4 shadow-md">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Assigned review</p>
            <h3 className="mt-2 text-sm font-medium">Legal Operations</h3>
            <p className="mt-1 text-xs text-muted-foreground">Due in 48 hours, with impact notes attached.</p>
          </div>
          <div className="absolute bottom-8 left-12 w-[78%] -rotate-1 rounded-2xl border bg-card p-4 shadow-md">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Evidence</p>
            <h3 className="mt-2 text-sm font-medium">Audit timeline complete</h3>
            <p className="mt-1 text-xs text-muted-foreground">Decision history and comments captured.</p>
          </div>
        </div>
      </div>
    </section>
  );
}
