"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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

type OrgSlaRules = {
  org_id: string;
  enabled: boolean;
  due_hours_low: number;
  due_hours_medium: number;
  due_hours_high: number;
  due_soon_threshold_hours: number;
  overdue_remind_every_hours: number;
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

function normalizeNumber(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.max(1, Math.trunc(value));
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value.trim());
    if (Number.isFinite(parsed)) {
      return Math.max(1, Math.trunc(parsed));
    }
  }
  return fallback;
}

function normalizeSlaRules(value: unknown, orgId: string): OrgSlaRules | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const row = value as Record<string, unknown>;
  return {
    org_id: typeof row.org_id === "string" ? row.org_id : orgId,
    enabled: Boolean(row.enabled),
    due_hours_low: normalizeNumber(row.due_hours_low, 168),
    due_hours_medium: normalizeNumber(row.due_hours_medium, 72),
    due_hours_high: normalizeNumber(row.due_hours_high, 24),
    due_soon_threshold_hours: normalizeNumber(row.due_soon_threshold_hours, 12),
    overdue_remind_every_hours: normalizeNumber(row.overdue_remind_every_hours, 24),
    created_at: typeof row.created_at === "string" ? row.created_at : new Date().toISOString(),
    updated_at: typeof row.updated_at === "string" ? row.updated_at : new Date().toISOString(),
  };
}

function formatError(base: string, payload: ApiErrorResponse): string {
  const detail =
    typeof payload.message === "string"
      ? payload.message
      : typeof payload.detail === "string"
        ? payload.detail
        : null;
  return detail ? `${base} ${detail}` : base;
}

export default function DashboardSlaSettingsPage() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [currentUserId, setCurrentUserId] = useState("");
  const [isOrgAdmin, setIsOrgAdmin] = useState(false);
  const [rules, setRules] = useState<OrgSlaRules | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingRules, setIsLoadingRules] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        setCurrentUserId("");
        setError(formatError("Unable to load your user profile.", result.json ?? {}));
        return;
      }
      setCurrentUserId(result.json.sub);
    } catch (caught: unknown) {
      if (caught instanceof FetchTimeoutError) {
        setError("Unable to load your user profile. Request timed out.");
      } else {
        setError("Unable to load your user profile.");
      }
      setCurrentUserId("");
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
        setOrgs([]);
        setSelectedOrgId("");
        setError(formatError("Unable to load workspaces.", result.json ?? {}));
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

  const loadRules = useCallback(async () => {
    if (!selectedOrgId || !currentUserId) {
      setIsOrgAdmin(false);
      setRules(null);
      return;
    }

    setIsLoadingRules(true);
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
        setRules(null);
        if (membersResult.status !== 403) {
          setError(formatError("Unable to load workspace membership.", membersResult.json ?? {}));
        }
        return;
      }

      const members = Array.isArray(membersResult.json?.members)
        ? (membersResult.json.members as MemberRecord[])
        : [];
      const currentMembership = members.find((member) => member.user_id === currentUserId);
      const role = normalizeRole(currentMembership?.role);
      const canManage = role === "owner" || role === "admin";
      setIsOrgAdmin(canManage);

      if (!canManage) {
        setRules(null);
        return;
      }

      const rulesResult = await fetchWithTimeout<OrgSlaRules & ApiErrorResponse>(
        `/api/orgs/${encodeURIComponent(selectedOrgId)}/sla`,
        { method: "GET", cache: "no-store", timeoutMs: 15_000 },
      );
      if (!rulesResult.ok) {
        setRules(null);
        setError(formatError("Unable to load SLA rules.", rulesResult.json ?? {}));
        return;
      }

      const nextRules = normalizeSlaRules(rulesResult.json, selectedOrgId);
      if (!nextRules) {
        setRules(null);
        setError("Unable to load SLA rules.");
        return;
      }
      setRules(nextRules);
    } catch (caught: unknown) {
      if (caught instanceof FetchTimeoutError) {
        setError("Unable to load SLA rules. Request timed out.");
      } else {
        setError("Unable to load SLA rules.");
      }
      setIsOrgAdmin(false);
      setRules(null);
    } finally {
      setIsLoadingRules(false);
    }
  }, [currentUserId, selectedOrgId]);

  useEffect(() => {
    void loadCurrentUser();
    void loadOrgs();
  }, [loadCurrentUser, loadOrgs]);

  useEffect(() => {
    void loadRules();
  }, [loadRules]);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }
    const timer = window.setTimeout(() => setToastMessage(null), 3500);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  const selectedOrgName = useMemo(
    () => orgs.find((org) => org.id === selectedOrgId)?.name ?? "",
    [orgs, selectedOrgId],
  );

  const saveRules = async () => {
    if (!selectedOrgId || !rules || !isOrgAdmin) {
      return;
    }
    if (rules.due_hours_low < rules.due_hours_medium || rules.due_hours_medium < rules.due_hours_high) {
      setError("Due hour tiers must be low >= medium >= high.");
      return;
    }

    setIsSaving(true);
    setError(null);
    try {
      const result = await fetchWithTimeout<OrgSlaRules & ApiErrorResponse>(
        `/api/orgs/${encodeURIComponent(selectedOrgId)}/sla`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            enabled: rules.enabled,
            due_hours_low: rules.due_hours_low,
            due_hours_medium: rules.due_hours_medium,
            due_hours_high: rules.due_hours_high,
            due_soon_threshold_hours: rules.due_soon_threshold_hours,
            overdue_remind_every_hours: rules.overdue_remind_every_hours,
          }),
          timeoutMs: 15_000,
        },
      );
      if (!result.ok) {
        setError(formatError("Unable to save SLA rules.", result.json ?? {}));
        return;
      }

      const nextRules = normalizeSlaRules(result.json, selectedOrgId);
      if (!nextRules) {
        setError("Unable to save SLA rules.");
        return;
      }
      setRules(nextRules);
      setToastMessage("SLA settings saved.");
    } catch (caught: unknown) {
      if (caught instanceof FetchTimeoutError) {
        setError("Unable to save SLA rules. Request timed out.");
      } else {
        setError("Unable to save SLA rules.");
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">SLA Settings</h1>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/settings">Back to settings</Link>
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          Configure remediation due dates and escalation reminder policy per workspace.
        </p>
      </section>

      {error ? (
        <Card className="border-destructive/40">
          <CardContent className="pt-6">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      ) : null}

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Workspace</CardTitle>
          <CardDescription>Select a workspace to manage SLA policy.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingOrgs ? <p className="text-sm text-muted-foreground">Loading workspaces...</p> : null}
          {!isLoadingOrgs && orgs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No workspaces found.</p>
          ) : null}
          {!isLoadingOrgs && orgs.length > 0 ? (
            <div className="space-y-2">
              <Label htmlFor="sla-org-selector">Workspace</Label>
              <select
                id="sla-org-selector"
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
          <CardTitle>Remediation SLA</CardTitle>
          <CardDescription>
            Severity-based due windows for {selectedOrgName || "selected workspace"}.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoadingRules ? <p className="text-sm text-muted-foreground">Loading SLA rules...</p> : null}
          {!isLoadingRules && !selectedOrgId ? (
            <p className="text-sm text-muted-foreground">Select a workspace first.</p>
          ) : null}
          {!isLoadingRules && selectedOrgId && !isOrgAdmin ? (
            <p className="text-sm text-muted-foreground">
              Only workspace owners and admins can configure SLA rules.
            </p>
          ) : null}
          {!isLoadingRules && isOrgAdmin && rules ? (
            <>
              <label
                htmlFor="sla-enabled"
                className="flex items-center justify-between gap-4 rounded-lg border border-border/70 p-3"
              >
                <div>
                  <p className="text-sm font-medium">Enable SLA policy</p>
                  <p className="text-xs text-muted-foreground">
                    Controls due dates, SLA state labels, and escalation checks.
                  </p>
                </div>
                <input
                  id="sla-enabled"
                  type="checkbox"
                  checked={rules.enabled}
                  onChange={(event) =>
                    setRules((current) => (current ? { ...current, enabled: event.target.checked } : current))
                  }
                  className="h-4 w-4 rounded border-input"
                />
              </label>

              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="sla-due-hours-low">Low severity due (hours)</Label>
                  <Input
                    id="sla-due-hours-low"
                    type="number"
                    min={1}
                    max={24 * 365}
                    value={rules.due_hours_low}
                    onChange={(event) =>
                      setRules((current) =>
                        current
                          ? { ...current, due_hours_low: normalizeNumber(event.target.value, current.due_hours_low) }
                          : current,
                      )
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sla-due-hours-medium">Medium severity due (hours)</Label>
                  <Input
                    id="sla-due-hours-medium"
                    type="number"
                    min={1}
                    max={24 * 365}
                    value={rules.due_hours_medium}
                    onChange={(event) =>
                      setRules((current) =>
                        current
                          ? {
                              ...current,
                              due_hours_medium: normalizeNumber(event.target.value, current.due_hours_medium),
                            }
                          : current,
                      )
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sla-due-hours-high">High severity due (hours)</Label>
                  <Input
                    id="sla-due-hours-high"
                    type="number"
                    min={1}
                    max={24 * 365}
                    value={rules.due_hours_high}
                    onChange={(event) =>
                      setRules((current) =>
                        current
                          ? { ...current, due_hours_high: normalizeNumber(event.target.value, current.due_hours_high) }
                          : current,
                      )
                    }
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="sla-due-soon-hours">Due soon threshold (hours)</Label>
                  <Input
                    id="sla-due-soon-hours"
                    type="number"
                    min={1}
                    max={24 * 30}
                    value={rules.due_soon_threshold_hours}
                    onChange={(event) =>
                      setRules((current) =>
                        current
                          ? {
                              ...current,
                              due_soon_threshold_hours: normalizeNumber(
                                event.target.value,
                                current.due_soon_threshold_hours,
                              ),
                            }
                          : current,
                      )
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sla-overdue-remind-hours">Overdue remind interval (hours)</Label>
                  <Input
                    id="sla-overdue-remind-hours"
                    type="number"
                    min={1}
                    max={24 * 30}
                    value={rules.overdue_remind_every_hours}
                    onChange={(event) =>
                      setRules((current) =>
                        current
                          ? {
                              ...current,
                              overdue_remind_every_hours: normalizeNumber(
                                event.target.value,
                                current.overdue_remind_every_hours,
                              ),
                            }
                          : current,
                      )
                    }
                  />
                </div>
              </div>

              <Button type="button" onClick={() => void saveRules()} disabled={isSaving}>
                {isSaving ? "Saving..." : "Save SLA settings"}
              </Button>
            </>
          ) : null}
        </CardContent>
      </Card>

      {toastMessage ? (
        <div className="fixed bottom-4 right-4 z-50 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 shadow">
          {toastMessage}
        </div>
      ) : null}
    </div>
  );
}
