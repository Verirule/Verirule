"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type ClaimsResponse = Record<string, unknown>;

export default function ProtectedPage() {
  const router = useRouter();
  const [claims, setClaims] = useState<ClaimsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadClaims = async () => {
      try {
        const response = await fetch("/api/me", {
          method: "GET",
          cache: "no-store",
        });

        const body = (await response.json().catch(() => ({}))) as {
          message?: string;
        } & ClaimsResponse;

        if (response.status === 401) {
          router.push("/auth/login");
          return;
        }

        if (!response.ok) {
          setError(body.message ?? "Failed to fetch claims from backend");
          return;
        }

        setClaims(body as ClaimsResponse);
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
        Authenticated dashboard. Claims below are returned by the server-side
        proxy endpoint
        <code className="ml-1">GET /api/me</code>.
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
