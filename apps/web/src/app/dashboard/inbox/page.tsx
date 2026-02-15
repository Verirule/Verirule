"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type MeResponse = {
  sub?: unknown;
};

type MemberRole = "owner" | "admin" | "member" | "viewer";

type MemberRecord = {
  org_id: string;
  user_id: string;
  role: MemberRole;
  created_at: string;
};

type NotificationType = "digest" | "immediate_alert";
type NotificationStatus = "queued" | "sent" | "failed";
type NotificationEntityType = "alert" | "task" | "export" | "system";

type InboxEvent = {
  id: string;
  org_id: string;
  user_id: string | null;
  job_id: string;
  type: NotificationType;
  entity_type: NotificationEntityType | null;
  entity_id: string | null;
  subject: string;
  status: NotificationStatus;
  attempts: number;
  last_error: string | null;
  sent_at: string | null;
  created_at: string;
  read_at: string | null;
  is_read: boolean;
};

type OrgsResponse = { orgs?: unknown };
type MembersResponse = { members?: unknown; message?: unknown };
type InboxResponse = { events?: unknown; message?: unknown };

type FilterMode = "all" | "unread" | "failed";

function formatTime(value: string | null): string {
  if (!value) {
    return "Not sent";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown time";
  }
  return parsed.toLocaleString();
}

function normalizeOrgs(payload: OrgsResponse): OrgRecord[] {
  if (!Array.isArray(payload.orgs)) {
    return [];
  }

  return payload.orgs
    .map((row) => {
      if (!row || typeof row !== "object") {
        return null;
      }
      const org = row as Record<string, unknown>;
      if (
        typeof org.id !== "string" ||
        typeof org.name !== "string" ||
        typeof org.created_at !== "string"
      ) {
        return null;
      }
      return { id: org.id, name: org.name, created_at: org.created_at };
    })
    .filter((row): row is OrgRecord => row !== null);
}

function normalizeMembers(payload: MembersResponse): MemberRecord[] {
  if (!Array.isArray(payload.members)) {
    return [];
  }

  return payload.members
    .map((row) => {
      if (!row || typeof row !== "object") {
        return null;
      }
      const member = row as Record<string, unknown>;
      const role = member.role;
      if (
        typeof member.org_id !== "string" ||
        typeof member.user_id !== "string" ||
        (role !== "owner" && role !== "admin" && role !== "member" && role !== "viewer") ||
        typeof member.created_at !== "string"
      ) {
        return null;
      }
      return {
        org_id: member.org_id,
        user_id: member.user_id,
        role,
        created_at: member.created_at,
      };
    })
    .filter((row): row is MemberRecord => row !== null);
}

function normalizeInbox(payload: InboxResponse): InboxEvent[] {
  if (!Array.isArray(payload.events)) {
    return [];
  }

  return payload.events
    .map((row) => {
      if (!row || typeof row !== "object") {
        return null;
      }
      const event = row as Record<string, unknown>;
      const status = event.status;
      const type = event.type;
      const entityType = event.entity_type;
      if (
        typeof event.id !== "string" ||
        typeof event.org_id !== "string" ||
        typeof event.job_id !== "string" ||
        (type !== "digest" && type !== "immediate_alert") ||
        (status !== "queued" && status !== "sent" && status !== "failed") ||
        typeof event.subject !== "string" ||
        typeof event.attempts !== "number" ||
        typeof event.created_at !== "string"
      ) {
        return null;
      }
      return {
        id: event.id,
        org_id: event.org_id,
        user_id: typeof event.user_id === "string" ? event.user_id : null,
        job_id: event.job_id,
        type,
        entity_type:
          entityType === "alert" || entityType === "task" || entityType === "export" || entityType === "system"
            ? entityType
            : null,
        entity_id: typeof event.entity_id === "string" ? event.entity_id : null,
        subject: event.subject,
        status,
        attempts: event.attempts,
        last_error: typeof event.last_error === "string" ? event.last_error : null,
        sent_at: typeof event.sent_at === "string" ? event.sent_at : null,
        created_at: event.created_at,
        read_at: typeof event.read_at === "string" ? event.read_at : null,
        is_read: Boolean(event.is_read),
      };
    })
    .filter((row): row is InboxEvent => row !== null);
}

function statusClass(status: NotificationStatus): string {
  if (status === "sent") return "bg-emerald-100 text-emerald-800";
  if (status === "failed") return "bg-red-100 text-red-700";
  return "bg-amber-100 text-amber-900";
}

function statusLabel(status: NotificationStatus): string {
  if (status === "queued") return "Queued";
  if (status === "sent") return "Sent";
  return "Failed";
}

function typeLabel(type: NotificationType): string {
  if (type === "immediate_alert") return "Immediate";
  return "Digest";
}

function entityHref(event: InboxEvent): string {
  const orgQuery = `org_id=${encodeURIComponent(event.org_id)}`;
  if (event.entity_type === "alert" && event.entity_id) {
    return `/dashboard/alerts/${encodeURIComponent(event.entity_id)}?${orgQuery}`;
  }
  if (event.entity_type === "task" && event.entity_id) {
    return `/dashboard/tasks?${orgQuery}&task_id=${encodeURIComponent(event.entity_id)}`;
  }
  if (event.entity_type === "export") {
    const exportQuery = event.entity_id ? `&export_id=${encodeURIComponent(event.entity_id)}` : "";
    return `/dashboard/exports?${orgQuery}${exportQuery}`;
  }
  return `/dashboard?${orgQuery}`;
}

export default function DashboardInboxPage() {
  const searchParams = useSearchParams();
  const requestedOrgId = searchParams.get("org_id")?.trim() ?? "";

  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [currentUserId, setCurrentUserId] = useState("");
  const [canRetry, setCanRetry] = useState(false);

  const [events, setEvents] = useState<InboxEvent[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterMode>("all");

  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingInbox, setIsLoadingInbox] = useState(false);
  const [isUpdatingReadState, setIsUpdatingReadState] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const selectedEvent = useMemo(
    () => events.find((event) => event.id === selectedEventId) ?? null,
    [events, selectedEventId],
  );

  const filteredEvents = useMemo(() => {
    if (filter === "unread") {
      return events.filter((event) => !event.is_read);
    }
    if (filter === "failed") {
      return events.filter((event) => event.status === "failed");
    }
    return events;
  }, [events, filter]);

  const unreadCount = useMemo(() => events.filter((event) => !event.is_read).length, [events]);

  const loadCurrentUser = useCallback(async () => {
    try {
      const response = await fetch("/api/me", { method: "GET", cache: "no-store" });
      const body = (await response.json().catch(() => ({}))) as MeResponse;

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      setCurrentUserId(typeof body.sub === "string" ? body.sub : "");
    } catch {
      setCurrentUserId("");
    }
  }, []);

  const loadOrgs = useCallback(async () => {
    setIsLoadingOrgs(true);
    setError(null);

    try {
      const response = await fetch("/api/orgs", { method: "GET", cache: "no-store" });
      const body = (await response.json().catch(() => ({}))) as OrgsResponse;

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        setError("Unable to load workspaces.");
        setOrgs([]);
        setSelectedOrgId("");
        return;
      }

      const rows = normalizeOrgs(body);
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
      setError("Unable to load workspaces.");
      setOrgs([]);
      setSelectedOrgId("");
    } finally {
      setIsLoadingOrgs(false);
    }
  }, [requestedOrgId]);

  const loadInbox = useCallback(async (orgId: string) => {
    if (!orgId) {
      setEvents([]);
      return;
    }

    setIsLoadingInbox(true);
    setError(null);

    try {
      const response = await fetch(`/api/orgs/${encodeURIComponent(orgId)}/notifications/inbox?limit=100`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as InboxResponse;

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        const detail = typeof body.message === "string" ? body.message : "Unable to load inbox.";
        setError(detail);
        setEvents([]);
        return;
      }

      const rows = normalizeInbox(body);
      setEvents(rows);
      setSelectedEventId((current) => (current && rows.some((event) => event.id === current) ? current : null));
    } catch {
      setError("Unable to load inbox.");
      setEvents([]);
    } finally {
      setIsLoadingInbox(false);
    }
  }, []);

  const loadRole = useCallback(async (orgId: string, userId: string) => {
    if (!orgId || !userId) {
      setCanRetry(false);
      return;
    }

    try {
      const response = await fetch(`/api/orgs/${encodeURIComponent(orgId)}/members`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as MembersResponse;

      if (!response.ok) {
        setCanRetry(false);
        return;
      }

      const members = normalizeMembers(body);
      const role = members.find((member) => member.user_id === userId)?.role;
      setCanRetry(role === "owner" || role === "admin");
    } catch {
      setCanRetry(false);
    }
  }, []);

  useEffect(() => {
    void loadCurrentUser();
    void loadOrgs();
  }, [loadCurrentUser, loadOrgs]);

  useEffect(() => {
    if (!selectedOrgId) {
      setEvents([]);
      setCanRetry(false);
      return;
    }

    void loadInbox(selectedOrgId);
    void loadRole(selectedOrgId, currentUserId);
  }, [selectedOrgId, currentUserId, loadInbox, loadRole]);

  const toggleRead = async () => {
    if (!selectedEvent) {
      return;
    }

    setIsUpdatingReadState(true);
    setError(null);
    setMessage(null);

    try {
      const method = selectedEvent.is_read ? "DELETE" : "POST";
      const response = await fetch(`/api/notifications/${encodeURIComponent(selectedEvent.id)}/read`, {
        method,
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as { message?: unknown };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        const detail = typeof body.message === "string" ? body.message : "Unable to update read state.";
        setError(detail);
        return;
      }

      const nextRead = !selectedEvent.is_read;
      const nowIso = new Date().toISOString();
      setEvents((current) =>
        current.map((event) =>
          event.id === selectedEvent.id
            ? {
                ...event,
                is_read: nextRead,
                read_at: nextRead ? nowIso : null,
              }
            : event,
        ),
      );
      setMessage(nextRead ? "Marked as read." : "Marked as unread.");
    } catch {
      setError("Unable to update read state.");
    } finally {
      setIsUpdatingReadState(false);
    }
  };

  const retrySend = async () => {
    if (!selectedEvent || !canRetry || selectedEvent.status !== "failed") {
      return;
    }

    setIsRetrying(true);
    setError(null);
    setMessage(null);

    try {
      const response = await fetch(`/api/notifications/jobs/${encodeURIComponent(selectedEvent.job_id)}/requeue`, {
        method: "POST",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as { message?: unknown };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        const detail = typeof body.message === "string" ? body.message : "Unable to requeue this notification.";
        setError(detail);
        return;
      }

      setMessage("Notification job requeued.");
      await loadInbox(selectedOrgId);
    } catch {
      setError("Unable to requeue this notification.");
    } finally {
      setIsRetrying(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>Inbox</CardTitle>
              <CardDescription>Delivery events for your in-app notifications.</CardDescription>
            </div>
            <Badge variant="outline" className="text-xs">
              Unread: {unreadCount}
            </Badge>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="inbox-org-select">Workspace</Label>
              <select
                id="inbox-org-select"
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={selectedOrgId}
                onChange={(event) => setSelectedOrgId(event.target.value)}
                disabled={isLoadingOrgs || orgs.length === 0}
              >
                {orgs.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label>Filter</Label>
              <div className="flex flex-wrap gap-2">
                <Button variant={filter === "all" ? "default" : "outline"} onClick={() => setFilter("all")}>
                  All
                </Button>
                <Button variant={filter === "unread" ? "default" : "outline"} onClick={() => setFilter("unread")}>
                  Unread
                </Button>
                <Button variant={filter === "failed" ? "default" : "outline"} onClick={() => setFilter("failed")}>
                  Failed
                </Button>
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-3">
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {message ? <p className="text-sm text-emerald-700">{message}</p> : null}

          {isLoadingInbox ? <p className="text-sm text-muted-foreground">Loading inbox...</p> : null}

          {!isLoadingInbox && filteredEvents.length === 0 ? (
            <p className="text-sm text-muted-foreground">No notifications for this filter.</p>
          ) : null}

          <div className="space-y-2">
            {filteredEvents.map((event) => (
              <button
                key={event.id}
                type="button"
                onClick={() => setSelectedEventId(event.id)}
                className={cn(
                  "w-full rounded-lg border px-4 py-3 text-left transition-colors",
                  selectedEventId === event.id
                    ? "border-[var(--vr-user-accent)] bg-accent"
                    : "border-border hover:bg-accent/50",
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", statusClass(event.status))}>
                    {statusLabel(event.status)}
                  </span>
                  <span className="text-xs text-muted-foreground">{typeLabel(event.type)}</span>
                  {!event.is_read ? (
                    <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                      Unread
                    </span>
                  ) : null}
                </div>
                <p className="mt-2 text-sm font-medium">{event.subject}</p>
                <p className="mt-1 text-xs text-muted-foreground">{formatTime(event.sent_at ?? event.created_at)}</p>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {selectedEvent ? (
        <div className="fixed inset-0 z-50">
          <button
            type="button"
            className="absolute inset-0 bg-black/35"
            aria-label="Close notification details"
            onClick={() => setSelectedEventId(null)}
          />

          <aside className="absolute right-0 top-0 h-full w-full max-w-md overflow-y-auto border-l bg-background p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Notification</h2>
                <p className="text-sm text-muted-foreground">{selectedEvent.subject}</p>
              </div>
              <Button variant="outline" onClick={() => setSelectedEventId(null)}>
                Close
              </Button>
            </div>

            <div className="mt-6 space-y-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Entity</p>
                <Link href={entityHref(selectedEvent)} className="text-sm font-medium underline">
                  {selectedEvent.entity_type ? `Open ${selectedEvent.entity_type}` : "Open dashboard"}
                </Link>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Status</p>
                  <p className="text-sm">{statusLabel(selectedEvent.status)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Attempts</p>
                  <p className="text-sm">{selectedEvent.attempts}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Type</p>
                  <p className="text-sm">{typeLabel(selectedEvent.type)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Created</p>
                  <p className="text-sm">{formatTime(selectedEvent.created_at)}</p>
                </div>
              </div>

              {selectedEvent.last_error ? (
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Last error</p>
                  <p className="mt-1 rounded-md border bg-muted p-3 text-sm">{selectedEvent.last_error}</p>
                </div>
              ) : null}

              <div className="flex flex-wrap gap-2">
                <Button onClick={toggleRead} disabled={isUpdatingReadState}>
                  {selectedEvent.is_read ? "Mark unread" : "Mark read"}
                </Button>

                {selectedEvent.status === "failed" && canRetry ? (
                  <Button variant="outline" onClick={retrySend} disabled={isRetrying}>
                    Retry send
                  </Button>
                ) : null}
              </div>
            </div>
          </aside>
        </div>
      ) : null}
    </div>
  );
}
