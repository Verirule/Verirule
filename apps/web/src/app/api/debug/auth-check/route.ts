import { connection, NextResponse } from "next/server";

type AuthCheckResponse = {
  siteUrl: string;
  supabaseUrl: string;
  urlHasWhitespace: boolean;
  urlHasQuotes: boolean;
  keyPresent: boolean;
  keyLength: number;
  settingsFetch: {
    ok: boolean;
    status: number | null;
  };
  expectedRedirect: string;
};

function isDebugEnabled(): boolean {
  return process.env.VERIRULE_ENABLE_DEBUG_PAGES === "true";
}

function hasSurroundingQuotes(value: string): boolean {
  const trimmed = value.trim();
  return (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  );
}

function hasWhitespace(value: string): boolean {
  return /\s/.test(value);
}

function isValidSupabaseUrl(value: string): boolean {
  return /^https:\/\/[a-z0-9-]+\.supabase\.co$/i.test(value);
}

export async function GET() {
  await connection();

  if (!isDebugEnabled()) {
    return NextResponse.json({ message: "Not found" }, { status: 404 });
  }

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "";
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "";

  const urlHasWhitespace = hasWhitespace(siteUrl) || hasWhitespace(supabaseUrl);
  const urlHasQuotes = hasSurroundingQuotes(siteUrl) || hasSurroundingQuotes(supabaseUrl);
  const keyPresent = publishableKey.length > 0;
  const keyLength = publishableKey.length;

  let settingsFetch: AuthCheckResponse["settingsFetch"] = {
    ok: false,
    status: null,
  };

  const normalizedSupabaseUrl = supabaseUrl.trim();
  if (!urlHasWhitespace && !urlHasQuotes && isValidSupabaseUrl(normalizedSupabaseUrl)) {
    try {
      const response = await fetch(`${normalizedSupabaseUrl}/auth/v1/settings`, {
        method: "GET",
        headers: keyPresent ? { apikey: publishableKey } : undefined,
        cache: "no-store",
      });
      settingsFetch = {
        ok: response.ok,
        status: response.status,
      };
    } catch {
      settingsFetch = {
        ok: false,
        status: null,
      };
    }
  }

  const expectedRedirect = siteUrl ? `${siteUrl}/auth/callback` : "/auth/callback";

  const payload: AuthCheckResponse = {
    siteUrl,
    supabaseUrl,
    urlHasWhitespace,
    urlHasQuotes,
    keyPresent,
    keyLength,
    settingsFetch,
    expectedRedirect,
  };

  return NextResponse.json(payload, { status: 200 });
}
