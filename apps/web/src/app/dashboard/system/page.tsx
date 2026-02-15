"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useEffect, useMemo, useState } from "react";

type SystemHealthResponse = {
  api: "ok";
  worker: "ok" | "stale" | "unknown";
  worker_last_seen_at: string | null;
  stale_after_seconds: number;
};

type SystemStatusRow = {
  id: string;
  updated_at: string;
  payload: Record<string, unknown>;
};

type SystemStatusResponse = {
  status: SystemStatusRow[];
};

type FailedJobType = "notifications" | "exports" | "monitoring";

type FailedJobRow = {
  id: string;
  org_id: string;
  type: string;
  status: string;
  attempts: number;
  last_error: string | null;
  updated_at: string | null;
};

type SystemJobsResponse = {
  jobs: FailedJobRow[];
};

const FAILED_JOB_TABS: { key: FailedJobType; label: string }[] = [
  { key: "notifications", label: "Notifications" },
  { key: "exports", label: "Exports" },
  { key: "monitoring", label: "Monitoring" },
];

function formatUtc(value: string | null): string {
  if (!value) return "n/a";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "n/a";
  return parsed.toISOString();
}

function formatRelative(value: string | null): string {
  if (!value) return "n/a";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "n/a";

  const diffMs = Date.now() - parsed.getTime();
  if (diffMs < 0) return "in the future";
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return `${seconds}s ago`;

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function asNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return 0;
}

function messageFromBody(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && !Array.isArray(body)) {
    const objectBody = body as Record<string, unknown>;
    if (typeof objectBody.error === "string" && objectBody.error.trim()) {
      return objectBody.error.trim();
    }
    if (typeof objectBody.message === "string" && objectBody.message.trim()) {
      return objectBody.message.trim();
    }
  }
  return fallback;
}

export default function DashboardSystemPage() {
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [statusRows, setStatusRows] = useState<SystemStatusRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [jobsByType, setJobsByType] = useState<Record<FailedJobType, FailedJobRow[]>>({
    notifications: [],
    exports: [],
    monitoring: [],
  });
  const [jobsLoading, setJobsLoading] = useState(true);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [activeJobsTab, setActiveJobsTab] = useState<FailedJobType>("notifications");
  const [copiedJobId, setCopiedJobId] = useState<string | null>(null);

  const loadSystemStatus = async () => {
    try {
      const [healthResponse, statusResponse] = await Promise.all([
        fetch("/api/system/health", { method: "GET", cache: "no-store" }),
        fetch("/api/system/status", { method: "GET", cache: "no-store" }),
      ]);

      if (healthResponse.status === 401 || statusResponse.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      const healthBody = (await healthResponse.json().catch(() => ({}))) as unknown;
      const statusBody = (await statusResponse.json().catch(() => ({}))) as unknown;
      const healthData = healthBody as Partial<SystemHealthResponse>;
      const statusData = statusBody as Partial<SystemStatusResponse>;

      if (
        !healthResponse.ok ||
        healthData.api !== "ok" ||
        (healthData.worker !== "ok" && healthData.worker !== "stale" && healthData.worker !== "unknown")
      ) {
        setError(messageFromBody(healthBody, "Unable to load system health."));
        return;
      }

      if (!statusResponse.ok || !Array.isArray(statusData.status)) {
        setError(messageFromBody(statusBody, "Unable to load system status."));
        return;
      }

      setError(null);
      setHealth({
        api: "ok",
        worker: healthData.worker,
        worker_last_seen_at:
          typeof healthData.worker_last_seen_at === "string" ? healthData.worker_last_seen_at : null,
        stale_after_seconds:
          typeof healthData.stale_after_seconds === "number" ? healthData.stale_after_seconds : 180,
      });
      setStatusRows(statusData.status as SystemStatusRow[]);
    } catch {
      setError("Unable to load system status right now.");
    } finally {
      setIsLoading(false);
    }
  };

  const loadFailedJobs = async () => {
    try {
      const next: Record<FailedJobType, FailedJobRow[]> = {
        notifications: [],
        exports: [],
        monitoring: [],
      };

      await Promise.all(
        FAILED_JOB_TABS.map(async ({ key }) => {
          const response = await fetch(`/api/system/jobs?type=${key}&status=failed&limit=50`, {
            method: "GET",
            cache: "no-store",
          });
          if (response.status === 401) {
            window.location.href = "/auth/login";
            return;
          }
          const body = (await response.json().catch(() => ({}))) as unknown;
          const parsed = body as Partial<SystemJobsResponse>;
          if (!response.ok || !Array.isArray(parsed.jobs)) {
            throw new Error(messageFromBody(body, "Unable to load failed jobs."));
          }

          next[key] = parsed.jobs
            .filter((job): job is FailedJobRow => {
              return Boolean(
                job &&
                  typeof job === "object" &&
                  typeof job.id === "string" &&
                  typeof job.org_id === "string",
              );
            })
            .map((job) => ({
              id: job.id,
              org_id: job.org_id,
              type: typeof job.type === "string" ? job.type : key,
              status: typeof job.status === "string" ? job.status : "failed",
              attempts: asNumber(job.attempts),
              last_error: typeof job.last_error === "string" ? job.last_error : null,
              updated_at: typeof job.updated_at === "string" ? job.updated_at : null,
            }));
        }),
      );

      setJobsByType(next);
      setJobsError(null);
    } catch (caughtError: unknown) {
      if (caughtError instanceof Error && caughtError.message.trim()) {
        setJobsError(caughtError.message);
      } else {
        setJobsError("Unable to load failed jobs right now.");
      }
    } finally {
      setJobsLoading(false);
    }
  };

  useEffect(() => {
    void Promise.all([loadSystemStatus(), loadFailedJobs()]);
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      void Promise.all([loadSystemStatus(), loadFailedJobs()]);
    }, 15000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!copiedJobId) return;
    const timeout = window.setTimeout(() => setCopiedJobId(null), 1800);
    return () => window.clearTimeout(timeout);
  }, [copiedJobId]);

  const workerStatusRow = useMemo(
    () => statusRows.find((row) => row.id === "worker") ?? null,
    [statusRows],
  );

  const workerPayload = workerStatusRow?.payload ?? {};
  const workerSeenAt = health?.worker_last_seen_at ?? workerStatusRow?.updated_at ?? null;
  const runsProcessed = asNumber(workerPayload.runs_processed);
  const exportsProcessed = asNumber(workerPayload.exports_processed);
  const runsQueued = asNumber(workerPayload.runs_queued);
  const dueSources = asNumber(workerPayload.due_sources);
  const errors = asNumber(workerPayload.errors);
  const tickStartedAt =
    typeof workerPayload.tick_started_at === "string" ? workerPayload.tick_started_at : null;
  const tickFinishedAt =
    typeof workerPayload.tick_finished_at === "string" ? workerPayload.tick_finished_at : null;
  const activeJobs = jobsByType[activeJobsTab];

  const copyJobId = async (jobId: string) => {
    try {
      await navigator.clipboard.writeText(jobId);
      setCopiedJobId(jobId);
    } catch {
      setCopiedJobId(null);
    }
  };

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">System</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          API and worker status, heartbeat freshness, and failed background jobs.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Health</CardTitle>
          <CardDescription>Current API and worker availability.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? <p className="text-sm text-muted-foreground">Loading system health...</p> : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          {!isLoading && !error && health ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-border/70 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">API</p>
                <p className="mt-2">
                  <span className="rounded bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-800">
                    {health.api}
                  </span>
                </p>
              </div>

              <div className="rounded-lg border border-border/70 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Worker</p>
                <p className="mt-2">
                  <span
                    className={`rounded px-2 py-1 text-xs font-medium ${
                      health.worker === "ok"
                        ? "bg-emerald-100 text-emerald-800"
                        : health.worker === "stale"
                          ? "bg-red-100 text-red-700"
                          : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {health.worker}
                  </span>
                </p>
              </div>

              <div className="rounded-lg border border-border/70 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Worker Last Seen</p>
                <p className="mt-2 text-sm font-medium">{formatRelative(workerSeenAt)}</p>
                <p className="mt-1 text-xs text-muted-foreground">{formatUtc(workerSeenAt)}</p>
              </div>

              <div className="rounded-lg border border-border/70 p-3">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Stale Threshold</p>
                <p className="mt-2 text-sm font-medium">{health.stale_after_seconds}s</p>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Last Tick</CardTitle>
          <CardDescription>Most recent worker loop statistics from heartbeat payload.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!workerStatusRow ? (
            <p className="text-sm text-muted-foreground">Worker heartbeat not available yet.</p>
          ) : (
            <>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <div className="rounded-lg border border-border/70 p-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Runs Processed</p>
                  <p className="mt-2 text-sm font-medium">{runsProcessed}</p>
                </div>
                <div className="rounded-lg border border-border/70 p-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Exports Processed</p>
                  <p className="mt-2 text-sm font-medium">{exportsProcessed}</p>
                </div>
                <div className="rounded-lg border border-border/70 p-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Runs Queued</p>
                  <p className="mt-2 text-sm font-medium">{runsQueued}</p>
                </div>
                <div className="rounded-lg border border-border/70 p-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Due Sources</p>
                  <p className="mt-2 text-sm font-medium">{dueSources}</p>
                </div>
                <div className="rounded-lg border border-border/70 p-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Errors</p>
                  <p className="mt-2 text-sm font-medium">{errors}</p>
                </div>
              </div>

              <div className="rounded-lg border border-border/70 p-3 text-sm">
                <p>
                  <span className="font-medium">Tick started:</span> {formatUtc(tickStartedAt)}
                </p>
                <p className="mt-1">
                  <span className="font-medium">Tick finished:</span> {formatUtc(tickFinishedAt)}
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Failed Jobs</CardTitle>
          <CardDescription>Recent dead-lettered or failed background jobs.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {FAILED_JOB_TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveJobsTab(tab.key)}
                className={`rounded-md border px-3 py-1.5 text-sm font-medium ${
                  activeJobsTab === tab.key
                    ? "border-blue-200 bg-blue-50 text-blue-700"
                    : "border-gray-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {jobsLoading ? <p className="text-sm text-muted-foreground">Loading failed jobs...</p> : null}
          {jobsError ? <p className="text-sm text-destructive">{jobsError}</p> : null}

          {!jobsLoading && !jobsError ? (
            activeJobs.length === 0 ? (
              <p className="text-sm text-muted-foreground">No failed jobs.</p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-border/70">
                <table className="min-w-[840px] w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
                    <tr>
                      <th className="px-3 py-2 font-medium">ID</th>
                      <th className="px-3 py-2 font-medium">Org</th>
                      <th className="px-3 py-2 font-medium">Attempts</th>
                      <th className="px-3 py-2 font-medium">Updated</th>
                      <th className="px-3 py-2 font-medium">Last Error</th>
                      <th className="px-3 py-2 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeJobs.map((job) => (
                      <tr key={`${job.type}-${job.id}`} className="border-t border-gray-200 align-top">
                        <td className="px-3 py-2 font-mono text-xs text-slate-800">{job.id}</td>
                        <td className="px-3 py-2 text-slate-700">{job.org_id}</td>
                        <td className="px-3 py-2 text-slate-700">{job.attempts}</td>
                        <td className="px-3 py-2 text-slate-700">
                          <p>{formatRelative(job.updated_at)}</p>
                          <p className="text-xs text-muted-foreground">{formatUtc(job.updated_at)}</p>
                        </td>
                        <td className="px-3 py-2 text-slate-700">
                          <p className="max-w-[360px] truncate" title={job.last_error ?? "n/a"}>
                            {job.last_error ?? "n/a"}
                          </p>
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            <Button variant="outline" size="sm" onClick={() => void copyJobId(job.id)}>
                              Copy ID
                            </Button>
                            {copiedJobId === job.id ? (
                              <span className="text-xs text-blue-700">Copied</span>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          ) : null}
        </CardContent>
      </Card>

      {health?.worker === "stale" ? (
        <Card className="border-border/70">
          <CardHeader>
            <CardTitle>If Worker Is Stale</CardTitle>
            <CardDescription>Immediate actions to restore processing.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>Check Fly worker instance status and ensure it is running.</p>
            <p>Review Fly worker logs for recent retry loops, auth failures, or upstream errors.</p>
            <p>Confirm `SUPABASE_SERVICE_ROLE_KEY` and `VERIRULE_SECRETS_KEY` are set for deployment.</p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
