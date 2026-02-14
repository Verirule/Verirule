"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { FetchTimeoutError, fetchWithTimeout } from "@/src/lib/fetch-with-timeout";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type OrgsResponse = {
  orgs?: unknown;
};

type MeResponse = {
  sub?: unknown;
};

type MemberRole = "owner" | "admin" | "member" | "viewer";

type MemberRecord = {
  user_id?: unknown;
  role?: unknown;
};

type MembersResponse = {
  members?: unknown;
};

type NotificationMode = "digest" | "immediate" | "both";
type DigestCadence = "daily" | "weekly";
type Severity = "low" | "medium" | "high";

type OrgNotificationRules = {
  org_id: string;
  enabled: boolean;
  mode: NotificationMode;
  digest_cadence: DigestCadence;
  min_severity: Severity;
  created_at: string;
  updated_at: string;
};

type UserNotificationPrefs = {
  user_id: string;
  email_enabled: boolean;
  created_at: string;
  updated_at: string;
};

type ApiErrorResponse = {
  message?: unknown;
  detail?: unknown;
  request_id?: unknown;
};

function normalizeOrgRows(payload: OrgsResponse): OrgRecord[] {
  if (!Array.isArray(payload.orgs)) {
    return [];
  }
  return payload.orgs
    .map((row) => {
      if (!row || typeof row !== "object") {
        return null;
      }
      const org = row as Record<string, unknown>;
      if (
        typeof org.id !== "string" ||
        typeof org.name !== "string" ||
        typeof org.created_at !== "string"
      ) {
        return null;
      }
      return { id: org.id, name: org.name, created_at: org.created_at };
    })
    .filter((row): row is OrgRecord => row !== null);
}

function normalizeRole(value: unknown): MemberRole | null {
  if (value === "owner" || value === "admin" || value === "member" || value === "viewer") {
    return value;
  }
  return null;
}

function normalizeOrgRules(value: unknown, orgId: string): OrgNotificationRules | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const row = value as Record<string, unknown>;
  const mode =
    row.mode === "immediate" || row.mode === "both" || row.mode === "digest" ? row.mode : "digest";
  const cadence = row.digest_cadence === "weekly" || row.digest_cadence === "daily" ? row.digest_cadence : "daily";
  const minSeverity =
    row.min_severity === "low" || row.min_severity === "high" || row.min_severity === "medium"
      ? row.min_severity
      : "medium";

  return {
    org_id: typeof row.org_id === "string" ? row.org_id : orgId,
    enabled: Boolean(row.enabled),
    mode,
    digest_cadence: cadence,
    min_severity: minSeverity,
    created_at: typeof row.created_at === "string" ? row.created_at : new Date().toISOString(),
    updated_at: typeof row.updated_at === "string" ? row.updated_at : new Date().toISOString(),
  };
}

function normalizeUserPrefs(value: unknown, fallbackUserId: string): UserNotificationPrefs | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const row = value as Record<string, unknown>;
  return {
    user_id: typeof row.user_id === "string" ? row.user_id : fallbackUserId,
    email_enabled: Boolean(row.email_enabled),
    created_at: typeof row.created_at === "string" ? row.created_at : new Date().toISOString(),
    updated_at: typeof row.updated_at === "string" ? row.updated_at : new Date().toISOString(),
  };
}

function extractRequestId(payload: ApiErrorResponse, requestId: string | null): string | null {
  if (requestId && requestId.trim()) {
    return requestId.trim();
  }
  if (typeof payload.request_id === "string" && payload.request_id.trim()) {
    return payload.request_id.trim();
  }
  return null;
}

function formatError(base: string, payload: ApiErrorResponse, requestId: string | null): string {
  const detail =
    typeof payload.message === "string"
      ? payload.message
      : typeof payload.detail === "string"
        ? payload.detail
        : null;
  const resolvedRequestId = extractRequestId(payload, requestId);
  const suffix = resolvedRequestId ? ` (Request ID: ${resolvedRequestId})` : "";
  return detail ? `${base} ${detail}${suffix}` : `${base}${suffix}`;
}

export default function DashboardNotificationsSettingsPage() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [currentUserId, setCurrentUserId] = useState("");
  const [isOrgAdmin, setIsOrgAdmin] = useState(false);

  const [orgRules, setOrgRules] = useState<OrgNotificationRules | null>(null);
  const [userPrefs, setUserPrefs] = useState<UserNotificationPrefs | null>(null);

  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingOrgRules, setIsLoadingOrgRules] = useState(false);
  const [isLoadingUserPrefs, setIsLoadingUserPrefs] = useState(true);
  const [isSavingOrgRules, setIsSavingOrgRules] = useState(false);
  const [isSavingUserPrefs, setIsSavingUserPrefs] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadCurrentUser = useCallback(async () => {
    try {
      const result = await fetchWithTimeout<MeResponse & ApiErrorResponse>("/api/me", {
        method: "GET",
        cache: "no-store",
        timeoutMs: 15_000,
      });

      if (result.status === 401) {
        window.location.href = "/auth/login";
        return;
      }
      if (!result.ok || typeof result.json?.sub !== "string") {
        setError(formatError("Unable to load your user profile.", result.json ?? {}, result.requestId));
        setCurrentUserId("");
        return;
      }
      setCurrentUserId(result.json.sub);
    } catch (caught: unknown) {
      if (caught instanceof FetchTimeoutError) {
        setError("Unable to load your user profile. Request timed out.");
        return;
      }
      setError("Unable to load your user profile.");
    }
  }, []);

  const loadOrgs = useCallback(async () => {
    setIsLoadingOrgs(true);
    try {
      const result = await fetchWithTimeout<OrgsResponse & ApiErrorResponse>("/api/orgs", {
        method: "GET",
        cache: "no-store",
        timeoutMs: 15_000,
      });

      if (result.status === 401) {
        window.location.href = "/auth/login";
        return;
      }
      if (!result.ok) {
        setError(formatError("Unable to load workspaces.", result.json ?? {}, result.requestId));
        setOrgs([]);
        setSelectedOrgId("");
        return;
      }

      const orgRows = normalizeOrgRows(result.json ?? {});
      setOrgs(orgRows);
      setSelectedOrgId((current) => {
        if (current && orgRows.some((org) => org.id === current)) {
          return current;
        }
        return orgRows[0]?.id ?? "";
      });
    } catch (caught: unknown) {
      if (caught instanceof FetchTimeoutError) {
        setError("Unable to load workspaces. Request timed out.");
      } else {
        setError("Unable to load workspaces.");
      }
      setOrgs([]);
      setSelectedOrgId("");
    } finally {
      setIsLoadingOrgs(false);
    }
  }, []);

  const loadUserPrefs = useCallback(async () => {
    setIsLoadingUserPrefs(true);
    try {
      const result = await fetchWithTimeout<UserNotificationPrefs & ApiErrorResponse>("/api/me/notifications", {
        method: "GET",
        cache: "no-store",
        timeoutMs: 15_000,
      });

      if (result.status === 401) {
        window.location.href = "/auth/login";
        return;
      }
      if (!result.ok) {
        setError(formatError("Unable to load notification preferences.", result.json ?? {}, result.requestId));
        setUserPrefs(null);
        return;
      }

      const prefs = normalizeUserPrefs(result.json, currentUserId);
      if (!prefs) {
        setError("Unable to load notification preferences.");
        setUserPrefs(null);
        return;
      }
      setUserPrefs(prefs);
    } catch (caught: unknown) {
      if (caught instanceof FetchTimeoutError) {
        setError("Unable to load notification preferences. Request timed out.");
      } else {
        setError("Unable to load notification preferences.");
      }
      setUserPrefs(null);
    } finally {
      setIsLoadingUserPrefs(false);
    }
  }, [currentUserId]);

  const loadOrgRules = useCallback(async () => {
    if (!selectedOrgId || !currentUserId) {
      setIsOrgAdmin(false);
      setOrgRules(null);
      return;
    }

    setIsLoadingOrgRules(true);
    try {
      const membersResult = await fetchWithTimeout<MembersResponse & ApiErrorResponse>(
        `/api/orgs/${encodeURIComponent(selectedOrgId)}/members`,
        { method: "GET", cache: "no-store", timeoutMs: 15_000 },
      );

      if (membersResult.status === 401) {
        window.location.href = "/auth/login";
        return;
      }
      if (!membersResult.ok) {
        setIsOrgAdmin(false);
        setOrgRules(null);
        if (membersResult.status !== 403) {
          setError(
            formatError("Unable to load workspace membership.", membersResult.json ?? {}, membersResult.requestId),
          );
        }
        return;
      }

      const members = Array.isArray(membersResult.json?.members)
        ? (membersResult.json.members as MemberRecord[])
        : [];
      const currentMembership = members.find((member) => member.user_id === currentUserId);
      const role = normalizeRole(currentMembership?.role);
      const canManageOrgRules = role === "owner" || role === "admin";
      setIsOrgAdmin(canManageOrgRules);

      if (!canManageOrgRules) {
        setOrgRules(null);
        return;
      }

      const rulesResult = await fetchWithTimeout<OrgNotificationRules & ApiErrorResponse>(
        `/api/orgs/${encodeURIComponent(selectedOrgId)}/notifications/rules`,
        { method: "GET", cache: "no-store", timeoutMs: 15_000 },
      );

      if (!rulesResult.ok) {
        setError(formatError("Unable to load workspace notification rules.", rulesResult.json ?? {}, rulesResult.requestId));
        setOrgRules(null);
        return;
      }

      const rules = normalizeOrgRules(rulesResult.json, selectedOrgId);
      if (!rules) {
        setError("Unable to load workspace notification rules.");
        setOrgRules(null);
        return;
      }
      setOrgRules(rules);
    } catch (caught: unknown) {
      if (caught instanceof FetchTimeoutError) {
        setError("Unable to load workspace notification rules. Request timed out.");
      } else {
        setError("Unable to load workspace notification rules.");
      }
      setOrgRules(null);
      setIsOrgAdmin(false);
    } finally {
      setIsLoadingOrgRules(false);
    }
  }, [currentUserId, selectedOrgId]);

  useEffect(() => {
    void loadCurrentUser();
    void loadOrgs();
  }, [loadCurrentUser, loadOrgs]);

  useEffect(() => {
    void loadUserPrefs();
  }, [loadUserPrefs]);

  useEffect(() => {
    void loadOrgRules();
  }, [loadOrgRules]);

  const saveOrgRules = async () => {
    if (!selectedOrgId || !orgRules || !isOrgAdmin) {
      return;
    }
    setError(null);
    setSuccess(null);
    setIsSavingOrgRules(true);
    try {
      const result = await fetchWithTimeout<OrgNotificationRules & ApiErrorResponse>(
        `/api/orgs/${encodeURIComponent(selectedOrgId)}/notifications/rules`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            enabled: orgRules.enabled,
            mode: orgRules.mode,
            digest_cadence: orgRules.digest_cadence,
            min_severity: orgRules.min_severity,
          }),
          timeoutMs: 15_000,
        },
      );

      if (!result.ok) {
        setError(
          formatError("Workspace notification settings failed. Please try again.", result.json ?? {}, result.requestId),
        );
        return;
      }

      const nextRules = normalizeOrgRules(result.json, selectedOrgId);
      if (!nextRules) {
        setError("Workspace notification settings failed. Please try again.");
        return;
      }
      setOrgRules(nextRules);
      setSuccess("Workspace notification settings saved.");
    } catch (caught: unknown) {
      if (caught instanceof FetchTimeoutError) {
        setError("Workspace notification settings failed. Please try again. Request timed out.");
      } else {
        setError("Workspace notification settings failed. Please try again.");
      }
    } finally {
      setIsSavingOrgRules(false);
    }
  };

  const saveUserPrefs = async () => {
    if (!userPrefs) {
      return;
    }
    setError(null);
    setSuccess(null);
    setIsSavingUserPrefs(true);
    try {
      const result = await fetchWithTimeout<UserNotificationPrefs & ApiErrorResponse>("/api/me/notifications", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email_enabled: userPrefs.email_enabled }),
        timeoutMs: 15_000,
      });

      if (!result.ok) {
        setError(formatError("Notification preferences failed to save. Please try again.", result.json ?? {}, result.requestId));
        return;
      }

      const nextPrefs = normalizeUserPrefs(result.json, currentUserId);
      if (!nextPrefs) {
        setError("Notification preferences failed to save. Please try again.");
        return;
      }
      setUserPrefs(nextPrefs);
      setSuccess("Notification preferences saved.");
    } catch (caught: unknown) {
      if (caught instanceof FetchTimeoutError) {
        setError("Notification preferences failed to save. Please try again. Request timed out.");
      } else {
        setError("Notification preferences failed to save. Please try again.");
      }
    } finally {
      setIsSavingUserPrefs(false);
    }
  };

  const selectedOrgName = useMemo(() => orgs.find((org) => org.id === selectedOrgId)?.name ?? "", [orgs, selectedOrgId]);

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Notifications</h1>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/settings">Back to settings</Link>
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          Configure workspace routing rules and your personal email opt-in preferences.
        </p>
      </section>

      {error ? (
        <Card className="border-destructive/40">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
            <p className="text-sm text-destructive">{error}</p>
            <Button variant="outline" size="sm" onClick={() => void loadOrgs()} disabled={isLoadingOrgs}>
              Reload workspaces
            </Button>
          </CardContent>
        </Card>
      ) : null}
      {success ? <p className="text-sm text-emerald-700">{success}</p> : null}

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Workspace</CardTitle>
          <CardDescription>Select an organization to manage notification routing.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingOrgs ? <p className="text-sm text-muted-foreground">Loading workspaces...</p> : null}
          {!isLoadingOrgs && orgs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No workspaces found.</p>
          ) : null}
          {!isLoadingOrgs && orgs.length > 0 ? (
            <div className="space-y-2">
              <Label htmlFor="notifications-org-selector">Workspace</Label>
              <select
                id="notifications-org-selector"
                value={selectedOrgId}
                onChange={(event) => setSelectedOrgId(event.target.value)}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                {orgs.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name}
                  </option>
                ))}
              </select>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Org Notifications</CardTitle>
          <CardDescription>
            Workspace-level routing policy for {selectedOrgName || "selected workspace"}.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoadingOrgRules ? <p className="text-sm text-muted-foreground">Loading workspace rules...</p> : null}
          {!isLoadingOrgRules && !selectedOrgId ? (
            <p className="text-sm text-muted-foreground">Select a workspace first.</p>
          ) : null}
          {!isLoadingOrgRules && selectedOrgId && !isOrgAdmin ? (
            <p className="text-sm text-muted-foreground">
              Only workspace owners and admins can manage org notification routing rules.
            </p>
          ) : null}
          {!isLoadingOrgRules && isOrgAdmin && orgRules ? (
            <>
              <label
                htmlFor="org-notifications-enabled"
                className="flex items-center justify-between gap-4 rounded-lg border border-border/70 p-3"
              >
                <div>
                  <p className="text-sm font-medium">Enable notifications</p>
                  <p className="text-xs text-muted-foreground">
                    Master switch for digest-based workspace emails.
                  </p>
                </div>
                <input
                  id="org-notifications-enabled"
                  type="checkbox"
                  checked={orgRules.enabled}
                  onChange={(event) => setOrgRules((current) => (current ? { ...current, enabled: event.target.checked } : current))}
                  className="h-4 w-4 rounded border-input"
                />
              </label>

              <div className="space-y-2">
                <Label htmlFor="org-notifications-mode">Delivery mode</Label>
                <select
                  id="org-notifications-mode"
                  value={orgRules.mode}
                  onChange={(event) =>
                    setOrgRules((current) =>
                      current
                        ? { ...current, mode: (event.target.value as NotificationMode) || "digest" }
                        : current,
                    )
                  }
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="digest">Digest</option>
                  <option value="immediate" disabled>
                    Immediate (coming next)
                  </option>
                  <option value="both" disabled>
                    Both (coming next)
                  </option>
                </select>
                <p className="text-xs text-muted-foreground">
                  Immediate delivery for high-severity alerts is planned for the next iteration.
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="org-notifications-cadence">Digest cadence</Label>
                  <select
                    id="org-notifications-cadence"
                    value={orgRules.digest_cadence}
                    onChange={(event) =>
                      setOrgRules((current) =>
                        current
                          ? {
                              ...current,
                              digest_cadence: event.target.value === "weekly" ? "weekly" : "daily",
                            }
                          : current,
                      )
                    }
                    className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="org-notifications-min-severity">Minimum severity</Label>
                  <select
                    id="org-notifications-min-severity"
                    value={orgRules.min_severity}
                    onChange={(event) =>
                      setOrgRules((current) =>
                        current
                          ? {
                              ...current,
                              min_severity:
                                event.target.value === "low" || event.target.value === "high"
                                  ? (event.target.value as Severity)
                                  : "medium",
                            }
                          : current,
                      )
                    }
                    className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>

              <Button type="button" onClick={() => void saveOrgRules()} disabled={isSavingOrgRules}>
                {isSavingOrgRules ? "Saving..." : "Save org settings"}
              </Button>
            </>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Your Email Preferences</CardTitle>
          <CardDescription>Manage your own email opt-in preference for notification delivery.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoadingUserPrefs ? <p className="text-sm text-muted-foreground">Loading your preferences...</p> : null}
          {!isLoadingUserPrefs && userPrefs ? (
            <>
              <label
                htmlFor="user-notifications-enabled"
                className="flex items-center justify-between gap-4 rounded-lg border border-border/70 p-3"
              >
                <div>
                  <p className="text-sm font-medium">Email notifications enabled</p>
                  <p className="text-xs text-muted-foreground">
                    Turn off to opt out of digest and future immediate email delivery.
                  </p>
                </div>
                <input
                  id="user-notifications-enabled"
                  type="checkbox"
                  checked={userPrefs.email_enabled}
                  onChange={(event) =>
                    setUserPrefs((current) => (current ? { ...current, email_enabled: event.target.checked } : current))
                  }
                  className="h-4 w-4 rounded border-input"
                />
              </label>

              <Button type="button" onClick={() => void saveUserPrefs()} disabled={isSavingUserPrefs}>
                {isSavingUserPrefs ? "Saving..." : "Save my preferences"}
              </Button>
            </>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

