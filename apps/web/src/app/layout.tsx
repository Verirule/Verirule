import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { AccentThemeManager } from "@/src/components/theme/AccentThemeManager";
import { ThemeProvider } from "@/src/components/theme/ThemeProvider";
import "./globals.css";

const metadataBase = process.env.NEXT_PUBLIC_SITE_URL
  ? new URL(process.env.NEXT_PUBLIC_SITE_URL)
  : process.env.VERCEL_URL
    ? new URL(`https://${process.env.VERCEL_URL}`)
    : undefined;

export const metadata: Metadata = {
  metadataBase,
  title: "Verirule",
  description: "Vertical AI SaaS for compliance monitoring",
};

const inter = Inter({
  variable: "--font-inter",
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
      <body className={`${inter.className} antialiased`}>
        <ThemeProvider>{children}</ThemeProvider>
        <AccentThemeManager />
      </body>
    </html>
  );
}
