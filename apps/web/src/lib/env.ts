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
    problems.push("Supabase key contains quotes. Remove quotes in Vercel env vars.");
  }
  if (url && url.includes('"')) {
    problems.push("Supabase URL contains quotes. Remove quotes in Vercel env vars.");
  }
  if (process.env.POSTGRES_URL || process.env.DATABASE_URL) {
    problems.push("DB credentials must not be set in web env vars");
  }

  return { url, key, problems };
}
