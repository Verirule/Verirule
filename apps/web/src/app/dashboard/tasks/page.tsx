"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent } from "react";

type TaskStatus = "open" | "in_progress" | "blocked" | "done";
const MAX_EVIDENCE_UPLOAD_BYTES = 25_000_000;
const ALLOWED_EVIDENCE_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".txt", ".log"];

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type TaskRecord = {
  id: string;
  org_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  assignee_user_id: string | null;
  alert_id: string | null;
  finding_id: string | null;
  due_at: string | null;
  created_at: string;
  updated_at: string;
};

type TaskCommentRecord = {
  id: string;
  task_id: string;
  author_user_id: string | null;
  body: string;
  created_at: string;
};

type EvidenceFileRecord = {
  id: string;
  org_id: string;
  task_id: string;
  filename: string;
  storage_bucket: string;
  storage_path: string;
  content_type: string | null;
  byte_size: number | null;
  sha256: string | null;
  uploaded_by: string | null;
  created_at: string;
};

type OrgsResponse = { orgs: OrgRecord[] };
type TasksResponse = { tasks: TaskRecord[] };
type CommentsResponse = { comments: TaskCommentRecord[] };
type EvidenceFilesResponse = { evidence_files: EvidenceFileRecord[] };
type EvidenceFileUploadUrlResponse = {
  evidence_file_id: string;
  bucket: string;
  path: string;
  signed_upload_url: string;
  expires_in: number;
};
type EvidenceFileDownloadUrlResponse = { download_url: string; expires_in: number };

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

function formatFileSize(byteSize: number | null): string {
  if (byteSize === null || byteSize <= 0) {
    return "Unknown size";
  }
  const kb = 1024;
  const mb = kb * 1024;
  if (byteSize >= mb) {
    return `${(byteSize / mb).toFixed(2)} MB`;
  }
  if (byteSize >= kb) {
    return `${(byteSize / kb).toFixed(1)} KB`;
  }
  return `${byteSize} B`;
}

function isAllowedEvidenceFile(file: File): boolean {
  const lowerName = file.name.toLowerCase();
  return ALLOWED_EVIDENCE_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
}

function inferContentType(file: File): string | null {
  if (file.type) {
    return file.type;
  }
  const lowerName = file.name.toLowerCase();
  if (lowerName.endsWith(".pdf")) return "application/pdf";
  if (lowerName.endsWith(".png")) return "image/png";
  if (lowerName.endsWith(".jpg") || lowerName.endsWith(".jpeg")) return "image/jpeg";
  if (lowerName.endsWith(".txt") || lowerName.endsWith(".log")) return "text/plain";
  return null;
}

async function sha256Hex(file: File): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest))
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

function uploadFileToSignedUrl(
  uploadUrl: string,
  file: File,
  onProgress: (progress: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("PUT", uploadUrl, true);
    request.setRequestHeader("Content-Type", file.type || "application/octet-stream");

    request.upload.onprogress = (event) => {
      if (!event.lengthComputable) {
        return;
      }
      const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
      onProgress(percent);
    };

    request.onerror = () => reject(new Error("Upload failed."));
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        onProgress(100);
        resolve();
        return;
      }
      reject(new Error(`Upload failed (${request.status}).`));
    };

    request.send(file);
  });
}

export default function DashboardTasksPage() {
  const searchParams = useSearchParams();
  const requestedOrgId = searchParams.get("org_id")?.trim() ?? "";

  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [tasks, setTasks] = useState<TaskRecord[]>([]);
  const [selectedTask, setSelectedTask] = useState<TaskRecord | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const [statusFilter, setStatusFilter] = useState<"all" | TaskStatus>("all");
  const [search, setSearch] = useState("");

  const [comments, setComments] = useState<TaskCommentRecord[]>([]);
  const [evidenceFiles, setEvidenceFiles] = useState<EvidenceFileRecord[]>([]);

  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [isSavingTask, setIsSavingTask] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [downloadingEvidenceId, setDownloadingEvidenceId] = useState<string | null>(null);
  const [deletingEvidenceId, setDeletingEvidenceId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [detailsError, setDetailsError] = useState<string | null>(null);

  const [commentBody, setCommentBody] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const filteredTasks = useMemo(() => {
    const query = search.trim().toLowerCase();
    return tasks.filter((task) => {
      if (statusFilter !== "all" && task.status !== statusFilter) {
        return false;
      }
      if (!query) {
        return true;
      }
      const haystack = `${task.title} ${task.description ?? ""}`.toLowerCase();
      return haystack.includes(query);
    });
  }, [search, statusFilter, tasks]);

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

      setTasks(body.tasks);
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
      const [commentsResponse, evidenceResponse] = await Promise.all([
        fetch(`/api/tasks/${encodeURIComponent(task.id)}/comments`, {
          method: "GET",
          cache: "no-store",
        }),
        fetch(
          `/api/tasks/${encodeURIComponent(task.id)}/evidence-files?org_id=${encodeURIComponent(selectedOrgId)}`,
          {
            method: "GET",
            cache: "no-store",
          },
        ),
      ]);

      const commentsBody = (await commentsResponse.json().catch(() => ({}))) as Partial<CommentsResponse>;
      const evidenceBody = (await evidenceResponse.json().catch(() => ({}))) as Partial<EvidenceFilesResponse>;

      if (!commentsResponse.ok || !Array.isArray(commentsBody.comments)) {
        setDetailsError("Unable to load task comments.");
        return;
      }

      if (!evidenceResponse.ok || !Array.isArray(evidenceBody.evidence_files)) {
        setDetailsError("Unable to load task evidence files.");
        return;
      }

      setComments(commentsBody.comments);
      setEvidenceFiles(evidenceBody.evidence_files);
    } catch {
      setDetailsError("Unable to load task details.");
    } finally {
      setIsLoadingDetails(false);
    }
  };

  useEffect(() => {
    void loadOrgs();
  }, [loadOrgs]);

  useEffect(() => {
    if (!selectedOrgId) {
      setTasks([]);
      return;
    }
    void loadTasks(selectedOrgId);
  }, [selectedOrgId]);

  const updateTaskStatus = async (status: TaskStatus) => {
    if (!selectedTask) {
      return;
    }

    setIsSavingTask(true);
    setDetailsError(null);
    try {
      const response = await fetch(`/api/tasks/${encodeURIComponent(selectedTask.id)}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { message?: unknown };
        setDetailsError(typeof body.message === "string" ? body.message : "Unable to update task status.");
        return;
      }

      const updatedTask = { ...selectedTask, status };
      setSelectedTask(updatedTask);
      await loadTasks(selectedOrgId);
      await loadTaskDetails(updatedTask);
    } catch {
      setDetailsError("Unable to update task status.");
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

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

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

  const beginFileUpload = () => {
    fileInputRef.current?.click();
  };

  const onFileSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    if (!selectedTask || !selectedOrgId || !file) {
      return;
    }
    if (!isAllowedEvidenceFile(file)) {
      setDetailsError("Unsupported file type. Allowed: pdf, png, jpg, txt, log.");
      event.target.value = "";
      return;
    }
    if (file.size > MAX_EVIDENCE_UPLOAD_BYTES) {
      setDetailsError("File exceeds 25 MB limit.");
      event.target.value = "";
      return;
    }

    setIsUploadingFile(true);
    setUploadProgress(0);
    setDetailsError(null);

    try {
      const uploadUrlResponse = await fetch(
        `/api/tasks/${encodeURIComponent(selectedTask.id)}/evidence-files/upload-url`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            org_id: selectedOrgId,
            filename: file.name,
            content_type: inferContentType(file),
            byte_size: file.size,
          }),
        },
      );

      if (uploadUrlResponse.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      const uploadUrlBody = (await uploadUrlResponse.json().catch(() => ({}))) as Partial<EvidenceFileUploadUrlResponse> &
        { message?: unknown };
      if (!uploadUrlResponse.ok) {
        setDetailsError(
          typeof uploadUrlBody.message === "string"
            ? uploadUrlBody.message
            : "Unable to request file upload URL.",
        );
        return;
      }

      const uploadUrl =
        typeof uploadUrlBody.signed_upload_url === "string" ? uploadUrlBody.signed_upload_url : "";
      const evidenceFileId =
        typeof uploadUrlBody.evidence_file_id === "string" ? uploadUrlBody.evidence_file_id : "";
      if (!uploadUrl || !evidenceFileId) {
        setDetailsError("Unable to request file upload URL.");
        return;
      }

      await uploadFileToSignedUrl(uploadUrl, file, setUploadProgress);
      const sha256 = await sha256Hex(file);

      const finalizeResponse = await fetch(
        `/api/evidence-files/${encodeURIComponent(evidenceFileId)}/finalize`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ org_id: selectedOrgId, sha256 }),
        },
      );

      if (finalizeResponse.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!finalizeResponse.ok) {
        const body = (await finalizeResponse.json().catch(() => ({}))) as { message?: unknown };
        setDetailsError(
          typeof body.message === "string" ? body.message : "Unable to finalize file evidence.",
        );
        return;
      }

      await loadTaskDetails(selectedTask);
    } catch {
      setDetailsError("Unable to upload file evidence.");
    } finally {
      setIsUploadingFile(false);
      setUploadProgress(null);
      event.target.value = "";
    }
  };

  const openEvidenceFile = async (item: EvidenceFileRecord) => {
    if (!selectedOrgId) {
      return;
    }

    setDownloadingEvidenceId(item.id);
    setDetailsError(null);

    try {
      const response = await fetch(
        `/api/evidence-files/${encodeURIComponent(item.id)}/download-url?org_id=${encodeURIComponent(selectedOrgId)}`,
        {
          method: "GET",
          cache: "no-store",
        },
      );

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      const body = (await response.json().catch(() => ({}))) as Partial<EvidenceFileDownloadUrlResponse> & {
        message?: unknown;
      };

      if (!response.ok || typeof body.download_url !== "string") {
        setDetailsError(typeof body.message === "string" ? body.message : "Unable to fetch download URL.");
        return;
      }

      window.open(body.download_url, "_blank", "noopener,noreferrer");
    } catch {
      setDetailsError("Unable to fetch download URL.");
    } finally {
      setDownloadingEvidenceId(null);
    }
  };

  const deleteEvidenceFile = async (item: EvidenceFileRecord) => {
    if (!selectedTask || !selectedOrgId) {
      return;
    }
    const confirmed = window.confirm(`Delete evidence file "${item.filename}"?`);
    if (!confirmed) {
      return;
    }

    setDeletingEvidenceId(item.id);
    setDetailsError(null);
    try {
      const response = await fetch(
        `/api/evidence-files/${encodeURIComponent(item.id)}?org_id=${encodeURIComponent(selectedOrgId)}`,
        {
          method: "DELETE",
          cache: "no-store",
        },
      );
      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { message?: unknown };
        setDetailsError(typeof body.message === "string" ? body.message : "Unable to delete evidence file.");
        return;
      }
      await loadTaskDetails(selectedTask);
    } catch {
      setDetailsError("Unable to delete evidence file.");
    } finally {
      setDeletingEvidenceId(null);
    }
  };

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Tasks</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Actionable remediation workflows with comments and evidence tracking.
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
          <CardTitle>Task Queue</CardTitle>
          <CardDescription>Filter by status and search title/description.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-[180px_1fr]">
            <div className="space-y-2">
              <Label htmlFor="task-status-filter">Status</Label>
              <select
                id="task-status-filter"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value as "all" | TaskStatus)}
                className="h-10 rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="all">all</option>
                <option value="open">open</option>
                <option value="in_progress">in_progress</option>
                <option value="blocked">blocked</option>
                <option value="done">done</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="task-search">Search</Label>
              <Input
                id="task-search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search task title or description"
              />
            </div>
          </div>

          {isLoadingTasks ? <p className="text-sm text-muted-foreground">Loading tasks...</p> : null}
          {!isLoadingTasks && selectedOrgId && filteredTasks.length === 0 ? (
            <p className="text-sm text-muted-foreground">No tasks match this filter.</p>
          ) : null}

          {!isLoadingTasks && filteredTasks.length > 0 ? (
            <ul className="space-y-2">
              {filteredTasks.map((task) => (
                <li key={task.id} className="rounded-lg border border-border/70 px-3 py-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{task.title}</p>
                      <p className="text-xs text-muted-foreground">Status: {task.status}</p>
                      <p className="text-xs text-muted-foreground">Updated: {formatTime(task.updated_at)}</p>
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
                  <p className="text-xs text-muted-foreground">{selectedTask.description ?? "No description"}</p>
                  <p className="text-xs text-muted-foreground">Alert: {selectedTask.alert_id ?? "none"}</p>
                  <p className="text-xs text-muted-foreground">Finding: {selectedTask.finding_id ?? "none"}</p>
                  <p className="text-xs text-muted-foreground">Assignee: {selectedTask.assignee_user_id ?? "none"}</p>
                  <div className="pt-1">
                    <Label htmlFor="task-status" className="text-xs">
                      Status
                    </Label>
                    <select
                      id="task-status"
                      value={selectedTask.status}
                      onChange={(event) => void updateTaskStatus(event.target.value as TaskStatus)}
                      className="mt-1 h-9 rounded-md border border-input bg-background px-2 text-sm"
                      disabled={isSavingTask}
                    >
                      <option value="open">open</option>
                      <option value="in_progress">in_progress</option>
                      <option value="blocked">blocked</option>
                      <option value="done">done</option>
                    </select>
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
                            {comment.author_user_id ?? "unknown"} at {formatTime(comment.created_at)}
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
                    <Button
                      type="submit"
                      size="sm"
                      disabled={isSavingTask || isUploadingFile || !commentBody.trim()}
                    >
                      Add Comment
                    </Button>
                  </form>
                </section>

                <section className="space-y-2 rounded-lg border border-border/70 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-medium">Evidence Files</h3>
                    <div className="flex items-center gap-2">
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf,.png,.jpg,.jpeg,.txt,.log"
                        className="hidden"
                        onChange={onFileSelected}
                      />
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={isUploadingFile || isSavingTask}
                        onClick={beginFileUpload}
                      >
                        {isUploadingFile ? "Uploading..." : "Upload evidence file"}
                      </Button>
                    </div>
                  </div>

                  {uploadProgress !== null ? (
                    <p className="text-xs text-muted-foreground">Upload progress: {uploadProgress}%</p>
                  ) : null}

                  {evidenceFiles.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No evidence files attached yet.</p>
                  ) : (
                    <ul className="space-y-2">
                      {evidenceFiles.map((item) => (
                        <li key={item.id} className="rounded-md border border-border/60 p-2 text-sm">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div className="min-w-0">
                              <p className="font-medium">{item.filename}</p>
                              <p className="text-xs text-muted-foreground">{formatFileSize(item.byte_size)}</p>
                              <p className="text-xs text-muted-foreground">{formatTime(item.created_at)}</p>
                            </div>
                            <div className="flex items-center gap-2">
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                disabled={
                                  downloadingEvidenceId === item.id ||
                                  deletingEvidenceId === item.id ||
                                  isUploadingFile
                                }
                                onClick={() => void openEvidenceFile(item)}
                              >
                                {downloadingEvidenceId === item.id ? "Loading..." : "Download"}
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                disabled={
                                  deletingEvidenceId === item.id ||
                                  downloadingEvidenceId === item.id ||
                                  isUploadingFile
                                }
                                onClick={() => void deleteEvidenceFile(item)}
                              >
                                {deletingEvidenceId === item.id ? "Deleting..." : "Delete"}
                              </Button>
                            </div>
                          </div>
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
