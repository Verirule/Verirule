import { getSiteUrl } from "@/lib/env";
import { createClient } from "@/lib/supabase/server";
import { type EmailOtpType } from "@supabase/supabase-js";
import { redirect } from "next/navigation";
import { type NextRequest } from "next/server";

function getValidatedNextRedirect(request: NextRequest) {
  const requestUrl = new URL(request.url);
  const nextParam = requestUrl.searchParams.get("next");
  const siteUrl = getSiteUrl(request);
  const defaultRedirect = `${siteUrl}/dashboard`;

  if (!nextParam) {
    return defaultRedirect;
  }

  try {
    const defaultOrigin = new URL(siteUrl).origin;
    const candidate = new URL(nextParam, siteUrl);
    if (candidate.origin === defaultOrigin) {
      return candidate.toString();
    }
  } catch {
    // Fall through to default if URL parsing fails.
  }

  return defaultRedirect;
}

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get("code");
  const tokenHash = requestUrl.searchParams.get("token_hash");
  const type = requestUrl.searchParams.get("type") as EmailOtpType | null;
  const next = getValidatedNextRedirect(request);
  const supabase = await createClient();

  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      redirect(next);
    }
    redirect(`/auth/error?error=${encodeURIComponent(error.message)}`);
  }

  if (tokenHash && type) {
    const { error } = await supabase.auth.verifyOtp({
      type,
      token_hash: tokenHash,
    });
    if (!error) {
      redirect(next);
    }
    redirect(`/auth/error?error=${encodeURIComponent(error.message)}`);
  }

  redirect("/auth/error?error=Missing+auth+callback+parameters");
}
