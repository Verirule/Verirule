"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

type TaskStatus = "open" | "in_progress" | "resolved" | "blocked";
type EvidenceType = "link" | "file" | "log";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type TaskRecord = {
  id: string;
  org_id: string;
  title: string;
  status: TaskStatus;
  assignee_user_id: string | null;
  alert_id: string | null;
  finding_id: string | null;
  due_at: string | null;
  created_by_user_id: string;
  created_at: string;
};

type TaskCommentRecord = {
  id: string;
  task_id: string;
  author_user_id: string;
  body: string;
  created_at: string;
};

type TaskEvidenceRecord = {
  id: string;
  task_id: string;
  type: EvidenceType;
  ref: string;
  created_by_user_id: string;
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
type TasksResponse = { tasks: TaskRecord[] };
type CommentsResponse = { comments: TaskCommentRecord[] };
type EvidenceResponse = { evidence: TaskEvidenceRecord[] };
type AuditResponse = { audit: AuditRecord[] };
type MeResponse = { sub?: string };

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

export default function DashboardTasksPage() {
  const searchParams = useSearchParams();
  const requestedOrgId = searchParams.get("org_id")?.trim() ?? "";
  const requestedTaskId = searchParams.get("task_id")?.trim() ?? "";

  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [selectedTask, setSelectedTask] = useState<TaskRecord | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const [comments, setComments] = useState<TaskCommentRecord[]>([]);
  const [evidence, setEvidence] = useState<TaskEvidenceRecord[]>([]);
  const [timeline, setTimeline] = useState<AuditRecord[]>([]);

  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [isCreatingTask, setIsCreatingTask] = useState(false);
  const [isSavingTask, setIsSavingTask] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailsError, setDetailsError] = useState<string | null>(null);

  const [meUserId, setMeUserId] = useState<string>("");

  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newTaskDueAt, setNewTaskDueAt] = useState("");
  const [newTaskAlertId, setNewTaskAlertId] = useState("");
  const [newTaskFindingId, setNewTaskFindingId] = useState("");

  const [commentBody, setCommentBody] = useState("");
  const [evidenceType, setEvidenceType] = useState<EvidenceType>("link");
  const [evidenceRef, setEvidenceRef] = useState("");

  const selectedTaskEvidenceCount = useMemo(() => evidence.length, [evidence]);

  const loadMe = useCallback(async () => {
    try {
      const response = await fetch("/api/me", { method: "GET", cache: "no-store" });
      if (!response.ok) {
        return;
      }
      const body = (await response.json().catch(() => ({}))) as MeResponse;
      setMeUserId(typeof body.sub === "string" ? body.sub : "");
    } catch {
      setMeUserId("");
    }
  }, []);

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

      const orgRows = body.orgs;
      setOrgs(orgRows);
      setSelectedOrgId((current) => {
        if (requestedOrgId && orgRows.some((org) => org.id === requestedOrgId)) {
          return requestedOrgId;
        }
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
  }, [requestedOrgId]);

  const loadTasks = async (orgId: string) => {
    if (!orgId) {
      setTasks([]);
      return;
    }

    setIsLoadingTasks(true);
    setError(null);
    try {
      const response = await fetch(`/api/tasks?org_id=${encodeURIComponent(orgId)}`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<TasksResponse>;

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.tasks)) {
        setError("Unable to load tasks right now.");
        setTasks([]);
        return;
      }

      const taskRows = body.tasks;
      setTasks(taskRows);
    } catch {
      setError("Unable to load tasks right now.");
      setTasks([]);
    } finally {
      setIsLoadingTasks(false);
    }
  };

  const loadTaskDetails = async (task: TaskRecord) => {
    setSelectedTask(task);
    setIsDrawerOpen(true);
    setIsLoadingDetails(true);
    setDetailsError(null);
    try {
      const [commentsResponse, evidenceResponse, auditResponse] = await Promise.all([
        fetch(`/api/tasks/${encodeURIComponent(task.id)}/comments`, {
          method: "GET",
          cache: "no-store",
        }),
        fetch(`/api/tasks/${encodeURIComponent(task.id)}/evidence`, {
          method: "GET",
          cache: "no-store",
        }),
        fetch(`/api/audit?org_id=${encodeURIComponent(task.org_id)}`, {
          method: "GET",
          cache: "no-store",
        }),
      ]);

      const commentsBody = (await commentsResponse.json().catch(() => ({}))) as Partial<CommentsResponse>;
      const evidenceBody = (await evidenceResponse.json().catch(() => ({}))) as Partial<EvidenceResponse>;
      const auditBody = (await auditResponse.json().catch(() => ({}))) as Partial<AuditResponse>;

      if (!commentsResponse.ok || !Array.isArray(commentsBody.comments)) {
        setDetailsError("Unable to load task comments.");
        return;
      }
      if (!evidenceResponse.ok || !Array.isArray(evidenceBody.evidence)) {
        setDetailsError("Unable to load task evidence.");
        return;
      }
      if (!auditResponse.ok || !Array.isArray(auditBody.audit)) {
        setDetailsError("Unable to load task timeline.");
        return;
      }

      const taskTimeline = auditBody.audit.filter(
        (entry) => entry.entity_type === "task" && entry.entity_id === task.id,
      );
      setComments(commentsBody.comments);
      setEvidence(evidenceBody.evidence);
      setTimeline(taskTimeline);
    } catch {
      setDetailsError("Unable to load task details.");
    } finally {
      setIsLoadingDetails(false);
    }
  };

  useEffect(() => {
    void loadMe();
    void loadOrgs();
  }, [loadMe, loadOrgs]);

  useEffect(() => {
    if (!selectedOrgId) {
      setTasks([]);
      return;
    }
    void loadTasks(selectedOrgId);
  }, [selectedOrgId]);

  useEffect(() => {
    if (!requestedTaskId || tasks.length === 0) {
      return;
    }
    const task = tasks.find((entry) => entry.id === requestedTaskId);
    if (task) {
      void loadTaskDetails(task);
    }
  }, [requestedTaskId, tasks]);

  const createTask = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedOrgId) {
      setError("Select an organization first.");
      return;
    }
    if (!newTaskTitle.trim()) {
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
          org_id: selectedOrgId,
          title: newTaskTitle.trim(),
          due_at: newTaskDueAt ? new Date(newTaskDueAt).toISOString() : null,
          alert_id: newTaskAlertId.trim() || null,
          finding_id: newTaskFindingId.trim() || null,
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

      setNewTaskTitle("");
      setNewTaskDueAt("");
      setNewTaskAlertId("");
      setNewTaskFindingId("");
      await loadTasks(selectedOrgId);
    } catch {
      setError("Unable to create task.");
    } finally {
      setIsCreatingTask(false);
    }
  };

  const updateTask = async (payload: { status?: TaskStatus; assignee_user_id?: string }) => {
    if (!selectedTask) {
      return;
    }

    setIsSavingTask(true);
    setDetailsError(null);
    try {
      const response = await fetch(`/api/tasks/${encodeURIComponent(selectedTask.id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { message?: unknown };
        setDetailsError(typeof body.message === "string" ? body.message : "Unable to update task.");
        return;
      }

      await loadTasks(selectedOrgId);
      const updatedTask = {
        ...selectedTask,
        status: payload.status ?? selectedTask.status,
        assignee_user_id: payload.assignee_user_id ?? selectedTask.assignee_user_id,
      };
      await loadTaskDetails(updatedTask);
    } catch {
      setDetailsError("Unable to update task.");
    } finally {
      setIsSavingTask(false);
    }
  };

  const addComment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedTask || !commentBody.trim()) {
      return;
    }

    setIsSavingTask(true);
    setDetailsError(null);
    try {
      const response = await fetch(`/api/tasks/${encodeURIComponent(selectedTask.id)}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body: commentBody.trim() }),
      });

      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { message?: unknown };
        setDetailsError(typeof body.message === "string" ? body.message : "Unable to add comment.");
        return;
      }

      setCommentBody("");
      await loadTaskDetails(selectedTask);
    } catch {
      setDetailsError("Unable to add comment.");
    } finally {
      setIsSavingTask(false);
    }
  };

  const addEvidence = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedTask || !evidenceRef.trim()) {
      return;
    }

    setIsSavingTask(true);
    setDetailsError(null);
    try {
      const response = await fetch(`/api/tasks/${encodeURIComponent(selectedTask.id)}/evidence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: evidenceType, ref: evidenceRef.trim() }),
      });

      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { message?: unknown };
        setDetailsError(typeof body.message === "string" ? body.message : "Unable to add evidence.");
        return;
      }

      setEvidenceRef("");
      await loadTaskDetails(selectedTask);
    } catch {
      setDetailsError("Unable to add evidence.");
    } finally {
      setIsSavingTask(false);
    }
  };

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Tasks</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Collaborative remediation tasks tied to alerts/findings with comments, evidence, and audit timeline.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Workspace</CardTitle>
          <CardDescription>Select org context before managing tasks.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingOrgs ? <p className="text-sm text-muted-foreground">Loading organizations...</p> : null}
          {!isLoadingOrgs && orgs.length > 0 ? (
            <div className="space-y-2">
              <Label htmlFor="tasks-org-selector">Workspace</Label>
              <select
                id="tasks-org-selector"
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
          <CardTitle>Create Task</CardTitle>
          <CardDescription>Manual now, automation-ready later.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={createTask} className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="new-task-title">Title</Label>
              <Input
                id="new-task-title"
                value={newTaskTitle}
                onChange={(event) => setNewTaskTitle(event.target.value)}
                maxLength={300}
                placeholder="Investigate suspicious cert rotation"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-task-due">Due at (optional)</Label>
              <Input
                id="new-task-due"
                type="datetime-local"
                value={newTaskDueAt}
                onChange={(event) => setNewTaskDueAt(event.target.value)}
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="new-task-alert-id">Alert ID (optional)</Label>
                <Input
                  id="new-task-alert-id"
                  value={newTaskAlertId}
                  onChange={(event) => setNewTaskAlertId(event.target.value)}
                  placeholder="uuid"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="new-task-finding-id">Finding ID (optional)</Label>
                <Input
                  id="new-task-finding-id"
                  value={newTaskFindingId}
                  onChange={(event) => setNewTaskFindingId(event.target.value)}
                  placeholder="uuid"
                />
              </div>
            </div>
            <Button type="submit" disabled={isCreatingTask || !selectedOrgId}>
              {isCreatingTask ? "Creating..." : "Create Task"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Task Queue</CardTitle>
          <CardDescription>Open a task to assign, comment, attach evidence, or resolve.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoadingTasks ? <p className="text-sm text-muted-foreground">Loading tasks...</p> : null}
          {!isLoadingTasks && selectedOrgId && tasks.length === 0 ? (
            <p className="text-sm text-muted-foreground">No tasks yet for this workspace.</p>
          ) : null}
          {!isLoadingTasks && tasks.length > 0 ? (
            <ul className="space-y-2">
              {tasks.map((task) => (
                <li key={task.id} className="rounded-lg border border-border/70 px-3 py-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{task.title}</p>
                      <p className="text-xs text-muted-foreground">
                        Status: {task.status} | Assignee: {task.assignee_user_id ?? "unassigned"}
                      </p>
                      <p className="text-xs text-muted-foreground">Due: {formatTime(task.due_at)}</p>
                    </div>
                    <Button type="button" size="sm" onClick={() => void loadTaskDetails(task)}>
                      Open
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </CardContent>
      </Card>

      {isDrawerOpen && selectedTask ? (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/40">
          <div className="h-full w-full max-w-xl overflow-y-auto bg-background p-4 sm:p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Task Details</h2>
              <Button type="button" variant="outline" size="sm" onClick={() => setIsDrawerOpen(false)}>
                Close
              </Button>
            </div>

            {isLoadingDetails ? <p className="text-sm text-muted-foreground">Loading task details...</p> : null}

            {!isLoadingDetails ? (
              <div className="space-y-6">
                <section className="space-y-2 rounded-lg border border-border/70 p-3">
                  <p className="font-medium">{selectedTask.title}</p>
                  <p className="text-xs text-muted-foreground">
                    Task ID: {selectedTask.id}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Status: {selectedTask.status} | Evidence items: {selectedTaskEvidenceCount}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Alert: {selectedTask.alert_id ?? "none"} | Finding: {selectedTask.finding_id ?? "none"}
                  </p>
                  <div className="flex flex-wrap gap-2 pt-1">
                    <select
                      value={selectedTask.status}
                      onChange={(event) =>
                        void updateTask({ status: event.target.value as TaskStatus })
                      }
                      className="h-9 rounded-md border border-input bg-background px-2 text-sm"
                      disabled={isSavingTask}
                    >
                      <option value="open">open</option>
                      <option value="in_progress">in_progress</option>
                      <option value="blocked">blocked</option>
                      <option value="resolved">resolved</option>
                    </select>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={isSavingTask || !meUserId}
                      onClick={() => void updateTask({ assignee_user_id: meUserId })}
                    >
                      Assign To Me
                    </Button>
                  </div>
                </section>

                <section className="space-y-2 rounded-lg border border-border/70 p-3">
                  <h3 className="font-medium">Comments</h3>
                  {comments.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No comments yet.</p>
                  ) : (
                    <ul className="space-y-2">
                      {comments.map((comment) => (
                        <li key={comment.id} className="rounded-md border border-border/60 p-2 text-sm">
                          <p>{comment.body}</p>
                          <p className="text-xs text-muted-foreground">
                            {comment.author_user_id} at {formatTime(comment.created_at)}
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                  <form onSubmit={addComment} className="space-y-2">
                    <textarea
                      value={commentBody}
                      onChange={(event) => setCommentBody(event.target.value)}
                      className="min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      placeholder="Add context for teammates..."
                    />
                    <Button type="submit" size="sm" disabled={isSavingTask || !commentBody.trim()}>
                      Add Comment
                    </Button>
                  </form>
                </section>

                <section className="space-y-2 rounded-lg border border-border/70 p-3">
                  <h3 className="font-medium">Evidence</h3>
                  {evidence.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No evidence attached yet.</p>
                  ) : (
                    <ul className="space-y-2">
                      {evidence.map((item) => (
                        <li key={item.id} className="rounded-md border border-border/60 p-2 text-sm">
                          <p className="font-medium">{item.type}</p>
                          <p className="break-all text-xs text-muted-foreground">{item.ref}</p>
                          <p className="text-xs text-muted-foreground">
                            {item.created_by_user_id} at {formatTime(item.created_at)}
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                  <form onSubmit={addEvidence} className="space-y-2">
                    <div className="grid gap-2 sm:grid-cols-[140px_1fr]">
                      <select
                        value={evidenceType}
                        onChange={(event) => setEvidenceType(event.target.value as EvidenceType)}
                        className="h-10 rounded-md border border-input bg-background px-2 text-sm"
                      >
                        <option value="link">link</option>
                        <option value="file">file</option>
                        <option value="log">log</option>
                      </select>
                      <Input
                        value={evidenceRef}
                        onChange={(event) => setEvidenceRef(event.target.value)}
                        placeholder="URL, path, hash, or log reference"
                      />
                    </div>
                    <Button type="submit" size="sm" disabled={isSavingTask || !evidenceRef.trim()}>
                      Add Evidence
                    </Button>
                  </form>
                </section>

                <section className="space-y-2 rounded-lg border border-border/70 p-3">
                  <h3 className="font-medium">Status Timeline</h3>
                  {timeline.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No timeline events yet.</p>
                  ) : (
                    <ul className="space-y-2">
                      {timeline.map((event) => (
                        <li key={event.id} className="rounded-md border border-border/60 p-2 text-sm">
                          <p className="font-medium">{event.action}</p>
                          <p className="text-xs text-muted-foreground">
                            Actor: {event.actor_user_id ?? "system"} at {formatTime(event.created_at)}
                          </p>
                          <p className="break-all text-xs text-muted-foreground">
                            {JSON.stringify(event.metadata)}
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                {detailsError ? <p className="text-sm text-destructive">{detailsError}</p> : null}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
