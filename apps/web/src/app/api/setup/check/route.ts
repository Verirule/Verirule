import { getSiteUrl, getSiteUrlConfig } from "@/lib/env";
import { createClient } from "@/lib/supabase/server";
import { connection, NextResponse } from "next/server";
import Stripe from "stripe";

type ProviderChecks = {
  google: boolean;
  github: boolean;
  apple: boolean;
  azure: boolean;
};

type SetupCheckResponse = {
  siteUrl: {
    ok: boolean;
    detail: string;
  };
  supabase: {
    ok: boolean;
    urlOk: boolean;
    authSettingsOk: boolean;
    sessionUserOk: boolean;
    providers: ProviderChecks;
    detail: string;
  };
  stripe: {
    ok: boolean;
    secretPresent: boolean;
    secretValid: boolean;
    priceProPresent: boolean;
    priceBusinessPresent: boolean;
    priceProOk: boolean;
    priceBusinessOk: boolean;
    webhookSecretPresent: boolean;
    expectedWebhookUrl: string;
    detail: string;
  };
  api: {
    configured: boolean;
    reachable: boolean;
    statusCode: number | null;
    detail: string;
  };
};

function isDebugEnabled(): boolean {
  return process.env.VERIRULE_ENABLE_DEBUG_PAGES === "true";
}

function hasQuotesOrWhitespace(value: string): boolean {
  return /['"\s]/.test(value);
}

function parseUrl(raw: string): URL | null {
  try {
    return new URL(raw);
  } catch {
    return null;
  }
}

function providerEnabled(settings: unknown, provider: string): boolean {
  if (!settings || typeof settings !== "object") {
    return false;
  }

  const external = (settings as Record<string, unknown>).external;
  if (!external || typeof external !== "object") {
    return false;
  }

  const value = (external as Record<string, unknown>)[provider];
  if (typeof value === "boolean") {
    return value;
  }

  if (!value || typeof value !== "object") {
    return false;
  }

  return (value as Record<string, unknown>).enabled === true;
}

function getProviderChecks(settings: unknown): ProviderChecks {
  return {
    google: providerEnabled(settings, "google"),
    github: providerEnabled(settings, "github"),
    apple: providerEnabled(settings, "apple"),
    azure: providerEnabled(settings, "azure") || providerEnabled(settings, "azure_oidc"),
  };
}

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal, cache: "no-store" });
  } finally {
    clearTimeout(timeout);
  }
}

async function checkSupabase(): Promise<SetupCheckResponse["supabase"]> {
  const supabaseUrlRaw = process.env.SUPABASE_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
  const supabasePublicKey =
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim() ??
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim() ??
    "";
  const providers: ProviderChecks = {
    google: false,
    github: false,
    apple: false,
    azure: false,
  };

  let urlOk = false;
  let authSettingsOk = false;
  let sessionUserOk = false;
  let detail = "";

  if (!supabaseUrlRaw) {
    detail = "Missing SUPABASE_URL or NEXT_PUBLIC_SUPABASE_URL.";
  } else if (hasQuotesOrWhitespace(supabaseUrlRaw)) {
    detail = "SUPABASE_URL contains quotes/whitespace.";
  } else {
    const parsed = parseUrl(supabaseUrlRaw);
    if (!parsed || parsed.protocol !== "https:") {
      detail = "SUPABASE_URL must be a valid https URL.";
    } else {
      urlOk = true;
      try {
        const settingsResponse = await fetchWithTimeout(
          `${parsed.origin}/auth/v1/settings`,
          {
            method: "GET",
            headers: supabasePublicKey ? { apikey: supabasePublicKey } : undefined,
          },
          4000,
        );
        authSettingsOk = settingsResponse.ok;
        if (settingsResponse.ok) {
          const body = (await settingsResponse.json().catch(() => ({}))) as unknown;
          const detected = getProviderChecks(body);
          providers.google = detected.google;
          providers.github = detected.github;
          providers.apple = detected.apple;
          providers.azure = detected.azure;
        } else {
          detail = `Supabase auth settings endpoint returned ${settingsResponse.status}.`;
        }
      } catch {
        detail = "Supabase auth settings endpoint unreachable.";
      }
    }
  }

  try {
    const supabase = await createClient();
    const { data, error } = await supabase.auth.getUser();
    sessionUserOk = !error && Boolean(data.user);
    if (error && !detail) {
      detail = "Session cookie is invalid or expired.";
    }
  } catch {
    if (!detail) {
      detail = "Supabase session check failed.";
    }
  }

  if (!detail) {
    detail = authSettingsOk
      ? "Supabase settings endpoint reachable and session is valid."
      : "Supabase check incomplete.";
  }

  return {
    ok: urlOk && authSettingsOk && sessionUserOk,
    urlOk,
    authSettingsOk,
    sessionUserOk,
    providers,
    detail,
  };
}

async function checkStripe(expectedWebhookUrl: string): Promise<SetupCheckResponse["stripe"]> {
  const secretKey = process.env.STRIPE_SECRET_KEY?.trim() ?? "";
  const pricePro = process.env.STRIPE_PRICE_PRO?.trim() ?? "";
  const priceBusiness = process.env.STRIPE_PRICE_BUSINESS?.trim() ?? "";
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET?.trim() ?? "";

  const secretPresent = Boolean(secretKey);
  const priceProPresent = Boolean(pricePro);
  const priceBusinessPresent = Boolean(priceBusiness);
  const webhookSecretPresent = Boolean(webhookSecret);

  let priceProOk = false;
  let priceBusinessOk = false;
  let secretValid = false;
  const details: string[] = [];

  if (!secretPresent) {
    details.push("Missing STRIPE_SECRET_KEY.");
  }
  if (!priceProPresent) {
    details.push("Missing STRIPE_PRICE_PRO.");
  }
  if (!priceBusinessPresent) {
    details.push("Missing STRIPE_PRICE_BUSINESS.");
  }
  if (!webhookSecretPresent) {
    details.push("Missing STRIPE_WEBHOOK_SECRET.");
  }

  if (secretPresent) {
    const stripe = new Stripe(secretKey);

    try {
      await stripe.prices.list({ limit: 1 });
      secretValid = true;
    } catch {
      details.push("STRIPE_SECRET_KEY is invalid.");
    }

    if (secretValid && priceProPresent) {
      try {
        await stripe.prices.retrieve(pricePro);
        priceProOk = true;
      } catch {
        details.push("Invalid STRIPE_PRICE_PRO.");
      }
    }

    if (secretValid && priceBusinessPresent) {
      try {
        await stripe.prices.retrieve(priceBusiness);
        priceBusinessOk = true;
      } catch {
        details.push("Invalid STRIPE_PRICE_BUSINESS.");
      }
    }
  }

  if (details.length === 0) {
    details.push("Stripe secret, prices, and webhook secret look valid.");
  }

  return {
    ok:
      secretPresent &&
      secretValid &&
      priceProPresent &&
      priceBusinessPresent &&
      priceProOk &&
      priceBusinessOk &&
      webhookSecretPresent,
    secretPresent,
    secretValid,
    priceProPresent,
    priceBusinessPresent,
    priceProOk,
    priceBusinessOk,
    webhookSecretPresent,
    expectedWebhookUrl,
    detail: details.join(" "),
  };
}

async function checkApi(): Promise<SetupCheckResponse["api"]> {
  const raw = process.env.VERIRULE_API_URL?.trim() ?? "";
  if (!raw) {
    return {
      configured: false,
      reachable: false,
      statusCode: null,
      detail: "VERIRULE_API_URL is not set.",
    };
  }

  if (hasQuotesOrWhitespace(raw)) {
    return {
      configured: true,
      reachable: false,
      statusCode: null,
      detail: "VERIRULE_API_URL contains quotes/whitespace.",
    };
  }

  const parsed = parseUrl(raw);
  if (!parsed || parsed.protocol !== "https:") {
    return {
      configured: true,
      reachable: false,
      statusCode: null,
      detail: "VERIRULE_API_URL must be a valid https URL.",
    };
  }

  try {
    const response = await fetchWithTimeout(`${parsed.origin}/healthz`, { method: "GET" }, 3500);
    return {
      configured: true,
      reachable: response.ok,
      statusCode: response.status,
      detail: response.ok
        ? "FastAPI health endpoint is reachable."
        : `FastAPI health endpoint returned ${response.status}.`,
    };
  } catch {
    return {
      configured: true,
      reachable: false,
      statusCode: null,
      detail: "FastAPI health endpoint is unreachable.",
    };
  }
}

export async function GET() {
  await connection();

  if (!isDebugEnabled()) {
    return NextResponse.json({ message: "Not found" }, { status: 404 });
  }

  const siteConfig = getSiteUrlConfig();
  const siteUrl = getSiteUrl();
  const expectedWebhookUrl = `${siteUrl}/api/stripe/webhook`;

  const [supabase, stripe, api] = await Promise.all([
    checkSupabase(),
    checkStripe(expectedWebhookUrl),
    checkApi(),
  ]);

  const payload: SetupCheckResponse = {
    siteUrl: {
      ok: siteConfig.ok,
      detail: siteConfig.detail,
    },
    supabase,
    stripe,
    api,
  };

  return NextResponse.json(payload, { status: 200 });
}
