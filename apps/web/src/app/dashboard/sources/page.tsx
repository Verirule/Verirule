"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useEffect, useMemo, useState, type FormEvent } from "react";

type SourceType = "rss" | "url";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type SourceRecord = {
  id: string;
  org_id: string;
  name: string;
  type: SourceType;
  url: string;
  is_enabled: boolean;
  created_at: string;
};

type MonitorRunStatus = "queued" | "running" | "succeeded" | "failed";

type MonitorRunRecord = {
  id: string;
  org_id: string;
  source_id: string;
  status: MonitorRunStatus;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  created_at: string;
};

type OrgsResponse = { orgs: OrgRecord[] };
type SourcesResponse = { sources: SourceRecord[] };
type RunsResponse = { runs: MonitorRunRecord[] };

function formatCreatedAt(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown date";
  }
  return parsed.toLocaleDateString();
}

function normalizeUrl(value: string): string {
  return value.trim();
}

export default function DashboardSourcesPage() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [runs, setRuns] = useState<MonitorRunRecord[]>([]);

  const [name, setName] = useState("");
  const [type, setType] = useState<SourceType>("rss");
  const [url, setUrl] = useState("");

  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingSources, setIsLoadingSources] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const trimmedName = useMemo(() => name.trim(), [name]);
  const trimmedUrl = useMemo(() => normalizeUrl(url), [url]);
  const latestRunBySource = useMemo(() => {
    const map = new Map<string, MonitorRunRecord>();
    for (const run of runs) {
      if (!map.has(run.source_id)) {
        map.set(run.source_id, run);
      }
    }
    return map;
  }, [runs]);

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

  const loadSourcesAndRuns = async (orgId: string) => {
    if (!orgId) {
      setSources([]);
      setRuns([]);
      return;
    }

    setIsLoadingSources(true);
    setError(null);

    try {
      const [sourcesResponse, runsResponse] = await Promise.all([
        fetch(`/api/sources?org_id=${encodeURIComponent(orgId)}`, {
          method: "GET",
          cache: "no-store",
        }),
        fetch(`/api/monitor-runs?org_id=${encodeURIComponent(orgId)}`, {
          method: "GET",
          cache: "no-store",
        }),
      ]);
      const sourcesBody = (await sourcesResponse.json().catch(() => ({}))) as Partial<SourcesResponse>;
      const runsBody = (await runsResponse.json().catch(() => ({}))) as Partial<RunsResponse>;

      if (sourcesResponse.status === 401 || runsResponse.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!sourcesResponse.ok || !Array.isArray(sourcesBody.sources)) {
        setError("Unable to load sources right now.");
        setSources([]);
        setRuns([]);
        return;
      }

      if (!runsResponse.ok || !Array.isArray(runsBody.runs)) {
        setError("Unable to load monitor runs right now.");
        setRuns([]);
        setSources(sourcesBody.sources);
        return;
      }

      const sourceRows = sourcesBody.sources;
      setSources(sourceRows);
      setRuns(runsBody.runs);
    } catch {
      setError("Unable to load sources right now.");
      setSources([]);
      setRuns([]);
    } finally {
      setIsLoadingSources(false);
    }
  };

  useEffect(() => {
    void loadOrgs();
  }, []);

  useEffect(() => {
    if (!selectedOrgId) {
      setSources([]);
      setRuns([]);
      return;
    }
    void loadSourcesAndRuns(selectedOrgId);
  }, [selectedOrgId]);

  const createSource = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (!selectedOrgId) {
      setError("Select an organization first.");
      return;
    }
    if (trimmedName.length < 1 || trimmedName.length > 120) {
      setError("Source name must be between 1 and 120 characters.");
      return;
    }
    if (!trimmedUrl) {
      setError("Source URL is required.");
      return;
    }

    setIsCreating(true);
    try {
      const response = await fetch("/api/sources", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          org_id: selectedOrgId,
          name: trimmedName,
          type,
          url: trimmedUrl,
        }),
      });

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        setError("Unable to create source right now.");
        return;
      }

      setName("");
      setType("rss");
      setUrl("");
      await loadSourcesAndRuns(selectedOrgId);
    } catch {
      setError("Unable to create source right now.");
    } finally {
      setIsCreating(false);
    }
  };

  const toggleSource = async (sourceId: string, nextState: boolean) => {
    setTogglingId(sourceId);
    setError(null);

    try {
      const response = await fetch(`/api/sources/${sourceId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_enabled: nextState }),
      });

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        setError("Unable to update source right now.");
        return;
      }

      setSources((current) =>
        current.map((source) =>
          source.id === sourceId ? { ...source, is_enabled: nextState } : source,
        ),
      );
    } catch {
      setError("Unable to update source right now.");
    } finally {
      setTogglingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Sources</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage per-organization ingestion sources through the same-origin API proxy.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Organization</CardTitle>
          <CardDescription>Select the workspace to view and manage sources.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingOrgs ? <p className="text-sm text-muted-foreground">Loading organizations...</p> : null}
          {!isLoadingOrgs && orgs.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No organizations found. Create one from the dashboard overview first.
            </p>
          ) : null}
          {!isLoadingOrgs && orgs.length > 0 ? (
            <div className="space-y-2">
              <Label htmlFor="org-selector">Workspace</Label>
              <select
                id="org-selector"
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
          <CardTitle>Current Sources</CardTitle>
          <CardDescription>Sources are scoped by org membership via database RLS.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoadingSources ? <p className="text-sm text-muted-foreground">Loading sources...</p> : null}
          {!isLoadingSources && selectedOrgId && sources.length === 0 ? (
            <p className="text-sm text-muted-foreground">No sources yet for this workspace.</p>
          ) : null}
          {!isLoadingSources && sources.length > 0 ? (
            <ul className="space-y-2">
              {sources.map((source) => (
                <li
                  key={source.id}
                  className="rounded-lg border border-border/70 bg-card px-3 py-3 text-sm shadow-sm"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 space-y-1">
                      <div className="font-medium">{source.name}</div>
                      <div className="text-xs uppercase tracking-wide text-muted-foreground">
                        {source.type}
                      </div>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        className="block truncate text-xs text-primary hover:underline"
                      >
                        {source.url}
                      </a>
                      <div className="text-xs text-muted-foreground">
                        Added {formatCreatedAt(source.created_at)}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Last run: {latestRunBySource.get(source.id)?.status ?? "never"}
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant={source.is_enabled ? "outline" : "default"}
                      size="sm"
                      disabled={togglingId === source.id}
                      onClick={() => toggleSource(source.id, !source.is_enabled)}
                    >
                      {togglingId === source.id
                        ? "Saving..."
                        : source.is_enabled
                          ? "Disable"
                          : "Enable"}
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Add Source</CardTitle>
          <CardDescription>Create a new RSS or URL source for the selected workspace.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={createSource} className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="source-name">Name</Label>
              <Input
                id="source-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Security Blog RSS"
                autoComplete="off"
                maxLength={120}
                disabled={isCreating || !selectedOrgId}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="source-type">Type</Label>
              <select
                id="source-type"
                value={type}
                onChange={(event) => setType(event.target.value as SourceType)}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                disabled={isCreating || !selectedOrgId}
              >
                <option value="rss">rss</option>
                <option value="url">url</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="source-url">URL</Label>
              <Input
                id="source-url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://example.com/feed.xml"
                autoComplete="off"
                maxLength={2048}
                disabled={isCreating || !selectedOrgId}
              />
            </div>
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            <Button type="submit" disabled={isCreating || !selectedOrgId}>
              {isCreating ? "Creating..." : "Create source"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
