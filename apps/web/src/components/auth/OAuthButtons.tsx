"use client";

import { Button } from "@/components/ui/button";
import { getSiteUrl } from "@/lib/env";
import { createClient } from "@/lib/supabase/client";
import type { ComponentType, SVGProps } from "react";
import { useState } from "react";
import { AppleIcon, GitHubIcon, GoogleIcon, MicrosoftIcon } from "./ProviderIcons";

type OAuthMode = "login" | "signup";
type OAuthProvider = "google" | "apple" | "github" | "azure";

type OAuthButtonsProps = {
  mode: OAuthMode;
};

const allProviders: OAuthProvider[] = ["google", "apple", "github", "azure"];

const providerLabels: Record<OAuthProvider, string> = {
  google: "Google",
  apple: "Apple",
  github: "GitHub",
  azure: "Microsoft",
};

const providers: OAuthProvider[] = allProviders;

const providerIcons: Record<OAuthProvider, ComponentType<SVGProps<SVGSVGElement>>> = {
  google: GoogleIcon,
  apple: AppleIcon,
  github: GitHubIcon,
  azure: MicrosoftIcon,
};

export function OAuthButtons({ mode }: OAuthButtonsProps) {
  void mode;
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
          redirectTo: `${getSiteUrl()}/auth/callback`,
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

  const actionText = "Continue with";

  if (providers.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      {providers.map((provider) => {
        const ProviderIcon = providerIcons[provider];
        return (
          <Button
            key={provider}
            type="button"
            variant="outline"
            className="relative z-20 h-11 w-full justify-center border border-slate-300/90 bg-white text-slate-900 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800/80 pointer-events-auto"
            disabled={loadingProvider !== null}
            onClick={() => handleOAuth(provider)}
          >
            <ProviderIcon className="size-4 text-current" />
            {loadingProvider === provider
              ? `Redirecting to ${providerLabels[provider]}...`
              : `${actionText} ${providerLabels[provider]}`}
          </Button>
        );
      })}
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
