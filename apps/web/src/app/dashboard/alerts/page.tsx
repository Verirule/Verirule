"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type AlertStatus = "open" | "acknowledged" | "resolved";
type AlertAction = "acknowledged" | "resolved";
type AlertTab = "open" | "acknowledged" | "resolved";
type FindingSeverity = "low" | "medium" | "high" | "critical";

type AlertRecord = {
  id: string;
  org_id: string;
  finding_id: string;
  status: AlertStatus;
  owner_user_id: string | null;
  created_at: string;
  resolved_at: string | null;
};

type FindingRecord = {
  id: string;
  org_id: string;
  source_id: string;
  run_id: string;
  title: string;
  summary: string;
  severity: FindingSeverity;
  detected_at: string;
  fingerprint: string;
  raw_url: string | null;
  raw_hash: string | null;
};

type OrgsResponse = { orgs: OrgRecord[] };
type AlertsResponse = { alerts: AlertRecord[] };
type FindingsResponse = { findings: FindingRecord[] };

function formatTime(value: string | null): string {
  if (!value) {
    return "Not set";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown time";
  }
  return parsed.toLocaleString();
}

function severityClass(severity: FindingSeverity | undefined): string {
  if (severity === "critical") return "bg-red-100 text-red-700";
  if (severity === "high") return "bg-orange-100 text-orange-700";
  if (severity === "medium") return "bg-amber-100 text-amber-800";
  return "bg-slate-100 text-slate-700";
}

export default function DashboardAlertsPage() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [findings, setFindings] = useState<FindingRecord[]>([]);

  const [activeTab, setActiveTab] = useState<AlertTab>("open");
  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingAlerts, setIsLoadingAlerts] = useState(false);
  const [updatingAlertId, setUpdatingAlertId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const findingById = useMemo(() => {
    return new Map(findings.map((finding) => [finding.id, finding]));
  }, [findings]);

  const filteredAlerts = useMemo(() => {
    return alerts.filter((alert) => alert.status === activeTab);
  }, [activeTab, alerts]);

  const loadOrgs = async () => {
    setIsLoadingOrgs(true);
    setError(null);
    try {
      const response = await fetch("/api/orgs", { method: "GET", cache: "no-store" });
      const body = (await response.json().catch(() => ({}))) as Partial<OrgsResponse>;

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.orgs)) {
        setError("Unable to load organizations right now.");
        setOrgs([]);
        setSelectedOrgId("");
        return;
      }

      const orgRows = body.orgs;
      setOrgs(orgRows);
      setSelectedOrgId((current) => {
        if (current && orgRows.some((org) => org.id === current)) {
          return current;
        }
        return orgRows[0]?.id ?? "";
      });
    } catch {
      setError("Unable to load organizations right now.");
      setOrgs([]);
      setSelectedOrgId("");
    } finally {
      setIsLoadingOrgs(false);
    }
  };

  const loadAlertsAndFindings = async (orgId: string) => {
    if (!orgId) {
      setAlerts([]);
      setFindings([]);
      return;
    }

    setIsLoadingAlerts(true);
    setError(null);

    try {
      const [alertsResponse, findingsResponse] = await Promise.all([
        fetch(`/api/alerts?org_id=${encodeURIComponent(orgId)}`, {
          method: "GET",
          cache: "no-store",
        }),
        fetch(`/api/findings?org_id=${encodeURIComponent(orgId)}`, {
          method: "GET",
          cache: "no-store",
        }),
      ]);

      if (alertsResponse.status === 401 || findingsResponse.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      const alertsBody = (await alertsResponse.json().catch(() => ({}))) as Partial<AlertsResponse>;
      const findingsBody = (await findingsResponse.json().catch(() => ({}))) as Partial<FindingsResponse>;

      if (!alertsResponse.ok || !Array.isArray(alertsBody.alerts)) {
        setError("Unable to load alerts right now.");
        setAlerts([]);
        return;
      }

      if (!findingsResponse.ok || !Array.isArray(findingsBody.findings)) {
        setError("Unable to load findings right now.");
        setFindings([]);
        return;
      }

      setAlerts(alertsBody.alerts);
      setFindings(findingsBody.findings);
    } catch {
      setError("Unable to load alerts right now.");
      setAlerts([]);
      setFindings([]);
    } finally {
      setIsLoadingAlerts(false);
    }
  };

  useEffect(() => {
    void loadOrgs();
  }, []);

  useEffect(() => {
    if (!selectedOrgId) {
      setAlerts([]);
      setFindings([]);
      return;
    }
    void loadAlertsAndFindings(selectedOrgId);
  }, [selectedOrgId]);

  const updateAlert = async (alertId: string, status: AlertAction) => {
    setUpdatingAlertId(alertId);
    setError(null);
    try {
      const response = await fetch(`/api/alerts/${alertId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        setError("Unable to update alert right now.");
        return;
      }

      await loadAlertsAndFindings(selectedOrgId);
    } catch {
      setError("Unable to update alert right now.");
    } finally {
      setUpdatingAlertId(null);
    }
  };

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Alerts</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Triage alert states and move findings through remediation.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Organization</CardTitle>
          <CardDescription>Select the workspace to review alerts.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingOrgs ? <p className="text-sm text-muted-foreground">Loading organizations...</p> : null}
          {!isLoadingOrgs && orgs.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No organizations found. Create one from dashboard overview first.
            </p>
          ) : null}
          {!isLoadingOrgs && orgs.length > 0 ? (
            <div className="space-y-2">
              <Label htmlFor="alerts-org-selector">Workspace</Label>
              <select
                id="alerts-org-selector"
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
          <CardTitle>Alert Queue</CardTitle>
          <CardDescription>Open, acknowledged, and resolved queues by workspace.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {(["open", "acknowledged", "resolved"] as const).map((tab) => (
              <Button
                key={tab}
                type="button"
                size="sm"
                variant={activeTab === tab ? "default" : "outline"}
                onClick={() => setActiveTab(tab)}
              >
                {tab === "open" ? "Open" : tab === "acknowledged" ? "Acknowledged" : "Resolved"}
              </Button>
            ))}
          </div>

          {isLoadingAlerts ? <p className="text-sm text-muted-foreground">Loading alerts...</p> : null}
          {!isLoadingAlerts && selectedOrgId && filteredAlerts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No {activeTab} alerts for this workspace.</p>
          ) : null}

          {!isLoadingAlerts && filteredAlerts.length > 0 ? (
            <ul className="space-y-2">
              {filteredAlerts.map((alert) => {
                const finding = findingById.get(alert.finding_id);
                return (
                  <li
                    key={alert.id}
                    className="rounded-lg border border-border/70 bg-card px-3 py-3 text-sm shadow-sm"
                  >
                    <div className="space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
                          {alert.status}
                        </span>
                        <span
                          className={`rounded px-2 py-1 text-xs font-medium ${severityClass(
                            finding?.severity,
                          )}`}
                        >
                          {finding?.severity ?? "unknown"}
                        </span>
                      </div>

                      <div>
                        <p className="font-medium">{finding?.title ?? "Related finding unavailable"}</p>
                        <p className="text-xs text-muted-foreground">
                          {finding?.summary ?? "No summary available."}
                        </p>
                      </div>

                      <div className="text-xs text-muted-foreground">
                        Created {formatTime(alert.created_at)}. Resolved {formatTime(alert.resolved_at)}.
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={updatingAlertId === alert.id || alert.status !== "open"}
                          onClick={() => void updateAlert(alert.id, "acknowledged")}
                        >
                          {updatingAlertId === alert.id ? "Saving..." : "Acknowledge"}
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          disabled={updatingAlertId === alert.id || alert.status === "resolved"}
                          onClick={() => void updateAlert(alert.id, "resolved")}
                        >
                          {updatingAlertId === alert.id ? "Saving..." : "Resolve"}
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setError("Create task flow is coming in the next phase.")}
                        >
                          Create task
                        </Button>
                        <Button asChild type="button" variant="ghost" size="sm">
                          <Link href={`/dashboard/alerts/${alert.id}?org_id=${encodeURIComponent(alert.org_id)}`}>
                            Details
                          </Link>
                        </Button>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
