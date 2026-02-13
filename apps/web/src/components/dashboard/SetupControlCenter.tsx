"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useEffect, useMemo, useState } from "react";

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

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`rounded px-2 py-1 text-xs font-medium ${
        ok ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
      }`}
    >
      {label}: {ok ? "ok" : "failed"}
    </span>
  );
}

function FixLine({ value }: { value: string }) {
  return (
    <code className="block rounded bg-muted px-2 py-1 text-xs text-foreground/90 break-all">
      {value}
    </code>
  );
}

export function SetupControlCenter() {
  const [data, setData] = useState<SetupCheckResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadChecks = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/setup/check", { method: "GET", cache: "no-store" });
      const body = (await response.json().catch(() => ({}))) as SetupCheckResponse & {
        message?: unknown;
      };

      if (!response.ok) {
        const message =
          typeof body.message === "string" ? body.message : "Unable to load setup checks.";
        setError(message);
        return;
      }

      setData(body);
    } catch {
      setError("Unable to load setup checks.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadChecks();
  }, []);

  const providerRows = useMemo(() => {
    if (!data) return [];
    return [
      { key: "google", enabled: data.supabase.providers.google },
      { key: "github", enabled: data.supabase.providers.github },
      { key: "apple", enabled: data.supabase.providers.apple },
      { key: "azure", enabled: data.supabase.providers.azure },
    ];
  }, [data]);

  return (
    <div className="space-y-6">
      <section className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Setup Control Center</h1>
          <Button type="button" variant="outline" size="sm" onClick={() => void loadChecks()} disabled={loading}>
            {loading ? "Checking..." : "Run checks"}
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          Validate Supabase, OAuth providers, Stripe billing, and optional FastAPI wiring.
        </p>
      </section>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {loading && !data ? <p className="text-sm text-muted-foreground">Running setup checks...</p> : null}

      {data ? (
        <>
          <Card className="border-border/70">
            <CardHeader>
              <CardTitle>Site URL</CardTitle>
              <CardDescription>Canonical redirect base URL for auth and billing.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <StatusPill ok={data.siteUrl.ok} label="siteUrl" />
              <p className="text-muted-foreground">{data.siteUrl.detail}</p>
              {!data.siteUrl.ok ? <FixLine value="NEXT_PUBLIC_SITE_URL=https://www.verirule.com" /> : null}
            </CardContent>
          </Card>

          <Card className="border-border/70">
            <CardHeader>
              <CardTitle>Supabase</CardTitle>
              <CardDescription>Auth settings endpoint, providers, and session cookie check.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex flex-wrap gap-2">
                <StatusPill ok={data.supabase.ok} label="supabase" />
                <StatusPill ok={data.supabase.urlOk} label="url" />
                <StatusPill ok={data.supabase.authSettingsOk} label="auth settings" />
                <StatusPill ok={data.supabase.sessionUserOk} label="session" />
              </div>
              <p className="text-muted-foreground">{data.supabase.detail}</p>
              <div className="space-y-1">
                {providerRows.map((provider) => (
                  <p key={provider.key} className="text-xs">
                    {provider.key}: {provider.enabled ? "enabled" : "disabled"}
                  </p>
                ))}
              </div>
              {!data.supabase.urlOk ? (
                <>
                  <FixLine value="SUPABASE_URL=https://<project-ref>.supabase.co" />
                  <FixLine value="NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co" />
                </>
              ) : null}
              {!data.supabase.authSettingsOk ? (
                <FixLine value="Verify <SUPABASE_URL>/auth/v1/settings is reachable from deployment." />
              ) : null}
              {!data.supabase.sessionUserOk ? (
                <FixLine value="Sign out, then sign in again to refresh auth cookies." />
              ) : null}
            </CardContent>
          </Card>

          <Card className="border-border/70">
            <CardHeader>
              <CardTitle>Stripe + Billing</CardTitle>
              <CardDescription>Keys, price IDs, and webhook baseline configuration.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex flex-wrap gap-2">
                <StatusPill ok={data.stripe.ok} label="stripe" />
                <StatusPill ok={data.stripe.secretPresent} label="secret" />
                <StatusPill ok={data.stripe.secretValid} label="secret validity" />
                <StatusPill ok={data.stripe.priceProOk} label="pro price" />
                <StatusPill ok={data.stripe.priceBusinessOk} label="business price" />
                <StatusPill ok={data.stripe.webhookSecretPresent} label="webhook secret" />
              </div>
              <p className="text-muted-foreground">{data.stripe.detail}</p>
              <FixLine value={`Webhook URL expected: ${data.stripe.expectedWebhookUrl}`} />
              {!data.stripe.secretPresent ? <FixLine value="STRIPE_SECRET_KEY=sk_live_..." /> : null}
              {data.stripe.secretPresent && !data.stripe.secretValid ? (
                <FixLine value="Replace STRIPE_SECRET_KEY with a valid Stripe secret key." />
              ) : null}
              {!data.stripe.priceProPresent ? <FixLine value="STRIPE_PRICE_PRO=price_..." /> : null}
              {!data.stripe.priceBusinessPresent ? (
                <FixLine value="STRIPE_PRICE_BUSINESS=price_..." />
              ) : null}
              {data.stripe.priceProPresent && !data.stripe.priceProOk ? (
                <FixLine value="Set STRIPE_PRICE_PRO to a valid recurring Stripe Price ID." />
              ) : null}
              {data.stripe.priceBusinessPresent && !data.stripe.priceBusinessOk ? (
                <FixLine value="Set STRIPE_PRICE_BUSINESS to a valid recurring Stripe Price ID." />
              ) : null}
              {!data.stripe.webhookSecretPresent ? (
                <FixLine value="STRIPE_WEBHOOK_SECRET=whsec_..." />
              ) : null}
            </CardContent>
          </Card>

          <Card className="border-border/70">
            <CardHeader>
              <CardTitle>FastAPI</CardTitle>
              <CardDescription>Optional API health check for VERIRULE_API_URL.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex flex-wrap gap-2">
                <StatusPill ok={data.api.configured} label="configured" />
                <StatusPill ok={data.api.reachable} label="reachable" />
              </div>
              <p className="text-muted-foreground">
                {data.api.detail}
                {data.api.statusCode !== null ? ` (status ${data.api.statusCode})` : ""}
              </p>
              {!data.api.configured ? (
                <FixLine value="VERIRULE_API_URL=https://<your-fastapi-domain>" />
              ) : null}
              {data.api.configured && !data.api.reachable ? (
                <FixLine value="Verify VERIRULE_API_URL and ensure /healthz responds with 200." />
              ) : null}
            </CardContent>
          </Card>

          <Card className="border-border/70">
            <CardHeader>
              <CardTitle>Where to fix</CardTitle>
              <CardDescription>Primary consoles for each setup domain.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>Supabase: Auth - URL Configuration, Providers, and Email Templates.</p>
              <p>Vercel: Environment Variables for web deployment.</p>
              <p>Stripe: Developers - API keys, Webhooks, and Products/Prices.</p>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
