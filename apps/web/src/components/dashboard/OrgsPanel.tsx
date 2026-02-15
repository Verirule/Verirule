"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { FetchTimeoutError, fetchWithTimeout } from "@/src/lib/fetch-with-timeout";
import { useEffect, useMemo, useState, type FormEvent } from "react";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type OrgsResponse = {
  orgs: OrgRecord[];
};

type OrgCreateResponse = {
  id?: unknown;
};

type ApiErrorResponse = {
  message?: unknown;
  error?: unknown;
  detail?: unknown;
  code?: unknown;
  missing?: unknown;
  request_id?: unknown;
};

type SystemHealthResponse = {
  api?: unknown;
  worker?: unknown;
};

function formatCreatedAt(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown date";
  }
  return parsed.toLocaleDateString();
}

function extractErrorMessage(payload: ApiErrorResponse): string | null {
  if (typeof payload.message === "string" && payload.message.trim().length > 0) {
    return payload.message;
  }
  if (typeof payload.error === "string" && payload.error.trim().length > 0) {
    return payload.error;
  }
  if (typeof payload.detail === "string" && payload.detail.trim().length > 0) {
    return payload.detail;
  }
  if (payload.detail && typeof payload.detail === "object") {
    const nestedMessage = (payload.detail as { message?: unknown }).message;
    if (typeof nestedMessage === "string" && nestedMessage.trim().length > 0) {
      return nestedMessage;
    }
  }
  return null;
}

function formatOrgLoadError(status: number, payload: ApiErrorResponse, requestId: string | null): string {
  const code = typeof payload.code === "string" ? payload.code : "";
  const requestIdSuffix = requestId ? ` (Request ID: ${requestId})` : "";

  if (status === 401 || code === "unauthorized") {
    return `Unable to load workspace: Sign in again.${requestIdSuffix}`;
  }

  if (status === 403 || code === "rls_denied") {
    return `Unable to load workspace: No access to orgs; verify membership.${requestIdSuffix}`;
  }

  if (code === "env_missing") {
    const missing = Array.isArray(payload.missing)
      ? payload.missing.filter((item): item is string => typeof item === "string")
      : [];
    if (missing.length > 0) {
      return `Unable to load workspace: missing env ${missing.join(", ")}.${requestIdSuffix}`;
    }
    return `Unable to load workspace: missing required environment variables.${requestIdSuffix}`;
  }

  const message = extractErrorMessage(payload);
  if (message) {
    return `Unable to load workspace: ${message}${requestIdSuffix}`;
  }

  return `Unable to load workspace right now.${requestIdSuffix}`;
}

function formatCreateFailureMessage(requestId: string | null): string {
  if (requestId) {
    return `Workspace creation failed. Please try again. (Request ID: ${requestId})`;
  }
  return "Workspace creation failed. Please try again.";
}

function formatCreateOrgError(status: number, payload: ApiErrorResponse, requestId: string | null): string {
  const code = typeof payload.code === "string" ? payload.code : "";
  const requestIdSuffix = requestId ? ` (Request ID: ${requestId})` : "";
  const message = extractErrorMessage(payload);

  if (status === 401 || code === "unauthorized") {
    return `Workspace creation failed: Sign in again.${requestIdSuffix}`;
  }

  if (status === 403 || code === "rls_denied") {
    return `Workspace creation failed: No access to orgs; verify membership.${requestIdSuffix}`;
  }

  if (status === 429) {
    return `Workspace creation failed: ${message ?? "Too many requests. Please wait and retry."}${requestIdSuffix}`;
  }

  if (message) {
    return `Workspace creation failed: ${message}${requestIdSuffix}`;
  }

  return formatCreateFailureMessage(requestId);
}

export function OrgsPanel() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [name, setName] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isCreateError, setIsCreateError] = useState(false);
  const [retryCreateName, setRetryCreateName] = useState<string | null>(null);

  const trimmedName = useMemo(() => name.trim(), [name]);

  const loadOrgs = async () => {
    setIsLoading(true);
    setError(null);
    setIsCreateError(false);
    setRetryCreateName(null);

    try {
      const result = await fetchWithTimeout<Partial<OrgsResponse> & ApiErrorResponse>("/api/orgs", {
        method: "GET",
        cache: "no-store",
        timeoutMs: 15_000,
      });
      const body = result.json ?? {};
      const orgRows = Array.isArray(body.orgs) ? (body.orgs as OrgRecord[]) : null;

      if (!result.ok || !orgRows) {
        setError(formatOrgLoadError(result.status, body, result.requestId));
        return;
      }

      setOrgs(orgRows);
    } catch (error: unknown) {
      if (error instanceof FetchTimeoutError) {
        setError("Unable to load workspace right now. Request timed out.");
      } else {
        setError("Unable to load workspace right now.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadOrgs();
  }, []);

  const createWorkspace = async (workspaceName: string) => {
    setError(null);
    setIsCreateError(false);
    setRetryCreateName(null);

    if (workspaceName.length < 2 || workspaceName.length > 64) {
      setError("Workspace name must be between 2 and 64 characters.");
      return;
    }

    setIsSubmitting(true);
    try {
      let healthResult: {
        ok: boolean;
        status: number;
        json: (SystemHealthResponse & ApiErrorResponse) | null;
        requestId: string | null;
      };
      try {
        healthResult = await fetchWithTimeout<SystemHealthResponse & ApiErrorResponse>("/api/system/health", {
          method: "GET",
          cache: "no-store",
          timeoutMs: 5_000,
        });
      } catch {
        setError("Service unavailable");
        setIsCreateError(true);
        setRetryCreateName(workspaceName);
        return;
      }
      const healthPayload = healthResult.json ?? {};
      const healthOk = healthResult.ok && healthPayload.api === "ok" && healthPayload.worker === "ok";
      if (!healthOk) {
        const requestIdSuffix = healthResult.requestId ? ` (Request ID: ${healthResult.requestId})` : "";
        setError(`Service unavailable${requestIdSuffix}`);
        setIsCreateError(true);
        setRetryCreateName(workspaceName);
        return;
      }

      const createRequest = async () =>
        fetchWithTimeout<ApiErrorResponse & OrgCreateResponse>("/api/orgs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: workspaceName }),
          timeoutMs: 15_000,
        });

      let result: Awaited<ReturnType<typeof createRequest>>;
      try {
        result = await createRequest();
      } catch (error: unknown) {
        if (error instanceof TypeError) {
          result = await createRequest();
        } else {
          throw error;
        }
      }

      if (!result.ok) {
        const payload = result.json ?? {};
        const isValidationError =
          result.status === 400 || (typeof payload.code === "string" && payload.code === "invalid_payload");
        setError(formatCreateOrgError(result.status, payload, result.requestId));
        setIsCreateError(true);
        setRetryCreateName(isValidationError ? null : workspaceName);
        return;
      }

      const orgId = typeof result.json?.id === "string" ? result.json.id : null;
      if (!orgId) {
        setError(formatCreateFailureMessage(result.requestId));
        return;
      }

      if (typeof window !== "undefined") {
        window.sessionStorage.setItem("verirule:selected_org_id", orgId);
        const nextPath = `/dashboard?org_id=${encodeURIComponent(orgId)}`;
        window.history.replaceState(window.history.state, "", nextPath);
      }

      setName("");
      setIsCreateError(false);
      setRetryCreateName(null);
      await loadOrgs();
    } catch (error: unknown) {
      if (error instanceof FetchTimeoutError) {
        setError("Workspace creation timed out. Please try again.");
      } else {
        setError("Unable to create workspace right now.");
      }
      setIsCreateError(true);
      setRetryCreateName(workspaceName);
    } finally {
      setIsSubmitting(false);
    }
  };

  const createOrg = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await createWorkspace(trimmedName);
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
          <CardDescription>Name must be 2 to 64 characters.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={createOrg} className="space-y-3">
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Acme Compliance"
              autoComplete="off"
              maxLength={64}
              disabled={isSubmitting}
            />
            {error ? (
              <div className="space-y-2">
                <p className="text-sm text-destructive">{error}</p>
                {isCreateError && retryCreateName ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => void createWorkspace(retryCreateName)}
                    disabled={isSubmitting}
                  >
                    Retry
                  </Button>
                ) : (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => void loadOrgs()}
                    disabled={isLoading}
                  >
                    Reload workspaces
                  </Button>
                )}
              </div>
            ) : null}
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create workspace"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
