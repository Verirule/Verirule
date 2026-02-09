"use client";

import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";
import { getPublicSupabaseEnv } from "@/lib/env";
import { useMemo, useState } from "react";

function safeErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown error";
}

export default function DebugAuthPage() {
  const { url, key, problems } = useMemo(() => getPublicSupabaseEnv(), []);
  const [connectionStatus, setConnectionStatus] = useState<string | null>(null);
  const [signupStatus, setSignupStatus] = useState<string | null>(null);
  const [rawFetchStatus, setRawFetchStatus] = useState<string | null>(null);
  const [isCheckingConnection, setIsCheckingConnection] = useState(false);
  const [isTestingSignup, setIsTestingSignup] = useState(false);
  const [isTestingRawFetch, setIsTestingRawFetch] = useState(false);

  const supabaseUrl = url ?? "";
  const urlHasQuotes = /['"]/.test(supabaseUrl);
  const urlHasWhitespace = /\s/.test(supabaseUrl);
  const keyPresent = Boolean(key);
  const keyLength = key?.length ?? 0;

  const handleTestConnection = async () => {
    setIsCheckingConnection(true);
    setConnectionStatus(null);
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.getSession();
      if (error) {
        setConnectionStatus(`Connection error: ${error.message}`);
        return;
      }
      setConnectionStatus("Connection check succeeded.");
    } catch (error) {
      const message = safeErrorMessage(error);
      console.error("debug/auth connection test failed", { message });
      setConnectionStatus(`Connection error: ${message}`);
    } finally {
      setIsCheckingConnection(false);
    }
  };

  const handleTestSignUp = async () => {
    setIsTestingSignup(true);
    setSignupStatus(null);
    try {
      const supabase = createClient();
      const testEmail = `test+${Date.now()}@example.com`;
      const { error } = await supabase.auth.signUp({
        email: testEmail,
        password: "DebugPassword123!",
      });

      if (error) {
        setSignupStatus(`Sign up error: ${error.message}`);
        return;
      }
      setSignupStatus("Sign up request accepted.");
    } catch (error) {
      const message = safeErrorMessage(error);
      console.error("debug/auth signup test failed", { message });
      setSignupStatus(`Sign up error: ${message}`);
    } finally {
      setIsTestingSignup(false);
    }
  };

  const handleTestRawFetch = async () => {
    setIsTestingRawFetch(true);
    setRawFetchStatus(null);

    try {
      if (!supabaseUrl) {
        setRawFetchStatus("Raw fetch error: Missing Supabase URL.");
        return;
      }

      const response = await fetch(`${supabaseUrl}/auth/v1/`, { method: "GET" });
      setRawFetchStatus(`Raw fetch status: ${response.status}`);
    } catch (error) {
      const message = safeErrorMessage(error);
      const errorName = error instanceof Error ? error.name : "UnknownError";
      setRawFetchStatus(`Raw fetch error (${errorName}): ${message}`);
    } finally {
      setIsTestingRawFetch(false);
    }
  };

  return (
    <main className="min-h-screen px-4 py-10 sm:px-6">
      <div className="mx-auto w-full max-w-3xl space-y-8">
        <header className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">Auth diagnostics</h1>
          <p className="text-sm text-muted-foreground">
            Public configuration checks for debugging signup/login failures.
          </p>
        </header>

        <section className="rounded-xl border bg-card p-5">
          <h2 className="text-base font-semibold">Environment checks</h2>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <span className="font-medium">supabaseUrl:</span>{" "}
              <code className="break-all">{supabaseUrl || "(empty)"}</code>
            </li>
            <li>
              <span className="font-medium">urlHasQuotes:</span> {String(urlHasQuotes)}
            </li>
            <li>
              <span className="font-medium">urlHasWhitespace:</span> {String(urlHasWhitespace)}
            </li>
            <li>
              <span className="font-medium">keyPresent:</span> {String(keyPresent)}
            </li>
            <li>
              <span className="font-medium">keyLength:</span> {keyLength}
            </li>
            <li className="space-y-1">
              <span className="font-medium">problems:</span>
              {problems.length > 0 ? (
                <ul className="list-disc pl-5 text-muted-foreground">
                  {problems.map((problem) => (
                    <li key={problem}>{problem}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground">None detected.</p>
              )}
            </li>
          </ul>
        </section>

        <section className="rounded-xl border bg-card p-5 space-y-4">
          <h2 className="text-base font-semibold">Supabase checks</h2>
          <div className="flex flex-wrap gap-3">
            <Button onClick={handleTestConnection} disabled={isCheckingConnection}>
              {isCheckingConnection ? "Testing..." : "Test Supabase connection"}
            </Button>
            <Button
              variant="outline"
              onClick={handleTestSignUp}
              disabled={isTestingSignup}
            >
              {isTestingSignup ? "Testing..." : "Test sign up (no email sent)"}
            </Button>
            <Button
              variant="outline"
              onClick={handleTestRawFetch}
              disabled={isTestingRawFetch}
            >
              {isTestingRawFetch ? "Testing..." : "Test raw fetch"}
            </Button>
          </div>
          {connectionStatus ? <p className="text-sm text-muted-foreground">{connectionStatus}</p> : null}
          {signupStatus ? <p className="text-sm text-muted-foreground">{signupStatus}</p> : null}
          {rawFetchStatus ? <p className="text-sm text-muted-foreground">{rawFetchStatus}</p> : null}
        </section>
      </div>
    </main>
  );
}
