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

const providerIcons: Record<OAuthProvider, ComponentType<SVGProps<SVGSVGElement>>> = {
  google: GoogleIcon,
  apple: AppleIcon,
  github: GitHubIcon,
  azure: MicrosoftIcon,
};

function getEnabledOAuthProviders(): OAuthProvider[] {
  const raw = process.env.NEXT_PUBLIC_SUPABASE_OAUTH_PROVIDERS?.trim();
  if (!raw) {
    return [];
  }

  const requested = raw
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter((item): item is OAuthProvider => allProviders.includes(item as OAuthProvider));

  return Array.from(new Set(requested));
}

function normalizeOAuthErrorMessage(message: string, provider: OAuthProvider): string {
  try {
    const parsed = JSON.parse(message) as { msg?: unknown; error?: unknown };
    const parsedMsg = typeof parsed.msg === "string" ? parsed.msg : null;
    const parsedError = typeof parsed.error === "string" ? parsed.error : null;
    message = parsedMsg ?? parsedError ?? message;
  } catch {
    // Keep original message
  }

  const lowered = message.toLowerCase();
  if (lowered.includes("provider is not enabled") || lowered.includes("unsupported provider")) {
    return `${providerLabels[provider]} sign-in is not enabled.`;
  }

  return message;
}

export function OAuthButtons({ mode }: OAuthButtonsProps) {
  const [loadingProvider, setLoadingProvider] = useState<OAuthProvider | null>(null);
  const [error, setError] = useState<string | null>(null);
  const providers = getEnabledOAuthProviders();

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
        setError(normalizeOAuthErrorMessage(oauthError.message, provider));
      }
    } catch (oauthError: unknown) {
      setError(oauthError instanceof Error ? oauthError.message : "OAuth sign-in failed.");
    } finally {
      setLoadingProvider(null);
    }
  };

  const actionText = mode === "signup" ? "Use" : "Use";

  if (providers.length === 0) {
    return (
      <div
        role="alert"
        className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200"
      >
        OAuth sign-in is not configured for this environment.
      </div>
    );
  }

  return (
    <div className="space-y-3" aria-live="polite">
      {providers.map((provider) => {
        const ProviderIcon = providerIcons[provider];
        return (
          <Button
            key={provider}
            type="button"
            variant="outline"
            className="relative z-20 flex h-11 w-full items-center justify-center gap-2 border border-blue-200 bg-white text-blue-900 hover:bg-blue-50 pointer-events-auto"
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
