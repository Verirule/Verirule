"use client";

import { Button } from "@/components/ui/button";
import { useCallback, useEffect, useState } from "react";

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

function asDisplay(value: string): string {
  return value || "(empty)";
}

export default function DebugAuthPage() {
  const [data, setData] = useState<AuthCheckResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadDiagnostics = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/debug/auth-check", {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<AuthCheckResponse> & {
        message?: unknown;
      };

      if (!response.ok) {
        setError(typeof body.message === "string" ? body.message : "Unable to load auth diagnostics.");
        setData(null);
        return;
      }

      setData({
        siteUrl: typeof body.siteUrl === "string" ? body.siteUrl : "",
        supabaseUrl: typeof body.supabaseUrl === "string" ? body.supabaseUrl : "",
        urlHasWhitespace: Boolean(body.urlHasWhitespace),
        urlHasQuotes: Boolean(body.urlHasQuotes),
        keyPresent: Boolean(body.keyPresent),
        keyLength: typeof body.keyLength === "number" ? body.keyLength : 0,
        settingsFetch: {
          ok: Boolean(body.settingsFetch?.ok),
          status: typeof body.settingsFetch?.status === "number" ? body.settingsFetch.status : null,
        },
        expectedRedirect:
          typeof body.expectedRedirect === "string" ? body.expectedRedirect : "/auth/callback",
      });
    } catch {
      setError("Unable to load auth diagnostics.");
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDiagnostics();
  }, [loadDiagnostics]);

  return (
    <main className="min-h-screen px-4 py-10 sm:px-6">
      <div className="mx-auto w-full max-w-3xl space-y-6">
        <header className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">Auth diagnostics</h1>
          <p className="text-sm text-muted-foreground">
            Diagnose Supabase signup/login redirect issues without exposing secrets.
          </p>
        </header>

        <section className="rounded-xl border bg-card p-5 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold">Checks</h2>
            <Button type="button" variant="outline" size="sm" onClick={() => void loadDiagnostics()} disabled={isLoading}>
              {isLoading ? "Refreshing..." : "Refresh"}
            </Button>
          </div>

          {isLoading ? <p className="text-sm text-muted-foreground">Loading diagnostics...</p> : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          {!isLoading && data ? (
            <ul className="space-y-2 text-sm">
              <li>
                <span className="font-medium">NEXT_PUBLIC_SITE_URL:</span>{" "}
                <code className="break-all">{asDisplay(data.siteUrl)}</code>
              </li>
              <li>
                <span className="font-medium">NEXT_PUBLIC_SUPABASE_URL:</span>{" "}
                <code className="break-all">{asDisplay(data.supabaseUrl)}</code>
              </li>
              <li>
                <span className="font-medium">NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY present:</span>{" "}
                {String(data.keyPresent)}
              </li>
              <li>
                <span className="font-medium">NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY length:</span> {data.keyLength}
              </li>
              <li>
                <span className="font-medium">URL contains whitespace:</span> {String(data.urlHasWhitespace)}
              </li>
              <li>
                <span className="font-medium">URL contains surrounding quotes:</span> {String(data.urlHasQuotes)}
              </li>
              <li>
                <span className="font-medium">Supabase settings fetch:</span>{" "}
                {data.settingsFetch.ok ? "ok" : "failed"}{" "}
                {data.settingsFetch.status !== null ? `(status ${data.settingsFetch.status})` : "(no status)"}
              </li>
              <li>
                <span className="font-medium">Expected redirect URL:</span>{" "}
                <code className="break-all">{data.expectedRedirect}</code>
              </li>
            </ul>
          ) : null}
        </section>

        {data?.urlHasQuotes || data?.urlHasWhitespace ? (
          <section className="rounded-xl border bg-card p-5">
            <h2 className="text-base font-semibold">Fix</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Remove quotes and whitespace from `NEXT_PUBLIC_SITE_URL` and `NEXT_PUBLIC_SUPABASE_URL` in Vercel
              Environment Variables, then redeploy.
            </p>
          </section>
        ) : null}

        {data && !data.settingsFetch.ok ? (
          <section className="rounded-xl border bg-card p-5">
            <h2 className="text-base font-semibold">Fix</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Supabase auth settings check failed. This usually means the Supabase URL is wrong or there is a network
              connectivity problem between Vercel and Supabase.
            </p>
          </section>
        ) : null}
      </div>
    </main>
  );
}
