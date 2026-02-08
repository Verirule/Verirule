"use client";

import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiFetch } from "../../lib/api";

type ClaimsResponse = Record<string, unknown>;

export default function ProtectedPage() {
  const router = useRouter();
  const [claims, setClaims] = useState<ClaimsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadClaims = async () => {
      const supabase = createClient();
      const { data, error: sessionError } = await supabase.auth.getSession();

      if (sessionError || !data.session?.access_token) {
        router.push("/auth/login");
        return;
      }

      try {
        const response = await apiFetch("/api/v1/me", data.session.access_token);
        setClaims(response as ClaimsResponse);
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Failed to fetch claims from backend",
        );
      } finally {
        setIsLoading(false);
      }
    };

    void loadClaims();
  }, [router]);

  return (
    <div className="flex-1 w-full flex flex-col gap-8">
      <div className="bg-accent text-sm p-3 px-5 rounded-md text-foreground">
        Authenticated dashboard. Claims below are returned from the FastAPI endpoint
        <code className="ml-1">GET /api/v1/me</code>.
      </div>
      <div className="flex flex-col gap-2">
        <h2 className="font-bold text-2xl">Backend claims</h2>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading claims...</p>
        ) : null}
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <pre className="text-xs font-mono p-3 rounded border min-h-24 overflow-auto">
          {claims ? JSON.stringify(claims, null, 2) : "{}"}
        </pre>
      </div>
    </div>
  );
}
