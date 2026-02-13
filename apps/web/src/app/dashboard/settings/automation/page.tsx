"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type OrgsResponse = { orgs: OrgRecord[] };
type Severity = "low" | "medium" | "high";

type AlertTaskRules = {
  org_id: string;
  enabled: boolean;
  auto_create_task_on_alert: boolean;
  min_severity: Severity;
  auto_link_suggested_controls: boolean;
  auto_add_evidence_checklist: boolean;
  created_at: string;
  updated_at: string;
};

function ToggleField({
  id,
  label,
  description,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <label htmlFor={id} className="flex items-start justify-between gap-4 rounded-lg border border-border/70 p-3">
      <div className="space-y-1">
        <p className="text-sm font-medium">{label}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-1 h-4 w-4 rounded border-input"
      />
    </label>
  );
}

export default function DashboardAutomationSettingsPage() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [rules, setRules] = useState<AlertTaskRules | null>(null);
  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingRules, setIsLoadingRules] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadOrgs = useCallback(async () => {
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
        setError("Unable to load organizations.");
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
      setError("Unable to load organizations.");
      setOrgs([]);
      setSelectedOrgId("");
    } finally {
      setIsLoadingOrgs(false);
    }
  }, []);

  const loadRules = useCallback(async (orgId: string) => {
    if (!orgId) {
      setRules(null);
      return;
    }

    setIsLoadingRules(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch(`/api/orgs/${encodeURIComponent(orgId)}/automation/alert-task-rules`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<AlertTaskRules> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }
      if (!response.ok) {
        setError(typeof body.message === "string" ? body.message : "Unable to load automation rules.");
        setRules(null);
        return;
      }

      setRules({
        org_id: typeof body.org_id === "string" ? body.org_id : orgId,
        enabled: Boolean(body.enabled),
        auto_create_task_on_alert: Boolean(body.auto_create_task_on_alert),
        min_severity:
          body.min_severity === "low" || body.min_severity === "high" ? body.min_severity : "medium",
        auto_link_suggested_controls: Boolean(body.auto_link_suggested_controls),
        auto_add_evidence_checklist: Boolean(body.auto_add_evidence_checklist),
        created_at: typeof body.created_at === "string" ? body.created_at : new Date().toISOString(),
        updated_at: typeof body.updated_at === "string" ? body.updated_at : new Date().toISOString(),
      });
    } catch {
      setError("Unable to load automation rules.");
      setRules(null);
    } finally {
      setIsLoadingRules(false);
    }
  }, []);

  useEffect(() => {
    void loadOrgs();
  }, [loadOrgs]);

  useEffect(() => {
    if (!selectedOrgId) {
      setRules(null);
      return;
    }
    void loadRules(selectedOrgId);
  }, [selectedOrgId, loadRules]);

  const saveRules = async () => {
    if (!selectedOrgId || !rules) {
      return;
    }

    setIsSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch(`/api/orgs/${encodeURIComponent(selectedOrgId)}/automation/alert-task-rules`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enabled: rules.enabled,
          auto_create_task_on_alert: rules.auto_create_task_on_alert,
          min_severity: rules.min_severity,
          auto_link_suggested_controls: rules.auto_link_suggested_controls,
          auto_add_evidence_checklist: rules.auto_add_evidence_checklist,
        }),
      });
      const body = (await response.json().catch(() => ({}))) as Partial<AlertTaskRules> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }
      if (!response.ok) {
        setError(typeof body.message === "string" ? body.message : "Unable to save automation rules.");
        return;
      }

      setRules({
        org_id: typeof body.org_id === "string" ? body.org_id : selectedOrgId,
        enabled: Boolean(body.enabled),
        auto_create_task_on_alert: Boolean(body.auto_create_task_on_alert),
        min_severity:
          body.min_severity === "low" || body.min_severity === "high" ? body.min_severity : "medium",
        auto_link_suggested_controls: Boolean(body.auto_link_suggested_controls),
        auto_add_evidence_checklist: Boolean(body.auto_add_evidence_checklist),
        created_at: typeof body.created_at === "string" ? body.created_at : new Date().toISOString(),
        updated_at: typeof body.updated_at === "string" ? body.updated_at : new Date().toISOString(),
      });
      setSuccess("Automation settings saved.");
    } catch {
      setError("Unable to save automation rules.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Automation Settings</h1>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/settings">Back to settings</Link>
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          Configure deterministic alert-to-task workflows per workspace.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Workspace</CardTitle>
          <CardDescription>Select an organization to manage automation policy.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingOrgs ? <p className="text-sm text-muted-foreground">Loading organizations...</p> : null}
          {!isLoadingOrgs && orgs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No organizations found.</p>
          ) : null}
          {!isLoadingOrgs && orgs.length > 0 ? (
            <div className="space-y-2">
              <Label htmlFor="automation-org-selector">Workspace</Label>
              <select
                id="automation-org-selector"
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
          <CardTitle>Alert to Task Policy</CardTitle>
          <CardDescription>Controls for automated remediation task creation and enrichment.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingRules ? <p className="text-sm text-muted-foreground">Loading rules...</p> : null}
          {!isLoadingRules && rules ? (
            <>
              <ToggleField
                id="automation-enabled"
                label="Enable automation"
                description="Master switch for alert-to-task automation in this workspace."
                checked={rules.enabled}
                onChange={(next) => setRules((current) => (current ? { ...current, enabled: next } : current))}
              />
              <ToggleField
                id="automation-auto-create"
                label="Auto create task on alert"
                description="Create a remediation task automatically when a new open alert is detected."
                checked={rules.auto_create_task_on_alert}
                onChange={(next) =>
                  setRules((current) => (current ? { ...current, auto_create_task_on_alert: next } : current))
                }
              />
              <div className="space-y-2 rounded-lg border border-border/70 p-3">
                <Label htmlFor="automation-min-severity">Minimum severity</Label>
                <select
                  id="automation-min-severity"
                  value={rules.min_severity}
                  onChange={(event) =>
                    setRules((current) =>
                      current
                        ? {
                            ...current,
                            min_severity:
                              event.target.value === "low" || event.target.value === "high"
                                ? event.target.value
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
              <ToggleField
                id="automation-suggest-controls"
                label="Link suggested controls"
                description="When direct finding-control mappings are missing, attach top control suggestions."
                checked={rules.auto_link_suggested_controls}
                onChange={(next) =>
                  setRules((current) => (current ? { ...current, auto_link_suggested_controls: next } : current))
                }
              />
              <ToggleField
                id="automation-evidence-checklist"
                label="Add evidence checklist"
                description="Pre-populate required evidence checklist entries from linked controls."
                checked={rules.auto_add_evidence_checklist}
                onChange={(next) =>
                  setRules((current) => (current ? { ...current, auto_add_evidence_checklist: next } : current))
                }
              />
              <div className="flex items-center gap-2">
                <Button type="button" size="sm" disabled={isSaving} onClick={() => void saveRules()}>
                  {isSaving ? "Saving..." : "Save policy"}
                </Button>
              </div>
            </>
          ) : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {success ? <p className="text-sm text-emerald-700">{success}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
