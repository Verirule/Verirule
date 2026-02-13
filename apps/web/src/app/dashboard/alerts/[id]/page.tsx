"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

type AlertStatus = "open" | "acknowledged" | "resolved";
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

type TaskRecord = {
  id: string;
  org_id: string;
  title: string;
  status: "open" | "in_progress" | "blocked" | "done";
  assignee_user_id: string | null;
  alert_id: string | null;
  finding_id: string | null;
  due_at: string | null;
  created_at: string;
  updated_at: string;
};

type AlertsResponse = { alerts: AlertRecord[] };
type FindingsResponse = { findings: FindingRecord[] };
type TasksResponse = { tasks: TaskRecord[] };
type EvidenceFilesResponse = {
  evidence_files: Array<{
    id: string;
    task_id: string;
    created_at: string;
  }>;
};

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

export default function AlertDetailsPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const alertId = params.id;
  const orgId = searchParams.get("org_id")?.trim() ?? "";

  const [alert, setAlert] = useState<AlertRecord | null>(null);
  const [finding, setFinding] = useState<FindingRecord | null>(null);
  const [linkedTasks, setLinkedTasks] = useState<TaskRecord[]>([]);
  const [evidenceCountByTask, setEvidenceCountByTask] = useState<Map<string, number>>(new Map());

  const [taskTitle, setTaskTitle] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isCreatingTask, setIsCreatingTask] = useState(false);
  const [isResolving, setIsResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalEvidenceCount = useMemo(() => {
    let total = 0;
    evidenceCountByTask.forEach((count) => {
      total += count;
    });
    return total;
  }, [evidenceCountByTask]);

  const loadAlertData = useCallback(async () => {
    if (!orgId || !alertId) {
      setError("Missing org_id or alert id.");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const [alertsResponse, findingsResponse, tasksResponse] = await Promise.all([
        fetch(`/api/alerts?org_id=${encodeURIComponent(orgId)}`, { method: "GET", cache: "no-store" }),
        fetch(`/api/findings?org_id=${encodeURIComponent(orgId)}`, { method: "GET", cache: "no-store" }),
        fetch(`/api/tasks?org_id=${encodeURIComponent(orgId)}`, { method: "GET", cache: "no-store" }),
      ]);

      if (alertsResponse.status === 401 || findingsResponse.status === 401 || tasksResponse.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      const alertsBody = (await alertsResponse.json().catch(() => ({}))) as Partial<AlertsResponse>;
      const findingsBody = (await findingsResponse.json().catch(() => ({}))) as Partial<FindingsResponse>;
      const tasksBody = (await tasksResponse.json().catch(() => ({}))) as Partial<TasksResponse>;

      if (!alertsResponse.ok || !Array.isArray(alertsBody.alerts)) {
        setError("Unable to load alert details.");
        return;
      }
      if (!findingsResponse.ok || !Array.isArray(findingsBody.findings)) {
        setError("Unable to load finding details.");
        return;
      }
      if (!tasksResponse.ok || !Array.isArray(tasksBody.tasks)) {
        setError("Unable to load tasks.");
        return;
      }

      const selectedAlert = alertsBody.alerts.find((entry) => entry.id === alertId) ?? null;
      if (!selectedAlert) {
        setError("Alert not found for this workspace.");
        return;
      }
      const selectedFinding =
        findingsBody.findings.find((entry) => entry.id === selectedAlert.finding_id) ?? null;
      const alertTasks = tasksBody.tasks.filter((task) => task.alert_id === selectedAlert.id);

      const evidencePairs = await Promise.all(
        alertTasks.map(async (task) => {
          const response = await fetch(
            `/api/tasks/${encodeURIComponent(task.id)}/evidence-files?org_id=${encodeURIComponent(orgId)}`,
            {
              method: "GET",
              cache: "no-store",
            },
          );
          if (!response.ok) {
            return [task.id, 0] as const;
          }
          const body = (await response.json().catch(() => ({}))) as Partial<EvidenceFilesResponse>;
          return [task.id, Array.isArray(body.evidence_files) ? body.evidence_files.length : 0] as const;
        }),
      );

      setAlert(selectedAlert);
      setFinding(selectedFinding);
      setLinkedTasks(alertTasks);
      setEvidenceCountByTask(new Map(evidencePairs));
      setTaskTitle((current) => current || `Investigate: ${selectedFinding?.title ?? "Alert follow-up"}`);
    } catch {
      setError("Unable to load alert details.");
    } finally {
      setIsLoading(false);
    }
  }, [alertId, orgId]);

  useEffect(() => {
    void loadAlertData();
  }, [loadAlertData]);

  const createTaskFromAlert = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!alert || !orgId) {
      return;
    }
    const trimmedTitle = taskTitle.trim();
    if (!trimmedTitle) {
      setError("Task title is required.");
      return;
    }

    setIsCreatingTask(true);
    setError(null);
    try {
      const response = await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          org_id: orgId,
          title: trimmedTitle,
          alert_id: alert.id,
          finding_id: alert.finding_id,
          due_at: dueAt ? new Date(dueAt).toISOString() : null,
        }),
      });

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { message?: unknown };
        setError(typeof body.message === "string" ? body.message : "Unable to create task.");
        return;
      }

      setDueAt("");
      await loadAlertData();
    } catch {
      setError("Unable to create task.");
    } finally {
      setIsCreatingTask(false);
    }
  };

  const resolveAlert = async () => {
    if (!alert) {
      return;
    }

    setIsResolving(true);
    setError(null);
    try {
      const response = await fetch(`/api/alerts/${encodeURIComponent(alert.id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "resolved" }),
      });

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { message?: unknown };
        setError(typeof body.message === "string" ? body.message : "Unable to resolve alert.");
        return;
      }

      await loadAlertData();
    } catch {
      setError("Unable to resolve alert.");
    } finally {
      setIsResolving(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Alert Details</h1>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/alerts">Back to alerts</Link>
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          Create follow-up tasks, collect evidence, and resolve alerts when readiness checks pass.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Alert</CardTitle>
          <CardDescription>Evidence requirement is enforced server-side and configurable.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {isLoading ? <p className="text-muted-foreground">Loading alert...</p> : null}
          {!isLoading && alert ? (
            <>
              <p>
                <span className="font-medium">Status:</span> {alert.status}
              </p>
              <p>
                <span className="font-medium">Created:</span> {formatTime(alert.created_at)}
              </p>
              <p>
                <span className="font-medium">Resolved:</span> {formatTime(alert.resolved_at)}
              </p>
              <p>
                <span className="font-medium">Finding:</span> {finding?.title ?? "Unknown finding"}
              </p>
              <p className="text-muted-foreground">
                Total evidence on linked tasks: <span className="font-medium text-foreground">{totalEvidenceCount}</span>
              </p>
              <Button type="button" disabled={isResolving || alert.status === "resolved"} onClick={resolveAlert}>
                {isResolving ? "Resolving..." : "Resolve Alert"}
              </Button>
            </>
          ) : null}
          {error ? <p className="text-destructive">{error}</p> : null}
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Create Task From Alert</CardTitle>
          <CardDescription>Link a remediation task directly to this alert/finding.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={createTaskFromAlert} className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="task-title">Task title</Label>
              <Input
                id="task-title"
                value={taskTitle}
                onChange={(event) => setTaskTitle(event.target.value)}
                maxLength={120}
                placeholder="Investigate suspicious change"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="task-due">Due at (optional)</Label>
              <Input
                id="task-due"
                type="datetime-local"
                value={dueAt}
                onChange={(event) => setDueAt(event.target.value)}
              />
            </div>
            <Button type="submit" disabled={isCreatingTask || !alert}>
              {isCreatingTask ? "Creating..." : "Create Task"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Linked Tasks</CardTitle>
          <CardDescription>Tasks associated with this alert.</CardDescription>
        </CardHeader>
        <CardContent>
          {linkedTasks.length === 0 ? (
            <p className="text-sm text-muted-foreground">No linked tasks yet.</p>
          ) : (
            <ul className="space-y-2">
              {linkedTasks.map((task) => (
                <li key={task.id} className="rounded-lg border border-border/70 p-3 text-sm">
                  <p className="font-medium">{task.title}</p>
                  <p className="text-xs text-muted-foreground">
                    Status: {task.status} | Evidence items: {evidenceCountByTask.get(task.id) ?? 0}
                  </p>
                  <p className="text-xs text-muted-foreground">Due: {formatTime(task.due_at)}</p>
                  <Button asChild type="button" variant="ghost" size="sm" className="mt-1">
                    <Link
                      href={`/dashboard/tasks?org_id=${encodeURIComponent(task.org_id)}&task_id=${encodeURIComponent(task.id)}`}
                    >
                      Open Task
                    </Link>
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
