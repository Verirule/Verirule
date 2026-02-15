import Link from "next/link";

import { Section } from "@/src/components/marketing/Section";

const plans = [
  {
    name: "Free",
    price: "$0",
    cadence: "per month",
    detail: "For teams starting a compliance program with real monitoring needs.",
    features: ["Up to 2 users", "Core monitoring and alerts", "Basic task and evidence tracking", "Manual export generation"],
    cta: "Start free",
    href: "/auth/sign-up",
    featured: false,
  },
  {
    name: "Pro",
    price: "$99",
    cadence: "per org / month",
    detail: "For growing teams that need higher throughput and deeper workflow controls.",
    features: ["Up to 10 users", "Slack and Jira integrations", "Automated workflow rules", "Priority support"],
    cta: "Choose Pro",
    href: "/auth/sign-up",
    featured: true,
  },
  {
    name: "Business",
    price: "Custom",
    cadence: "annual contract",
    detail: "For enterprises requiring advanced governance and procurement support.",
    features: ["Unlimited users", "SAML SSO and role controls", "Dedicated onboarding", "Custom security review support"],
    cta: "Contact sales",
    href: "/auth/sign-up",
    featured: false,
  },
] as const;

export function Pricing() {
  return (
    <Section id="pricing">
      <div className="mb-8 max-w-3xl">
        <h2 className="text-3xl font-semibold text-white sm:text-4xl">Pricing</h2>
        <p className="mt-3 text-base text-[#b6c4df]">
          Transparent tiers with a usable free plan and no hidden trial constraints.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {plans.map((plan) => (
          <article
            key={plan.name}
            className={[
              "flex h-full flex-col rounded-xl border p-6",
              plan.featured ? "border-[#4f77d6] bg-[#13274a]" : "border-[#2b3f62] bg-[#111d34]",
            ].join(" ")}
          >
            <h3 className="text-xl font-semibold text-white">{plan.name}</h3>
            <p className="mt-3 text-3xl font-semibold text-white">{plan.price}</p>
            <p className="text-sm text-[#aab8d6]">{plan.cadence}</p>
            <p className="mt-3 text-sm text-[#b7c4dc] sm:text-base">{plan.detail}</p>
            <ul className="mt-4 space-y-2 text-sm text-[#d5dff2]">
              {plan.features.map((feature) => (
                <li key={feature}>- {feature}</li>
              ))}
            </ul>
            <div className="mt-6">
              <Link
                href={plan.href}
                className={[
                  "inline-flex rounded-md px-4 py-2 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]",
                  plan.featured
                    ? "bg-[#3e6ef4] text-white hover:bg-[#2f5dd9]"
                    : "border border-[#3a5277] bg-[#0f1a2f] text-[#d9e4fb] hover:border-[#6285c6] hover:text-white",
                ].join(" ")}
              >
                {plan.cta}
              </Link>
            </div>
          </article>
        ))}
      </div>
    </Section>
  );
}
