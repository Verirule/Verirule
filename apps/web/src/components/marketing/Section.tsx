import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type SectionProps = {
  id?: string;
  className?: string;
  containerClassName?: string;
  children: ReactNode;
};

export function Section({ id, className, containerClassName, children }: SectionProps) {
  return (
    <section id={id} className={cn("border-t border-[#233656]", className)}>
      <div className={cn("mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 lg:px-8 lg:py-20", containerClassName)}>{children}</div>
    </section>
  );
}
