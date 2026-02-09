import { Button } from "@/components/ui/button";
import Link from "next/link";

const tiers = [
  {
    name: "Free",
    price: "$0",
    cadence: "forever",
    bullets: ["Single workspace", "Core monitoring feeds", "Basic alert routing"],
    cta: "Start free",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$99",
    cadence: "per month",
    bullets: ["Multi-workspace support", "Change diff prioritization", "Audit export and history"],
    cta: "Upgrade",
    highlighted: true,
  },
  {
    name: "Business",
    price: "Custom",
    cadence: "annual plans",
    bullets: ["SAML and enterprise controls", "Dedicated onboarding", "Advanced governance options"],
    cta: "Start free",
    highlighted: false,
  },
];

export function Pricing() {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {tiers.map((tier) => (
        <article
          key={tier.name}
          className={`rounded-2xl border bg-card/80 p-6 ${
            tier.highlighted ? "ring-2 ring-foreground/20 shadow-sm" : ""
          }`}
        >
          <h3 className="text-lg font-semibold">{tier.name}</h3>
          <p className="mt-1 text-3xl font-semibold tracking-tight">{tier.price}</p>
          <p className="mt-1 text-sm text-muted-foreground">{tier.cadence}</p>
          <ul className="mt-5 space-y-2 text-sm text-muted-foreground">
            {tier.bullets.map((bullet) => (
              <li key={bullet}>- {bullet}</li>
            ))}
          </ul>
          <Button asChild className="mt-6 w-full" variant={tier.highlighted ? "default" : "outline"}>
            <Link href="/auth/sign-up">{tier.cta}</Link>
          </Button>
        </article>
      ))}
    </div>
  );
}
