import type { Metadata } from "next";
import { Manrope, Space_Grotesk } from "next/font/google";
import { AccentThemeManager } from "@/src/components/theme/AccentThemeManager";
import { ThemeProvider } from "@/src/components/theme/ThemeProvider";
import { getSiteUrl } from "@/lib/env";
import "./globals.css";

const metadataBase = new URL(getSiteUrl());

export const metadata: Metadata = {
  metadataBase,
  title: "Verirule",
  description: "Regulatory monitoring and audit evidence workflow platform",
  icons: {
    icon: [{ url: "/brand/icon.svg", type: "image/svg+xml" }],
    shortcut: "/brand/icon.svg",
    apple: "/brand/icon.svg",
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
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${manrope.className} ${manrope.variable} ${spaceGrotesk.variable} antialiased`}>
        <ThemeProvider>{children}</ThemeProvider>
        <AccentThemeManager />
      </body>
    </html>
  );
}
