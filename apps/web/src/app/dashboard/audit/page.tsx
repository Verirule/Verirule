"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { useEffect, useState } from "react";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type AuditRecord = {
  id: string;
  org_id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

type OrgsResponse = { orgs: OrgRecord[] };
type AuditResponse = { audit: AuditRecord[] };

function formatTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown time";
  }
  return parsed.toLocaleString();
}

function formatMetadata(value: Record<string, unknown>): string {
  const keys = Object.keys(value);
  if (keys.length === 0) {
    return "{}";
  }
  return JSON.stringify(value);
}

export default function DashboardAuditPage() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [auditRows, setAuditRows] = useState<AuditRecord[]>([]);
  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingAudit, setIsLoadingAudit] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const loadAudit = async (orgId: string) => {
    if (!orgId) {
      setAuditRows([]);
      return;
    }

    setIsLoadingAudit(true);
    setError(null);
    try {
      const response = await fetch(`/api/audit?org_id=${encodeURIComponent(orgId)}`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<AuditResponse>;

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.audit)) {
        setError("Unable to load audit events right now.");
        setAuditRows([]);
        return;
      }

      setAuditRows(body.audit);
    } catch {
      setError("Unable to load audit events right now.");
      setAuditRows([]);
    } finally {
      setIsLoadingAudit(false);
    }
  };

  useEffect(() => {
    void loadOrgs();
  }, []);

  useEffect(() => {
    if (!selectedOrgId) {
      setAuditRows([]);
      return;
    }
    void loadAudit(selectedOrgId);
  }, [selectedOrgId]);

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Audit Log</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Immutable event history for monitoring actions and state transitions.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Organization</CardTitle>
          <CardDescription>Select the workspace to review audit events.</CardDescription>
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
              <Label htmlFor="org-selector">Workspace</Label>
              <select
                id="org-selector"
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
          <CardTitle>Events</CardTitle>
          <CardDescription>Most recent events first.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoadingAudit ? <p className="text-sm text-muted-foreground">Loading audit events...</p> : null}
          {!isLoadingAudit && selectedOrgId && auditRows.length === 0 ? (
            <p className="text-sm text-muted-foreground">No audit events yet for this workspace.</p>
          ) : null}
          {!isLoadingAudit && auditRows.length > 0 ? (
            <ul className="space-y-2">
              {auditRows.map((event) => (
                <li
                  key={event.id}
                  className="rounded-lg border border-border/70 bg-card px-3 py-3 text-sm shadow-sm"
                >
                  <div className="space-y-1">
                    <div className="font-medium">
                      {event.action} on {event.entity_type}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Entity: {event.entity_id ?? "n/a"} | Actor: {event.actor_user_id ?? "system"}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Metadata: {formatMetadata(event.metadata)}
                    </div>
                    <div className="text-xs text-muted-foreground">At {formatTime(event.created_at)}</div>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
