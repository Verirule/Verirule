"use client";

import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";
import { useState } from "react";

type OAuthMode = "login" | "signup";
type OAuthProvider = "google" | "apple" | "github" | "azure";

type OAuthButtonsProps = {
  mode: OAuthMode;
};

const providerLabels: Record<OAuthProvider, string> = {
  google: "Google",
  apple: "Apple",
  github: "GitHub",
  azure: "Microsoft",
};

const providers: OAuthProvider[] = ["google", "apple", "github", "azure"];

export function OAuthButtons({ mode }: OAuthButtonsProps) {
  const [loadingProvider, setLoadingProvider] = useState<OAuthProvider | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleOAuth = async (provider: OAuthProvider) => {
    const supabase = createClient();
    setError(null);
    setLoadingProvider(provider);

    try {
      const { error: oauthError } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        },
      });

      if (oauthError) {
        setError(oauthError.message);
      }
    } catch (oauthError: unknown) {
      setError(oauthError instanceof Error ? oauthError.message : "OAuth sign-in failed.");
    } finally {
      setLoadingProvider(null);
    }
  };

  const actionText = mode === "signup" ? "Continue with" : "Sign in with";

  return (
    <div className="space-y-3">
      {providers.map((provider) => (
        <Button
          key={provider}
          type="button"
          variant="outline"
          className="w-full justify-center border-border/70"
          disabled={loadingProvider !== null}
          onClick={() => handleOAuth(provider)}
        >
          {loadingProvider === provider
            ? `Redirecting to ${providerLabels[provider]}...`
            : `${actionText} ${providerLabels[provider]}`}
        </Button>
      ))}
      {error ? (
        <div
          role="alert"
          className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200"
        >
          {error}
        </div>
      ) : null}
    </div>
  );
}
