"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

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
type ReadinessListResponse = { snapshots: ReadinessSnapshot[] };
type ReadinessComputeResponse = { snapshot_id: string; readiness: ReadinessSnapshot };

function formatTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown time";
  }
  return parsed.toLocaleString();
}

function scoreBadgeClass(score: number): string {
  if (score >= 80) return "bg-emerald-100 text-emerald-800";
  if (score >= 60) return "bg-amber-100 text-amber-800";
  return "bg-red-100 text-red-700";
}

function scoreLabel(score: number): string {
  if (score >= 80) return "Strong";
  if (score >= 60) return "Moderate";
  return "Needs attention";
}

function computeSparklinePath(scores: number[], width: number, height: number): string {
  if (scores.length === 0) {
    return "";
  }

  const padding = 8;
  const min = Math.min(...scores, 0);
  const max = Math.max(...scores, 100);
  const xStep = scores.length > 1 ? (width - padding * 2) / (scores.length - 1) : 0;
  const yRange = max - min || 1;

  return scores
    .map((score, index) => {
      const x = padding + xStep * index;
      const y = height - padding - ((score - min) / yRange) * (height - padding * 2);
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

export default function DashboardReadinessPage() {
  const searchParams = useSearchParams();
  const requestedOrgId = searchParams.get("org_id")?.trim() ?? "";

  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [snapshots, setSnapshots] = useState<ReadinessSnapshot[]>([]);
  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingSnapshots, setIsLoadingSnapshots] = useState(false);
  const [isComputing, setIsComputing] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        setError("Unable to load organizations right now.");
        setOrgs([]);
        setSelectedOrgId("");
        return;
      }

      const rows = body.orgs;
      setOrgs(rows);
      setSelectedOrgId((current) => {
        if (requestedOrgId && rows.some((org) => org.id === requestedOrgId)) {
          return requestedOrgId;
        }
        if (current && rows.some((org) => org.id === current)) {
          return current;
        }
        return rows[0]?.id ?? "";
      });
    } catch {
      setError("Unable to load organizations right now.");
      setOrgs([]);
      setSelectedOrgId("");
    } finally {
      setIsLoadingOrgs(false);
    }
  }, [requestedOrgId]);

  const loadSnapshots = useCallback(async (orgId: string) => {
    if (!orgId) {
      setSnapshots([]);
      return;
    }

    setIsLoadingSnapshots(true);
    setError(null);
    try {
      const response = await fetch(`/api/orgs/${encodeURIComponent(orgId)}/readiness?limit=30`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<ReadinessListResponse> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.snapshots)) {
        setError(typeof body.message === "string" ? body.message : "Unable to load readiness trend.");
        setSnapshots([]);
        return;
      }

      const ordered = [...body.snapshots].sort((a, b) => {
        return new Date(b.computed_at).getTime() - new Date(a.computed_at).getTime();
      });
      setSnapshots(ordered);
    } catch {
      setError("Unable to load readiness trend.");
      setSnapshots([]);
    } finally {
      setIsLoadingSnapshots(false);
    }
  }, []);

  useEffect(() => {
    void loadOrgs();
  }, [loadOrgs]);

  useEffect(() => {
    if (!selectedOrgId) {
      setSnapshots([]);
      return;
    }
    void loadSnapshots(selectedOrgId);
  }, [selectedOrgId, loadSnapshots]);

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

      if (!response.ok || !("readiness" in body)) {
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

      const next = body.readiness;
      setSnapshots((current) => {
        const merged = [next, ...current.filter((item) => item.id !== next.id)];
        return merged.slice(0, 30);
      });
    } catch {
      setError("Unable to recompute readiness.");
    } finally {
      setIsComputing(false);
    }
  };

  const latestSnapshot = snapshots[0] ?? null;
  const evidencePercent = useMemo(() => {
    if (!latestSnapshot || latestSnapshot.evidence_items_total <= 0) {
      return 0;
    }
    return Math.round((latestSnapshot.evidence_items_done / latestSnapshot.evidence_items_total) * 100);
  }, [latestSnapshot]);

  const sparklineScores = useMemo(() => {
    return [...snapshots].reverse().map((snapshot) => snapshot.score);
  }, [snapshots]);
  const sparklineWidth = 520;
  const sparklineHeight = 110;
  const sparklinePath = useMemo(
    () => computeSparklinePath(sparklineScores, sparklineWidth, sparklineHeight),
    [sparklineScores],
  );

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Readiness</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Org-level compliance readiness from controls, evidence completion, alert load, and task backlog.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Workspace</CardTitle>
          <CardDescription>Select a workspace and compute or review recent readiness snapshots.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingOrgs ? <p className="text-sm text-muted-foreground">Loading organizations...</p> : null}
          {!isLoadingOrgs && orgs.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No organizations found. Create a workspace from dashboard overview first.
            </p>
          ) : null}
          {!isLoadingOrgs && orgs.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
              <div className="space-y-2">
                <Label htmlFor="readiness-org-selector">Workspace</Label>
                <select
                  id="readiness-org-selector"
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
              <Button type="button" variant="outline" onClick={() => void recompute()} disabled={isComputing}>
                {isComputing ? "Computing..." : "Recompute now"}
              </Button>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Trend (Last 30)</CardTitle>
          <CardDescription>New snapshots are generated by the worker every 15 minutes and on demand.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoadingSnapshots ? <p className="text-sm text-muted-foreground">Loading readiness trend...</p> : null}
          {!isLoadingSnapshots && latestSnapshot ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <p className="text-3xl font-semibold">{latestSnapshot.score}</p>
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-medium ${scoreBadgeClass(latestSnapshot.score)}`}
                >
                  {scoreLabel(latestSnapshot.score)}
                </span>
                <p className="text-xs text-muted-foreground">
                  Latest snapshot: {formatTime(latestSnapshot.computed_at)}
                </p>
              </div>
              <div className="overflow-x-auto rounded-md border border-border/60 p-3">
                {sparklineScores.length > 0 ? (
                  <svg
                    viewBox={`0 0 ${sparklineWidth} ${sparklineHeight}`}
                    className="h-[110px] min-w-[520px] w-full"
                    role="img"
                    aria-label="Readiness score trend"
                  >
                    <line
                      x1="8"
                      y1={sparklineHeight - 8}
                      x2={sparklineWidth - 8}
                      y2={sparklineHeight - 8}
                      stroke="currentColor"
                      strokeOpacity="0.25"
                      strokeWidth="1"
                    />
                    <path d={sparklinePath} fill="none" stroke="currentColor" strokeWidth="2.5" />
                  </svg>
                ) : (
                  <p className="text-sm text-muted-foreground">No trend points available.</p>
                )}
              </div>
              <div className="overflow-x-auto rounded-md border border-border/60">
                <table className="min-w-[680px] text-sm">
                  <thead>
                    <tr className="border-b border-border/60 text-left">
                      <th className="px-3 py-2 font-medium">Computed At</th>
                      <th className="px-3 py-2 font-medium">Score</th>
                      <th className="px-3 py-2 font-medium">Evidence</th>
                      <th className="px-3 py-2 font-medium">High Alerts</th>
                      <th className="px-3 py-2 font-medium">Open Tasks</th>
                      <th className="px-3 py-2 font-medium">Overdue Tasks</th>
                    </tr>
                  </thead>
                  <tbody>
                    {snapshots.map((snapshot) => (
                      <tr key={snapshot.id} className="border-b border-border/40 last:border-b-0">
                        <td className="px-3 py-2">{formatTime(snapshot.computed_at)}</td>
                        <td className="px-3 py-2">{snapshot.score}</td>
                        <td className="px-3 py-2">
                          {snapshot.evidence_items_done}/{snapshot.evidence_items_total}
                        </td>
                        <td className="px-3 py-2">{snapshot.open_alerts_high}</td>
                        <td className="px-3 py-2">{snapshot.open_tasks}</td>
                        <td className="px-3 py-2">{snapshot.overdue_tasks}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
          {!isLoadingSnapshots && !latestSnapshot ? (
            <p className="text-sm text-muted-foreground">
              No readiness snapshots yet. Select a workspace and click Recompute now.
            </p>
          ) : null}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-border/70">
          <CardHeader>
            <CardTitle>Evidence</CardTitle>
            <CardDescription>Checklist and control proof completion.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>
              Controls with evidence:{" "}
              <span className="font-medium">
                {latestSnapshot?.controls_with_evidence ?? 0}/{latestSnapshot?.controls_total ?? 0}
              </span>
            </p>
            <p>
              Evidence items complete:{" "}
              <span className="font-medium">
                {latestSnapshot?.evidence_items_done ?? 0}/{latestSnapshot?.evidence_items_total ?? 0}
              </span>
            </p>
            <p>Completion: {evidencePercent}%</p>
          </CardContent>
        </Card>

        <Card className="border-border/70">
          <CardHeader>
            <CardTitle>Alerts</CardTitle>
            <CardDescription>Outstanding high severity alert load.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>
              Open high severity alerts: <span className="font-medium">{latestSnapshot?.open_alerts_high ?? 0}</span>
            </p>
            <p className="text-muted-foreground">Linked findings are folded into score metadata and weights.</p>
          </CardContent>
        </Card>

        <Card className="border-border/70">
          <CardHeader>
            <CardTitle>Tasks</CardTitle>
            <CardDescription>Backlog pressure and deadline risk.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>
              Open tasks: <span className="font-medium">{latestSnapshot?.open_tasks ?? 0}</span>
            </p>
            <p>
              Overdue tasks: <span className="font-medium">{latestSnapshot?.overdue_tasks ?? 0}</span>
            </p>
          </CardContent>
        </Card>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}
