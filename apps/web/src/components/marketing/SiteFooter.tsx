import Link from "next/link";

import { SocialIcons } from "@/src/components/SocialIcons";

const linkGroups = [
  {
    title: "Product",
    links: [
      { label: "Monitoring", href: "#product" },
      { label: "Pricing", href: "#pricing" },
      { label: "Security", href: "#security" },
      { label: "Resources", href: "#resources" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "Privacy", href: "/privacy" },
      { label: "Terms", href: "/terms" },
      { label: "Policy", href: "/policy" },
      { label: "Service", href: "/service" },
    ],
  },
] as const;

export function SiteFooter() {
  return (
    <footer className="border-t border-[#233656] bg-[#0a1424]">
      <div className="mx-auto grid w-full max-w-6xl gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[1fr_auto_auto] lg:px-8">
        <div className="space-y-4">
          <Link href="/" className="inline-flex items-center rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]">
            <img src="/logo.svg" alt="Verirule" className="h-8 w-auto" />
          </Link>
          <p className="max-w-sm text-sm text-[#b7c4dc]">
            Compliance monitoring and workflow evidence for teams operating in regulated environments.
          </p>
          <SocialIcons />
        </div>

        {linkGroups.map((group) => (
          <div key={group.title}>
            <p className="text-sm font-semibold text-white">{group.title}</p>
            <ul className="mt-3 space-y-2">
              {group.links.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    className="text-sm text-[#b7c4dc] transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86aefc]"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-[#233656] px-4 py-4 text-center text-xs text-[#8fa4c8] sm:px-6 lg:px-8">
        (c) Verirule. All rights reserved.
      </div>
    </footer>
  );
}
