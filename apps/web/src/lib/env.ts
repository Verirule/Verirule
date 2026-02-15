import type { NextRequest } from "next/server";

const CANONICAL_SITE_URL = "https://www.verirule.com";
const warnedSiteMessages = new Set<string>();

function warnSiteConfig(message: string): void {
  if (warnedSiteMessages.has(message)) {
    return;
  }
  warnedSiteMessages.add(message);
  console.warn(message);
}

export function getPublicSupabaseEnv() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key =
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  // Basic validation (no secrets here, both are public keys)
  const problems: string[] = [];
  if (!url) problems.push("NEXT_PUBLIC_SUPABASE_URL is missing");
  if (url && !url.startsWith("https://")) {
    problems.push("NEXT_PUBLIC_SUPABASE_URL must start with https://");
  }
  if (!key) {
    problems.push(
      "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY or NEXT_PUBLIC_SUPABASE_ANON_KEY is missing",
    );
  }
  if (key && key.includes('"')) {
    problems.push("Supabase key contains quotes. Remove quotes in deployment environment variables.");
  }
  if (url && url.includes('"')) {
    problems.push("Supabase URL contains quotes. Remove quotes in deployment environment variables.");
  }
  if (process.env.POSTGRES_URL || process.env.DATABASE_URL) {
    problems.push("DB credentials must not be set in web env vars");
  }

  return { url, key, problems };
}

type SiteUrlConfig = {
  siteUrl: string;
  detail: string;
  ok: boolean;
  warnings: string[];
};

export function getSiteUrlConfig(): SiteUrlConfig {
  const raw = process.env.NEXT_PUBLIC_SITE_URL;
  const warnings: string[] = [];

  if (!raw) {
    warnings.push(`NEXT_PUBLIC_SITE_URL is missing; using ${CANONICAL_SITE_URL}.`);
    return {
      siteUrl: CANONICAL_SITE_URL,
      detail: warnings[0],
      ok: false,
      warnings,
    };
  }

  const trimmed = raw.trim();
  if (trimmed.length === 0) {
    warnings.push(`NEXT_PUBLIC_SITE_URL is empty; using ${CANONICAL_SITE_URL}.`);
    return {
      siteUrl: CANONICAL_SITE_URL,
      detail: warnings[0],
      ok: false,
      warnings,
    };
  }
  if (trimmed !== raw) {
    warnings.push("NEXT_PUBLIC_SITE_URL contains leading/trailing whitespace; using canonical URL.");
  }
  if (/['"]/.test(trimmed)) {
    warnings.push("NEXT_PUBLIC_SITE_URL contains quotes; using canonical URL.");
  }
  if (/\s/.test(trimmed)) {
    warnings.push("NEXT_PUBLIC_SITE_URL contains whitespace; using canonical URL.");
  }

  if (warnings.length > 0) {
    return {
      siteUrl: CANONICAL_SITE_URL,
      detail: warnings.join(" "),
      ok: false,
      warnings,
    };
  }

  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    warnings.push(`NEXT_PUBLIC_SITE_URL is not a valid URL; using ${CANONICAL_SITE_URL}.`);
    return {
      siteUrl: CANONICAL_SITE_URL,
      detail: warnings[0],
      ok: false,
      warnings,
    };
  }

  if (parsed.protocol !== "https:" && parsed.hostname !== "localhost") {
    warnings.push("NEXT_PUBLIC_SITE_URL must use https (localhost allowed only for local dev); using canonical URL.");
  }

  if (warnings.length > 0) {
    return {
      siteUrl: CANONICAL_SITE_URL,
      detail: warnings.join(" "),
      ok: false,
      warnings,
    };
  }

  return {
    siteUrl: parsed.origin,
    detail: `Using ${parsed.origin}.`,
    ok: true,
    warnings: [],
  };
}

function getRequestOrigin(req?: NextRequest): string | null {
  if (!req) {
    return null;
  }

  const candidate = req.nextUrl.origin?.trim();
  if (!candidate) {
    return null;
  }

  try {
    const parsed = new URL(candidate);
    if (parsed.protocol === "https:" || parsed.hostname === "localhost") {
      return parsed.origin;
    }
  } catch {
    return null;
  }

  return null;
}

export function getSiteUrl(req?: NextRequest) {
  const config = getSiteUrlConfig();
  config.warnings.forEach((warning) => warnSiteConfig(warning));
  if (config.ok) {
    return config.siteUrl;
  }

  const requestOrigin = getRequestOrigin(req);
  if (requestOrigin) {
    warnSiteConfig(`Using request origin fallback for site URL: ${requestOrigin}.`);
    return requestOrigin;
  }

  return config.siteUrl;
}
