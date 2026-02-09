import { ReactNode } from "react";

type SectionProps = {
  id?: string;
  title?: string;
  eyebrow?: string;
  children: ReactNode;
};

export function Section({ id, title, eyebrow, children }: SectionProps) {
  return (
    <section id={id} className="scroll-mt-24 py-16 sm:py-20">
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6">
        {eyebrow || title ? (
          <header className="max-w-2xl space-y-2">
            {eyebrow ? (
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                {eyebrow}
              </p>
            ) : null}
            {title ? <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h2> : null}
          </header>
        ) : null}
        <div className={eyebrow || title ? "mt-8" : ""}>{children}</div>
      </div>
    </section>
  );
}
