import type { Metadata } from "next";
import { getSiteUrl } from "@/lib/env";
import { ThemeProvider } from "@/src/components/theme/ThemeProvider";
import { ThemeToggle } from "@/src/components/theme/ThemeToggle";
import "./globals.css";

const siteUrl = getSiteUrl().replace(/\/$/, "");
const metadataBase = new URL(siteUrl);

export const metadata: Metadata = {
  metadataBase,
  alternates: {
    canonical: "/",
  },
  title: {
    default: "Verirule",
    template: "%s | Verirule",
  },
  description:
    "Compliance operations workspace for controls, findings, readiness, alerts, tasks, and audit evidence.",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }],
    shortcut: "/icon.svg",
    apple: [{ url: "/icon.svg", type: "image/svg+xml" }],
  },
  openGraph: {
    type: "website",
    title: "Verirule",
    description:
      "Compliance operations workspace for controls, findings, readiness, alerts, tasks, and audit evidence.",
    url: siteUrl,
    siteName: "Verirule",
    images: [{ url: "/opengraph-image", width: 1200, height: 630, alt: "Verirule logo" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Verirule",
    description:
      "Compliance operations workspace for controls, findings, readiness, alerts, tasks, and audit evidence.",
    images: ["/twitter-image"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const organizationJsonLd = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "Verirule",
    url: siteUrl,
    logo: `${siteUrl}/logo.svg`,
  };

  const websiteJsonLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "Verirule",
    url: siteUrl,
  };

  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <ThemeProvider>
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationJsonLd) }}
          />
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteJsonLd) }}
          />
          {children}
          <ThemeToggle className="fixed bottom-4 right-4 z-[60] inline-flex h-10 w-10 items-center justify-center rounded-full border border-border bg-card text-card-foreground shadow-md" />
        </ThemeProvider>
      </body>
    </html>
  );
}
