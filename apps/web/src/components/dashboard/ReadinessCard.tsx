"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type ReadinessSnapshot = {
  id: string;
  org_id: string;
  computed_at: string;
  score: number;
  controls_total: number;
  controls_with_evidence: number;
  evidence_items_total: number;
  evidence_items_done: number;
  open_alerts_high: number;
  open_tasks: number;
  overdue_tasks: number;
  metadata: Record<string, unknown>;
};

type OrgsResponse = { orgs: OrgRecord[] };
type ReadinessComputeResponse = { snapshot_id: string; readiness: ReadinessSnapshot };

function scoreBadgeClass(score: number): string {
  if (score >= 80) return "bg-emerald-100 text-emerald-800";
  if (score >= 60) return "bg-amber-100 text-amber-800";
  return "bg-red-100 text-red-700";
}

export function ReadinessCard() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [snapshot, setSnapshot] = useState<ReadinessSnapshot | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isComputing, setIsComputing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadOrgsAndReadiness = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const orgsResponse = await fetch("/api/orgs", { method: "GET", cache: "no-store" });
      const orgsBody = (await orgsResponse.json().catch(() => ({}))) as Partial<OrgsResponse> & {
        message?: unknown;
      };
      if (orgsResponse.status === 401) {
        window.location.href = "/auth/login";
        return;
      }
      if (!orgsResponse.ok || !Array.isArray(orgsBody.orgs)) {
        setError(typeof orgsBody.message === "string" ? orgsBody.message : "Unable to load workspaces.");
        return;
      }

      const rows = orgsBody.orgs;
      setOrgs(rows);
      const orgId = rows[0]?.id ?? "";
      setSelectedOrgId(orgId);
      if (!orgId) {
        setSnapshot(null);
        return;
      }

      const readinessResponse = await fetch(`/api/orgs/${encodeURIComponent(orgId)}/readiness/latest`, {
        method: "GET",
        cache: "no-store",
      });
      if (readinessResponse.status === 404) {
        setSnapshot(null);
        return;
      }
      const readinessBody = (await readinessResponse.json().catch(() => ({}))) as
        | ReadinessSnapshot
        | { message?: unknown };
      if (!readinessResponse.ok) {
        const message =
          typeof readinessBody === "object" &&
          readinessBody &&
          "message" in readinessBody &&
          typeof readinessBody.message === "string"
            ? readinessBody.message
            : "Unable to load readiness snapshot.";
        setError(message);
        return;
      }
      setSnapshot(readinessBody as ReadinessSnapshot);
    } catch {
      setError("Unable to load readiness.");
    } finally {
      setIsLoading(false);
    }
  };

  const loadLatestForOrg = async (orgId: string) => {
    if (!orgId) {
      setSnapshot(null);
      return;
    }
    setError(null);
    try {
      const response = await fetch(`/api/orgs/${encodeURIComponent(orgId)}/readiness/latest`, {
        method: "GET",
        cache: "no-store",
      });
      if (response.status === 404) {
        setSnapshot(null);
        return;
      }
      const body = (await response.json().catch(() => ({}))) as ReadinessSnapshot & { message?: unknown };
      if (!response.ok) {
        setError(typeof body.message === "string" ? body.message : "Unable to load readiness snapshot.");
        return;
      }
      setSnapshot(body);
    } catch {
      setError("Unable to load readiness snapshot.");
    }
  };

  useEffect(() => {
    void loadOrgsAndReadiness();
  }, []);

  const recompute = async () => {
    if (!selectedOrgId) {
      return;
    }
    setIsComputing(true);
    setError(null);
    try {
      const response = await fetch(`/api/orgs/${encodeURIComponent(selectedOrgId)}/readiness/compute`, {
        method: "POST",
      });
      const body = (await response.json().catch(() => ({}))) as
        | ReadinessComputeResponse
        | { message?: unknown };
      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }
      if (!response.ok) {
        const message =
          typeof body === "object" &&
          body &&
          "message" in body &&
          typeof body.message === "string"
            ? body.message
            : "Unable to recompute readiness.";
        setError(message);
        return;
      }
      setSnapshot((body as ReadinessComputeResponse).readiness);
    } catch {
      setError("Unable to recompute readiness.");
    } finally {
      setIsComputing(false);
    }
  };

  const evidenceProgress = useMemo(() => {
    if (!snapshot || snapshot.evidence_items_total <= 0) {
      return 0;
    }
    return Math.round((snapshot.evidence_items_done / snapshot.evidence_items_total) * 100);
  }, [snapshot]);

  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle>Compliance Readiness</CardTitle>
        <CardDescription>Latest org-level readiness score from controls, evidence, tasks, and alerts.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? <p className="text-sm text-muted-foreground">Loading readiness...</p> : null}

        {!isLoading && orgs.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end">
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">Workspace</span>
              <select
                value={selectedOrgId}
                onChange={(event) => {
                  const value = event.target.value;
                  setSelectedOrgId(value);
                  void loadLatestForOrg(value);
                }}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                {orgs.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name}
                  </option>
                ))}
              </select>
            </label>
            <Button type="button" variant="outline" onClick={() => void recompute()} disabled={isComputing}>
              {isComputing ? "Computing..." : "Recompute now"}
            </Button>
            <Button asChild type="button" variant="outline">
              <Link href={`/dashboard/readiness?org_id=${encodeURIComponent(selectedOrgId)}`}>View trend</Link>
            </Button>
          </div>
        ) : null}

        {!isLoading && snapshot ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-3xl font-semibold">{snapshot.score}</p>
              <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${scoreBadgeClass(snapshot.score)}`}>
                {snapshot.score >= 80 ? "Strong" : snapshot.score >= 60 ? "Moderate" : "Needs attention"}
              </span>
              <p className="text-xs text-muted-foreground">Computed {new Date(snapshot.computed_at).toLocaleString()}</p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-md border border-border/60 p-2 text-sm">
                Controls with evidence: {snapshot.controls_with_evidence}/{snapshot.controls_total}
              </div>
              <div className="rounded-md border border-border/60 p-2 text-sm">
                Evidence completion: {snapshot.evidence_items_done}/{snapshot.evidence_items_total} ({evidenceProgress}%)
              </div>
              <div className="rounded-md border border-border/60 p-2 text-sm">
                Open high alerts: {snapshot.open_alerts_high}
              </div>
              <div className="rounded-md border border-border/60 p-2 text-sm">Open tasks: {snapshot.open_tasks}</div>
              <div className="rounded-md border border-border/60 p-2 text-sm">Overdue tasks: {snapshot.overdue_tasks}</div>
            </div>
          </div>
        ) : null}

        {!isLoading && orgs.length > 0 && !snapshot ? (
          <p className="text-sm text-muted-foreground">
            No readiness snapshot yet. Click <span className="font-medium">Recompute now</span>.
          </p>
        ) : null}

        {!isLoading && orgs.length === 0 ? (
          <p className="text-sm text-muted-foreground">Create a workspace to start readiness scoring.</p>
        ) : null}

        {error ? <p className="text-sm text-destructive">{error}</p> : null}
      </CardContent>
    </Card>
  );
}
