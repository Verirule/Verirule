import type { Metadata } from "next";
import { Manrope, Space_Grotesk } from "next/font/google";
import { AccentThemeManager } from "@/src/components/theme/AccentThemeManager";
import { ThemeProvider } from "@/src/components/theme/ThemeProvider";
import { getSiteUrl } from "@/lib/env";
import "./globals.css";

const siteUrl = getSiteUrl().replace(/\/$/, "");
const metadataBase = new URL(siteUrl);

export const metadata: Metadata = {
  metadataBase,
  title: {
    default: "Verirule",
    template: "%s | Verirule",
  },
  description: "Audit-ready regulatory monitoring, workflows, and evidence operations.",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [{ url: "/brand/icon.svg", type: "image/svg+xml" }],
    shortcut: "/brand/icon.svg",
    apple: [{ url: "/brand/icon.svg", type: "image/svg+xml" }],
  },
  openGraph: {
    type: "website",
    title: "Verirule",
    description: "Audit-ready regulatory monitoring, workflows, and evidence operations.",
    url: siteUrl,
    siteName: "Verirule",
    images: [{ url: "/opengraph-image", width: 1200, height: 630, alt: "Verirule logo" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Verirule",
    description: "Audit-ready regulatory monitoring, workflows, and evidence operations.",
    images: ["/twitter-image"],
  },
};

const manrope = Manrope({
  variable: "--font-body",
  display: "swap",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-display",
  display: "swap",
  subsets: ["latin"],
});

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
    logo: `${siteUrl}/brand/icon.svg`,
  };

  const websiteJsonLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "Verirule",
    url: siteUrl,
  };

  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${manrope.className} ${manrope.variable} ${spaceGrotesk.variable} antialiased`}>
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
