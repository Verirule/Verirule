"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useEffect, useMemo, useState, type FormEvent } from "react";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type OrgsResponse = {
  orgs: OrgRecord[];
};

type ApiErrorResponse = {
  message?: unknown;
  code?: unknown;
  missing?: unknown;
};

function formatCreatedAt(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown date";
  }
  return parsed.toLocaleDateString();
}

function formatOrgLoadError(status: number, payload: ApiErrorResponse): string {
  const code = typeof payload.code === "string" ? payload.code : "";

  if (status === 401 || code === "unauthorized") {
    return "Unable to load workspace: Sign in again.";
  }

  if (status === 403 || code === "rls_denied") {
    return "Unable to load workspace: No access to orgs; verify membership.";
  }

  if (code === "env_missing") {
    const missing = Array.isArray(payload.missing)
      ? payload.missing.filter((item): item is string => typeof item === "string")
      : [];
    if (missing.length > 0) {
      return `Unable to load workspace: missing env ${missing.join(", ")}.`;
    }
    return "Unable to load workspace: missing required environment variables.";
  }

  if (typeof payload.message === "string" && payload.message.trim().length > 0) {
    return `Unable to load workspace: ${payload.message}`;
  }

  return "Unable to load workspace right now.";
}

export function OrgsPanel() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [name, setName] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmedName = useMemo(() => name.trim(), [name]);

  const loadOrgs = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/orgs", { method: "GET", cache: "no-store" });
      const body = (await response.json().catch(() => ({}))) as
        | (Partial<OrgsResponse> & ApiErrorResponse)
        | ApiErrorResponse;
      const orgRows =
        "orgs" in body && Array.isArray(body.orgs) ? (body.orgs as OrgRecord[]) : null;

      if (!response.ok || !orgRows) {
        setError(formatOrgLoadError(response.status, body));
        return;
      }

      setOrgs(orgRows);
    } catch {
      setError("Unable to load workspace right now.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadOrgs();
  }, []);

  const createOrg = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (trimmedName.length < 2 || trimmedName.length > 80) {
      setError("Workspace name must be between 2 and 80 characters.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch("/api/orgs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: trimmedName }),
      });
      const body = (await response.json().catch(() => ({}))) as ApiErrorResponse;

      if (!response.ok) {
        setError(
          typeof body.message === "string" && body.message.trim().length > 0
            ? body.message
            : "Unable to create workspace right now.",
        );
        return;
      }

      setName("");
      await loadOrgs();
    } catch {
      setError("Unable to create workspace right now.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Workspaces</CardTitle>
          <CardDescription>
            Your organizations are scoped by database RLS and loaded through the same-origin API.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? <p className="text-sm text-muted-foreground">Loading workspaces...</p> : null}
          {!isLoading && orgs.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No workspace found yet. Create your first workspace to continue.
            </p>
          ) : null}
          {!isLoading && orgs.length > 0 ? (
            <ul className="space-y-2">
              {orgs.map((org) => (
                <li
                  key={org.id}
                  className="rounded-lg border border-border/70 bg-card px-3 py-2 text-sm shadow-sm"
                >
                  <div className="font-medium">{org.name}</div>
                  <div className="text-xs text-muted-foreground">
                    Created {formatCreatedAt(org.created_at)}
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>{orgs.length === 0 ? "Create Workspace" : "Create Another Workspace"}</CardTitle>
          <CardDescription>Name must be 2 to 80 characters.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={createOrg} className="space-y-3">
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Acme Compliance"
              autoComplete="off"
              maxLength={80}
              disabled={isSubmitting}
            />
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create workspace"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
