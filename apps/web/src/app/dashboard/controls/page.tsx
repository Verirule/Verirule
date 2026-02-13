"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useEffect, useMemo, useState } from "react";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type OrgControlStatus = "not_started" | "in_progress" | "implemented" | "needs_review";
type FindingSeverity = "low" | "medium" | "high" | "critical";
type ControlConfidence = "low" | "medium" | "high";

type LinkedFindingRecord = {
  finding_id: string;
  title: string;
  summary: string;
  severity: FindingSeverity;
  detected_at: string;
  confidence: ControlConfidence;
};

type OrgControlRecord = {
  id: string;
  org_id: string;
  control_id: string;
  status: OrgControlStatus;
  owner_user_id: string | null;
  notes: string | null;
  created_at: string;
  framework_slug: string;
  control_key: string;
  title: string;
  description: string;
  severity_default: "low" | "medium" | "high";
  tags: string[];
  evidence_count: number;
  linked_findings: LinkedFindingRecord[];
};

type ControlEvidenceRecord = {
  id: string;
  control_id: string;
  label: string;
  description: string;
  evidence_type: "document" | "screenshot" | "log" | "config" | "ticket" | "attestation";
  required: boolean;
  sort_order: number;
  created_at: string;
};

type ControlDetailResponse = {
  control: {
    id: string;
    framework_slug: string;
    control_key: string;
    title: string;
    description: string;
    severity_default: "low" | "medium" | "high";
    tags: string[];
    created_at: string;
  };
  evidence: ControlEvidenceRecord[];
  guidance: {
    id: string;
    control_id: string;
    guidance_markdown: string;
    created_at: string;
  } | null;
};

type OrgsResponse = { orgs: OrgRecord[] };
type OrgControlsResponse = { controls: OrgControlRecord[] };

function formatDateTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown";
  }
  return parsed.toLocaleString();
}

function statusLabel(status: OrgControlStatus): string {
  if (status === "not_started") return "Not started";
  if (status === "in_progress") return "In progress";
  if (status === "implemented") return "Implemented";
  return "Needs review";
}

export default function DashboardControlsPage() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [controls, setControls] = useState<OrgControlRecord[]>([]);
  const [frameworkFilter, setFrameworkFilter] = useState<"all" | string>("all");
  const [statusFilter, setStatusFilter] = useState<"all" | OrgControlStatus>("all");

  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingControls, setIsLoadingControls] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedOrgControl, setSelectedOrgControl] = useState<OrgControlRecord | null>(null);
  const [controlDetail, setControlDetail] = useState<ControlDetailResponse | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [draftStatus, setDraftStatus] = useState<OrgControlStatus>("not_started");
  const [draftOwnerUserId, setDraftOwnerUserId] = useState("");
  const [draftNotes, setDraftNotes] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const frameworkOptions = useMemo(() => {
    const values = new Set<string>();
    for (const row of controls) {
      values.add(row.framework_slug);
    }
    return Array.from(values).sort();
  }, [controls]);

  const filteredControls = useMemo(() => {
    return controls.filter((row) => {
      if (frameworkFilter !== "all" && row.framework_slug !== frameworkFilter) {
        return false;
      }
      if (statusFilter !== "all" && row.status !== statusFilter) {
        return false;
      }
      return true;
    });
  }, [controls, frameworkFilter, statusFilter]);

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
        setError("Unable to load workspaces right now.");
        setOrgs([]);
        setSelectedOrgId("");
        return;
      }

      setOrgs(body.orgs);
      setSelectedOrgId((current) => {
        if (current && body.orgs?.some((org) => org.id === current)) {
          return current;
        }
        return body.orgs?.[0]?.id ?? "";
      });
    } catch {
      setError("Unable to load workspaces right now.");
      setOrgs([]);
      setSelectedOrgId("");
    } finally {
      setIsLoadingOrgs(false);
    }
  };

  const loadOrgControls = async (orgId: string) => {
    if (!orgId) {
      setControls([]);
      return;
    }

    setIsLoadingControls(true);
    setError(null);
    try {
      const response = await fetch(`/api/orgs/${encodeURIComponent(orgId)}/controls`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<OrgControlsResponse> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.controls)) {
        setError("Unable to load controls right now.");
        setControls([]);
        return;
      }

      setControls(body.controls);
    } catch {
      setError("Unable to load controls right now.");
      setControls([]);
    } finally {
      setIsLoadingControls(false);
    }
  };

  const loadControlDetail = async (controlId: string) => {
    setIsLoadingDetail(true);
    setDetailError(null);
    setControlDetail(null);
    try {
      const response = await fetch(`/api/controls/${encodeURIComponent(controlId)}`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<ControlDetailResponse> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !body.control || !Array.isArray(body.evidence)) {
        const message = typeof body.message === "string" ? body.message : "Unable to load control details right now.";
        setDetailError(message);
        return;
      }

      setControlDetail({
        control: body.control,
        evidence: body.evidence,
        guidance: body.guidance ?? null,
      });
    } catch {
      setDetailError("Unable to load control details right now.");
    } finally {
      setIsLoadingDetail(false);
    }
  };

  useEffect(() => {
    void loadOrgs();
  }, []);

  useEffect(() => {
    if (!selectedOrgId) {
      setControls([]);
      return;
    }
    void loadOrgControls(selectedOrgId);
  }, [selectedOrgId]);

  const openControl = (row: OrgControlRecord) => {
    setSelectedOrgControl(row);
    setDraftStatus(row.status);
    setDraftOwnerUserId(row.owner_user_id ?? "");
    setDraftNotes(row.notes ?? "");
    void loadControlDetail(row.control_id);
  };

  const saveOrgControl = async () => {
    if (!selectedOrgControl) {
      return;
    }

    setIsSaving(true);
    setDetailError(null);
    try {
      const response = await fetch(`/api/org-controls/${encodeURIComponent(selectedOrgControl.id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: draftStatus,
          owner_user_id: draftOwnerUserId.trim() || null,
          notes: draftNotes.trim() || null,
        }),
      });
      const body = (await response.json().catch(() => ({}))) as { message?: unknown };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        const message = typeof body.message === "string" ? body.message : "Unable to update control status right now.";
        setDetailError(message);
        return;
      }

      setControls((current) =>
        current.map((item) =>
          item.id === selectedOrgControl.id
            ? {
                ...item,
                status: draftStatus,
                owner_user_id: draftOwnerUserId.trim() || null,
                notes: draftNotes.trim() || null,
              }
            : item,
        ),
      );
      setSelectedOrgControl((current) =>
        current
          ? {
              ...current,
              status: draftStatus,
              owner_user_id: draftOwnerUserId.trim() || null,
              notes: draftNotes.trim() || null,
            }
          : current,
      );
    } catch {
      setDetailError("Unable to update control status right now.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Controls</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage control implementation coverage, evidence expectations, and finding mappings by workspace.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Workspace</CardTitle>
          <CardDescription>Select the organization to view control coverage.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingOrgs ? <p className="text-sm text-muted-foreground">Loading workspaces...</p> : null}
          {!isLoadingOrgs && orgs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No workspace found.</p>
          ) : null}
          {!isLoadingOrgs && orgs.length > 0 ? (
            <div className="space-y-2">
              <Label htmlFor="controls-org-selector">Workspace</Label>
              <select
                id="controls-org-selector"
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
          <CardTitle>Coverage</CardTitle>
          <CardDescription>Filter controls by framework and implementation status.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="controls-framework-filter">Framework</Label>
              <select
                id="controls-framework-filter"
                value={frameworkFilter}
                onChange={(event) => setFrameworkFilter(event.target.value)}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="all">All frameworks</option>
                {frameworkOptions.map((framework) => (
                  <option key={framework} value={framework}>
                    {framework}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="controls-status-filter">Status</Label>
              <select
                id="controls-status-filter"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value as "all" | OrgControlStatus)}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="all">All statuses</option>
                <option value="not_started">Not started</option>
                <option value="in_progress">In progress</option>
                <option value="implemented">Implemented</option>
                <option value="needs_review">Needs review</option>
              </select>
            </div>
          </div>

          {isLoadingControls ? <p className="text-sm text-muted-foreground">Loading controls...</p> : null}
          {!isLoadingControls && selectedOrgId && controls.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No controls are installed for this workspace. Apply a template and install recommended controls.
            </p>
          ) : null}
          {!isLoadingControls && controls.length > 0 && filteredControls.length === 0 ? (
            <p className="text-sm text-muted-foreground">No controls match the selected filters.</p>
          ) : null}

          {!isLoadingControls && filteredControls.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-border/70 text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="px-2 py-2">Control</th>
                    <th className="px-2 py-2">Framework</th>
                    <th className="px-2 py-2">Status</th>
                    <th className="px-2 py-2">Owner</th>
                    <th className="px-2 py-2">Evidence</th>
                    <th className="px-2 py-2">Mapped Findings</th>
                    <th className="px-2 py-2">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredControls.map((row) => (
                    <tr key={row.id} className="border-b border-border/50">
                      <td className="px-2 py-2 align-top">
                        <p className="font-medium">{row.control_key}</p>
                        <p className="text-xs text-muted-foreground">{row.title}</p>
                      </td>
                      <td className="px-2 py-2 align-top text-xs text-muted-foreground">{row.framework_slug}</td>
                      <td className="px-2 py-2 align-top">{statusLabel(row.status)}</td>
                      <td className="px-2 py-2 align-top text-xs text-muted-foreground">
                        {row.owner_user_id || "Unassigned"}
                      </td>
                      <td className="px-2 py-2 align-top">{row.evidence_count}</td>
                      <td className="px-2 py-2 align-top">{row.linked_findings.length}</td>
                      <td className="px-2 py-2 align-top">
                        <Button type="button" size="sm" variant="outline" onClick={() => openControl(row)}>
                          Details
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </CardContent>
      </Card>

      {selectedOrgControl ? (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/40">
          <div className="h-full w-full max-w-2xl overflow-y-auto bg-background p-4 sm:p-6">
            <div className="mb-4 flex items-center justify-between gap-2">
              <div>
                <h2 className="text-lg font-semibold">
                  {selectedOrgControl.control_key} - {selectedOrgControl.title}
                </h2>
                <p className="text-sm text-muted-foreground">{selectedOrgControl.framework_slug}</p>
              </div>
              <Button type="button" variant="outline" size="sm" onClick={() => setSelectedOrgControl(null)}>
                Close
              </Button>
            </div>

            <div className="space-y-4 rounded-lg border border-border/70 p-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="control-status">Status</Label>
                  <select
                    id="control-status"
                    value={draftStatus}
                    onChange={(event) => setDraftStatus(event.target.value as OrgControlStatus)}
                    className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  >
                    <option value="not_started">Not started</option>
                    <option value="in_progress">In progress</option>
                    <option value="implemented">Implemented</option>
                    <option value="needs_review">Needs review</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="control-owner-user-id">Owner User ID</Label>
                  <Input
                    id="control-owner-user-id"
                    value={draftOwnerUserId}
                    onChange={(event) => setDraftOwnerUserId(event.target.value)}
                    placeholder="User UUID"
                    autoComplete="off"
                    maxLength={120}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="control-notes">Notes</Label>
                <textarea
                  id="control-notes"
                  value={draftNotes}
                  onChange={(event) => setDraftNotes(event.target.value)}
                  className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  maxLength={4000}
                />
              </div>

              <div className="flex justify-end">
                <Button type="button" disabled={isSaving} onClick={() => void saveOrgControl()}>
                  {isSaving ? "Saving..." : "Update status"}
                </Button>
              </div>

              {isLoadingDetail ? <p className="text-sm text-muted-foreground">Loading control details...</p> : null}
              {detailError ? <p className="text-sm text-destructive">{detailError}</p> : null}

              {controlDetail ? (
                <>
                  <div>
                    <p className="text-sm text-muted-foreground">Description</p>
                    <p className="text-sm">{controlDetail.control.description}</p>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground">Guidance</p>
                    <pre className="whitespace-pre-wrap rounded-md border border-border/60 bg-card p-3 text-xs">
                      {controlDetail.guidance?.guidance_markdown || "No guidance has been published for this control."}
                    </pre>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground">Evidence Checklist</p>
                    <ul className="mt-2 space-y-2">
                      {controlDetail.evidence.map((item) => (
                        <li key={item.id} className="rounded-md border border-border/60 bg-card p-3">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="font-medium">{item.label}</p>
                            <p className="text-xs text-muted-foreground">
                              {item.evidence_type} {item.required ? "(required)" : "(optional)"}
                            </p>
                          </div>
                          <p className="mt-1 text-xs text-muted-foreground">{item.description}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                </>
              ) : null}

              <div>
                <p className="text-sm text-muted-foreground">Linked Findings</p>
                <ul className="mt-2 space-y-2">
                  {selectedOrgControl.linked_findings.length === 0 ? (
                    <li className="text-sm text-muted-foreground">No findings are linked to this control.</li>
                  ) : (
                    selectedOrgControl.linked_findings.map((finding) => (
                      <li key={finding.finding_id} className="rounded-md border border-border/60 bg-card p-3">
                        <p className="font-medium">{finding.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {finding.severity} | confidence {finding.confidence}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">{finding.summary}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Detected {formatDateTime(finding.detected_at)}
                        </p>
                      </li>
                    ))
                  )}
                </ul>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

