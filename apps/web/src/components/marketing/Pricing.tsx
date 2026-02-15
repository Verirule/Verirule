import Link from "next/link";

import { getPlanDisplayPrice, getPlanIncludedItems, type BillingPlan } from "@/src/lib/billing";
import { Section } from "@/src/components/marketing/Section";

const plans: Array<{ plan: BillingPlan; name: string; cta: string }> = [
  { plan: "free", name: "Free", cta: "Start free" },
  { plan: "pro", name: "Pro", cta: "Choose Pro" },
  { plan: "business", name: "Business", cta: "Choose Business" },
];

export function Pricing() {
  return (
    <Section id="pricing">
      <div className="mb-8 max-w-3xl">
        <h2 className="text-3xl font-semibold text-slate-900 sm:text-4xl">Pricing</h2>
        <p className="mt-3 text-base text-slate-600">Clear monthly plans with limits aligned to workspace entitlements.</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {plans.map((plan) => {
          const displayPrice = getPlanDisplayPrice(plan.plan);
          const included = getPlanIncludedItems(plan.plan);

          return (
            <article key={plan.name} className="flex h-full flex-col rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="text-xl font-semibold text-slate-900">{plan.name}</h3>
              {displayPrice ? (
                <p className="mt-3 text-3xl font-semibold text-slate-900">
                  {displayPrice}
                  <span className="ml-1 text-sm font-medium text-slate-500">/mo</span>
                </p>
              ) : (
                <p className="mt-3 text-2xl font-semibold text-slate-900">{plan.name}</p>
              )}
              <ul className="mt-4 space-y-2 text-sm text-slate-600">
                {included.map((feature) => (
                  <li key={feature} className="flex items-start gap-2">
                    <span className="pt-0.5 text-blue-600">&bull;</span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-6">
                <Link
                  href="/auth/sign-up"
                  className="inline-flex rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700"
                >
                  {plan.cta}
                </Link>
              </div>
            </article>
          );
        })}
      </div>
    </Section>
  );
}
