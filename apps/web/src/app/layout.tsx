import type { Metadata } from "next";
import { AccentThemeManager } from "@/src/components/theme/AccentThemeManager";
import { ThemeProvider } from "@/src/components/theme/ThemeProvider";
import { getSiteUrl } from "@/lib/env";
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
  description: "Enterprise compliance monitoring, workflow management, and audit-ready evidence tracking.",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }],
    shortcut: "/icon.svg",
    apple: [{ url: "/icon.svg", type: "image/svg+xml" }],
  },
  openGraph: {
    type: "website",
    title: "Verirule",
    description: "Enterprise compliance monitoring, workflow management, and audit-ready evidence tracking.",
    url: siteUrl,
    siteName: "Verirule",
    images: [{ url: "/opengraph-image", width: 1200, height: 630, alt: "Verirule logo" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Verirule",
    description: "Enterprise compliance monitoring, workflow management, and audit-ready evidence tracking.",
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
      <body className="font-sans antialiased">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationJsonLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteJsonLd) }}
        />
        <ThemeProvider>{children}</ThemeProvider>
        <AccentThemeManager />
      </body>
    </html>
  );
}
