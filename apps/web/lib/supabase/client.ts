import { createBrowserClient } from "@supabase/ssr";
import { getPublicSupabaseEnv } from "@/lib/env";

export function createClient() {
  const { url, key, problems } = getPublicSupabaseEnv();

  if (!url || !key || problems.length > 0) {
    throw new Error(`Supabase env not configured: ${problems.join(", ")}`);
  }

  return createBrowserClient(url, key);
}
