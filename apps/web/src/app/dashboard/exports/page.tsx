"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePlan } from "@/src/components/billing/usePlan";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type ExportFormat = "pdf" | "csv" | "zip";
type ExportStatus = "queued" | "running" | "succeeded" | "failed";

type ExportRecord = {
  id: string;
  org_id: string;
  requested_by_user_id: string | null;
  format: ExportFormat;
  scope: Record<string, unknown>;
  status: ExportStatus;
  file_path: string | null;
  file_sha256: string | null;
  error_text: string | null;
  created_at: string;
  completed_at: string | null;
};

type OrgsResponse = { orgs: OrgRecord[] };
type ExportsResponse = { exports: ExportRecord[] };
type DownloadUrlResponse = { downloadUrl: string; expiresIn: number };

function formatTime(value: string | null): string {
  if (!value) return "n/a";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "n/a";
  }
  return parsed.toLocaleString();
}

function statusClass(status: ExportStatus): string {
  if (status === "succeeded") return "bg-emerald-100 text-emerald-800";
  if (status === "failed") return "bg-red-100 text-red-700";
  if (status === "running") return "bg-amber-100 text-amber-800";
  return "bg-slate-100 text-slate-700";
}

function toIsoOrNull(value: string): string | null {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed.toISOString();
}

export default function DashboardExportsPage() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [exportRows, setExportRows] = useState<ExportRecord[]>([]);

  const [fromLocal, setFromLocal] = useState("");
  const [toLocal, setToLocal] = useState("");
  const [format, setFormat] = useState<ExportFormat>("pdf");

  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingExports, setIsLoadingExports] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [showUpgradeCta, setShowUpgradeCta] = useState(false);
  const { features } = usePlan(selectedOrgId);

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

  const loadExports = useCallback(async (orgId: string) => {
    if (!orgId) {
      setExportRows([]);
      return;
    }
    if (!features.canUseExports) {
      setExportRows([]);
      return;
    }

    setIsLoadingExports(true);
    setError(null);
    setShowUpgradeCta(false);
    try {
      const response = await fetch(`/api/exports?org_id=${encodeURIComponent(orgId)}`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<ExportsResponse> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.exports)) {
        const messageText = typeof body.message === "string" ? body.message : null;
        setError(messageText || "Unable to load exports right now.");
        setShowUpgradeCta(response.status === 402);
        setExportRows([]);
        return;
      }

      setExportRows(body.exports);
    } catch {
      setError("Unable to load exports right now.");
      setExportRows([]);
    } finally {
      setIsLoadingExports(false);
    }
  }, [features.canUseExports]);

  const generateExport = async () => {
    if (!selectedOrgId) {
      setError("Select a workspace first.");
      return;
    }
    if (!features.canUseExports) {
      setError("Upgrade required to generate exports.");
      setShowUpgradeCta(true);
      return;
    }

    const fromIso = toIsoOrNull(fromLocal);
    const toIso = toIsoOrNull(toLocal);
    if (fromLocal && !fromIso) {
      setError("Invalid 'from' date.");
      return;
    }
    if (toLocal && !toIso) {
      setError("Invalid 'to' date.");
      return;
    }
    if (fromIso && toIso && fromIso > toIso) {
      setError("'From' date must be before 'to' date.");
      return;
    }

    setIsGenerating(true);
    setError(null);
    setMessage(null);
    setShowUpgradeCta(false);
    try {
      const response = await fetch("/api/exports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          org_id: selectedOrgId,
          format,
          from: fromIso,
          to: toIso,
          include: [
            "findings",
            "alerts",
            "tasks",
            "evidence",
            "runs",
            "snapshots",
            "audit_timeline",
          ],
        }),
      });
      const body = (await response.json().catch(() => ({}))) as {
        id?: unknown;
        status?: unknown;
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || typeof body.id !== "string") {
        const messageText = typeof body.message === "string" ? body.message : null;
        setError(messageText || "Unable to queue export right now.");
        setShowUpgradeCta(response.status === 402);
        return;
      }

      setMessage("Export queued. It will appear below when processing starts.");
      await loadExports(selectedOrgId);
    } catch {
      setError("Unable to queue export right now.");
      setShowUpgradeCta(false);
    } finally {
      setIsGenerating(false);
    }
  };

  const openDownload = async (exportId: string) => {
    if (!features.canUseExports) {
      setError("Upgrade required to download exports.");
      setShowUpgradeCta(true);
      return;
    }

    setError(null);
    setShowUpgradeCta(false);
    try {
      const response = await fetch(`/api/exports/${encodeURIComponent(exportId)}/download-url`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<DownloadUrlResponse> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || typeof body.downloadUrl !== "string") {
        const messageText = typeof body.message === "string" ? body.message : null;
        setError(messageText || "Download is not ready yet.");
        setShowUpgradeCta(response.status === 402);
        return;
      }

      window.open(body.downloadUrl, "_blank", "noopener,noreferrer");
    } catch {
      setError("Unable to open download right now.");
      setShowUpgradeCta(false);
    }
  };

  useEffect(() => {
    void loadOrgs();
  }, []);

  useEffect(() => {
    if (!selectedOrgId) {
      setExportRows([]);
      return;
    }
    if (!features.canUseExports) {
      setExportRows([]);
      return;
    }
    void loadExports(selectedOrgId);
  }, [selectedOrgId, features.canUseExports, loadExports]);

  useEffect(() => {
    if (!selectedOrgId || !features.canUseExports) return;
    const interval = window.setInterval(() => {
      void loadExports(selectedOrgId);
    }, 15000);
    return () => window.clearInterval(interval);
  }, [selectedOrgId, features.canUseExports, loadExports]);

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Exports</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Generate formal audit exports in CSV, PDF, or ZIP packet with date range filtering.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Export Setup</CardTitle>
          <CardDescription>Select workspace, range, and format.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoadingOrgs ? <p className="text-sm text-muted-foreground">Loading organizations...</p> : null}
          {!isLoadingOrgs && orgs.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No organizations found. Create one from dashboard overview first.
            </p>
          ) : null}

          {!isLoadingOrgs && orgs.length > 0 ? (
            <>
              <div className="space-y-2">
                <Label htmlFor="exports-org-selector">Workspace</Label>
                <select
                  id="exports-org-selector"
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

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="exports-from">From</Label>
                  <Input
                    id="exports-from"
                    type="datetime-local"
                    value={fromLocal}
                    onChange={(event) => setFromLocal(event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="exports-to">To</Label>
                  <Input
                    id="exports-to"
                    type="datetime-local"
                    value={toLocal}
                    onChange={(event) => setToLocal(event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="exports-format">Format</Label>
                  <select
                    id="exports-format"
                    value={format}
                    onChange={(event) => setFormat(event.target.value as ExportFormat)}
                    className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  >
                    <option value="pdf">PDF</option>
                    <option value="csv">CSV</option>
                    <option value="zip">Audit Packet (ZIP)</option>
                  </select>
                </div>
              </div>

              {features.canUseExports ? (
                <Button type="button" onClick={generateExport} disabled={isGenerating || !selectedOrgId}>
                  {isGenerating ? "Generating..." : "Generate export"}
                </Button>
              ) : (
                <div className="space-y-2 rounded-md border border-border/70 bg-muted/30 p-3">
                  <p className="text-sm text-muted-foreground">Exports are available on Pro and Business plans.</p>
                  <Button asChild size="sm">
                    <Link href="/dashboard/settings/billing">Upgrade plan</Link>
                  </Button>
                </div>
              )}
            </>
          ) : null}
          {message ? <p className="text-sm text-emerald-700">{message}</p> : null}
          {error ? (
            <div className="space-y-2">
              <p className="text-sm text-destructive">{error}</p>
              {showUpgradeCta ? (
                <Button asChild size="sm" variant="outline">
                  <Link href="/dashboard/settings/billing">Upgrade plan</Link>
                </Button>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Export History</CardTitle>
          <CardDescription>Queued and completed exports for the selected workspace.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {!features.canUseExports && selectedOrgId ? (
            <p className="text-sm text-muted-foreground">Upgrade to view and manage export history.</p>
          ) : null}
          {isLoadingExports ? <p className="text-sm text-muted-foreground">Loading exports...</p> : null}
          {!isLoadingExports && selectedOrgId && exportRows.length === 0 && features.canUseExports ? (
            <p className="text-sm text-muted-foreground">No exports for this workspace yet.</p>
          ) : null}

          {!isLoadingExports && exportRows.length > 0 && features.canUseExports ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-border/70 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-2 py-2">Created</th>
                    <th className="px-2 py-2">Format</th>
                    <th className="px-2 py-2">Status</th>
                    <th className="px-2 py-2">Completed</th>
                    <th className="px-2 py-2">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {exportRows.map((row) => (
                    <tr key={row.id} className="border-b border-border/50">
                      <td className="px-2 py-2">{formatTime(row.created_at)}</td>
                      <td className="px-2 py-2 uppercase">{row.format}</td>
                      <td className="px-2 py-2">
                        <span className={`rounded px-2 py-1 text-xs font-medium ${statusClass(row.status)}`}>
                          {row.status}
                        </span>
                      </td>
                      <td className="px-2 py-2">{formatTime(row.completed_at)}</td>
                      <td className="px-2 py-2">
                        {row.status === "succeeded" ? (
                          <Button type="button" size="sm" onClick={() => openDownload(row.id)}>
                            Download
                          </Button>
                        ) : (
                          <span className="text-xs text-muted-foreground">Not ready</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
