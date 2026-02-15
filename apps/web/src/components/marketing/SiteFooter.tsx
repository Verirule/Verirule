import Image from "next/image";
import Link from "next/link";

import { SocialIcons } from "@/src/components/SocialIcons";

const linkGroups = [
  {
    title: "Product",
    links: [
      { label: "Monitoring", href: "#product" },
      { label: "Integrations", href: "#resources" },
      { label: "Pricing", href: "#pricing" },
      { label: "Security", href: "#security" },
      { label: "FAQ", href: "#faq" },
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
    <footer className="border-t border-[#2E7DB5] bg-[#082E4E]">
      <div className="mx-auto grid w-full max-w-6xl gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[1fr_auto_auto] lg:px-8">
        <div className="space-y-4">
          <Link href="/" className="inline-flex items-center rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8CC9FF]">
            <span className="vr-brand-chip h-12 w-12">
              <Image
                src="/logo.svg"
                alt="Verirule"
                width={320}
                height={84}
                className="h-full w-full object-contain"
              />
            </span>
          </Link>
          <p className="max-w-sm text-sm text-[#D4EAFF]">
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
                    className="text-sm text-[#D4EAFF] transition-colors hover:text-[#9ED4FF] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8CC9FF]"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-[#2E7DB5] px-4 py-4 text-center text-xs text-[#A8D3F7] sm:px-6 lg:px-8">
        (c) Verirule. All rights reserved.
      </div>
    </footer>
  );
}
