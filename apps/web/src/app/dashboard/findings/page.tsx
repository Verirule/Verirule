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

type FindingSeverity = "low" | "medium" | "high" | "critical";

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
  canonical_title: string | null;
  item_published_at: string | null;
  has_explanation: boolean;
};

type OrgsResponse = { orgs: OrgRecord[] };
type FindingsResponse = { findings: FindingRecord[] };
type FindingExplanationCitation = {
  quote: string;
  context: string;
};
type FindingExplanation = {
  id: string;
  org_id: string;
  finding_id: string;
  summary: string;
  diff_preview: string | null;
  citations: FindingExplanationCitation[];
  created_at: string;
};

type SeverityFilter = "all" | FindingSeverity;

function formatTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown time";
  }
  return parsed.toLocaleString();
}

function severityClass(severity: FindingSeverity): string {
  if (severity === "critical") return "bg-red-100 text-red-700";
  if (severity === "high") return "bg-orange-100 text-orange-700";
  if (severity === "medium") return "bg-amber-100 text-amber-800";
  return "bg-slate-100 text-slate-700";
}

export default function DashboardFindingsPage() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [findings, setFindings] = useState<FindingRecord[]>([]);

  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingFindings, setIsLoadingFindings] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedFinding, setSelectedFinding] = useState<FindingRecord | null>(null);
  const [explanation, setExplanation] = useState<FindingExplanation | null>(null);
  const [isLoadingExplanation, setIsLoadingExplanation] = useState(false);
  const [explanationError, setExplanationError] = useState<string | null>(null);
  const [showExplanation, setShowExplanation] = useState(false);

  const filteredFindings = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    return findings.filter((finding) => {
      if (severityFilter !== "all" && finding.severity !== severityFilter) {
        return false;
      }
      if (!query) {
        return true;
      }
      return (
        finding.title.toLowerCase().includes(query) ||
        finding.summary.toLowerCase().includes(query) ||
        finding.fingerprint.toLowerCase().includes(query)
      );
    });
  }, [findings, searchTerm, severityFilter]);

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

  const loadFindings = async (orgId: string) => {
    if (!orgId) {
      setFindings([]);
      return;
    }

    setIsLoadingFindings(true);
    setError(null);
    try {
      const response = await fetch(`/api/findings?org_id=${encodeURIComponent(orgId)}`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<FindingsResponse>;

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.findings)) {
        setError("Unable to load findings right now.");
        setFindings([]);
        return;
      }

      setFindings(body.findings);
    } catch {
      setError("Unable to load findings right now.");
      setFindings([]);
    } finally {
      setIsLoadingFindings(false);
    }
  };

  useEffect(() => {
    void loadOrgs();
  }, []);

  useEffect(() => {
    if (!selectedOrgId) {
      setFindings([]);
      return;
    }
    void loadFindings(selectedOrgId);
  }, [selectedOrgId]);

  const loadExplanation = async (findingId: string) => {
    setIsLoadingExplanation(true);
    setExplanationError(null);
    try {
      const response = await fetch(`/api/findings/${encodeURIComponent(findingId)}/explanation`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<FindingExplanation>;

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (response.status === 404) {
        setExplanation(null);
        setExplanationError("No explanation is available for this finding yet.");
        return;
      }

      if (
        !response.ok ||
        typeof body.id !== "string" ||
        typeof body.summary !== "string" ||
        !Array.isArray(body.citations)
      ) {
        setExplanation(null);
        setExplanationError("Unable to load explanation right now.");
        return;
      }

      setExplanation({
        id: body.id,
        org_id: typeof body.org_id === "string" ? body.org_id : "",
        finding_id: typeof body.finding_id === "string" ? body.finding_id : findingId,
        summary: body.summary,
        diff_preview: typeof body.diff_preview === "string" ? body.diff_preview : null,
        citations: body.citations
          .filter(
            (item): item is FindingExplanationCitation =>
              typeof item === "object" &&
              item !== null &&
              typeof (item as { quote?: unknown }).quote === "string" &&
              typeof (item as { context?: unknown }).context === "string",
          )
          .slice(0, 20),
        created_at: typeof body.created_at === "string" ? body.created_at : "",
      });
    } catch {
      setExplanation(null);
      setExplanationError("Unable to load explanation right now.");
    } finally {
      setIsLoadingExplanation(false);
    }
  };

  const openDetails = (finding: FindingRecord) => {
    setSelectedFinding(finding);
    setShowExplanation(false);
    setExplanation(null);
    setExplanationError(null);
    setIsLoadingExplanation(false);
  };

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Findings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Review detected changes and investigate details before promoting actions.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Organization</CardTitle>
          <CardDescription>Select the workspace to review findings.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingOrgs ? <p className="text-sm text-muted-foreground">Loading organizations...</p> : null}
          {!isLoadingOrgs && orgs.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No organizations found. Create one from dashboard overview first.
            </p>
          ) : null}
          {!isLoadingOrgs && orgs.length > 0 ? (
            <div className="space-y-2">
              <Label htmlFor="findings-org-selector">Workspace</Label>
              <select
                id="findings-org-selector"
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
          <CardTitle>Finding Queue</CardTitle>
          <CardDescription>Filter by severity and search title, summary, or fingerprint.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-[220px_1fr]">
            <div className="space-y-2">
              <Label htmlFor="findings-severity-filter">Severity</Label>
              <select
                id="findings-severity-filter"
                value={severityFilter}
                onChange={(event) => setSeverityFilter(event.target.value as SeverityFilter)}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="all">all</option>
                <option value="critical">critical</option>
                <option value="high">high</option>
                <option value="medium">medium</option>
                <option value="low">low</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="findings-search">Search</Label>
              <Input
                id="findings-search"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Search findings..."
                maxLength={300}
              />
            </div>
          </div>

          {isLoadingFindings ? <p className="text-sm text-muted-foreground">Loading findings...</p> : null}
          {!isLoadingFindings && selectedOrgId && findings.length === 0 ? (
            <p className="text-sm text-muted-foreground">No findings yet for this workspace.</p>
          ) : null}
          {!isLoadingFindings && findings.length > 0 && filteredFindings.length === 0 ? (
            <p className="text-sm text-muted-foreground">No findings match the current filters.</p>
          ) : null}

          {!isLoadingFindings && filteredFindings.length > 0 ? (
            <ul className="space-y-2">
              {filteredFindings.map((finding) => (
                <li
                  key={finding.id}
                  className="rounded-lg border border-border/70 bg-card px-3 py-3 text-sm shadow-sm"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0 space-y-1">
                      <p className="font-medium">{finding.title}</p>
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`rounded px-2 py-1 text-xs font-medium ${severityClass(finding.severity)}`}
                        >
                          {finding.severity}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {formatTime(finding.detected_at)}
                        </span>
                      </div>
                    </div>
                    <Button type="button" size="sm" onClick={() => openDetails(finding)}>
                      Details
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </CardContent>
      </Card>

      {selectedFinding ? (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/40">
          <div className="h-full w-full max-w-xl overflow-y-auto bg-background p-4 sm:p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">
                {selectedFinding.canonical_title || "Finding Details"}
              </h2>
              <Button type="button" variant="outline" size="sm" onClick={() => setSelectedFinding(null)}>
                Close
              </Button>
            </div>

            <div className="space-y-4 rounded-lg border border-border/70 p-4">
              <div>
                <p className="text-sm text-muted-foreground">Title</p>
                <p className="font-medium">{selectedFinding.title}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Summary</p>
                <p className="text-sm">{selectedFinding.summary}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-sm text-muted-foreground">Severity</p>
                  <p className="text-sm">{selectedFinding.severity}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Detected At</p>
                  <p className="text-sm">{formatTime(selectedFinding.detected_at)}</p>
                </div>
              </div>
              {selectedFinding.item_published_at ? (
                <div>
                  <p className="text-sm text-muted-foreground">Item Published</p>
                  <p className="text-sm">{formatTime(selectedFinding.item_published_at)}</p>
                </div>
              ) : null}
              <div>
                <p className="text-sm text-muted-foreground">Raw URL</p>
                <p className="break-all text-sm">{selectedFinding.raw_url ?? "n/a"}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Fingerprint</p>
                <p className="break-all text-sm">{selectedFinding.fingerprint}</p>
              </div>
              <div className="space-y-3 border-t border-border/70 pt-3">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={isLoadingExplanation}
                  onClick={() => {
                    setShowExplanation(true);
                    if (explanation?.finding_id !== selectedFinding.id) {
                      void loadExplanation(selectedFinding.id);
                    }
                  }}
                >
                  {isLoadingExplanation ? "Loading..." : "Why this was flagged"}
                </Button>
                {showExplanation ? (
                  <div className="space-y-3 rounded-md border border-border/70 bg-background p-3">
                    {explanationError ? (
                      <p className="text-sm text-muted-foreground">{explanationError}</p>
                    ) : null}
                    {explanation && !explanationError ? (
                      <>
                        <div>
                          <p className="text-sm text-muted-foreground">Summary</p>
                          <p className="text-sm">{explanation.summary}</p>
                        </div>

                        <details className="rounded-md border border-border/60 bg-card p-2">
                          <summary className="cursor-pointer text-sm font-medium">
                            Changed snippets ({explanation.citations.length})
                          </summary>
                          <ul className="mt-2 space-y-2">
                            {explanation.citations.length === 0 ? (
                              <li className="text-xs text-muted-foreground">
                                No snippet citations were generated.
                              </li>
                            ) : (
                              explanation.citations.map((citation, index) => (
                                <li
                                  key={`${citation.quote}-${index}`}
                                  className="rounded border border-border/60 bg-background px-2 py-2"
                                >
                                  <p className="text-xs text-muted-foreground">{citation.context}</p>
                                  <p className="text-sm">{citation.quote}</p>
                                </li>
                              ))
                            )}
                          </ul>
                        </details>

                        <div>
                          <p className="text-sm text-muted-foreground">Diff preview</p>
                          <pre className="max-h-72 overflow-auto rounded-md border border-border/60 bg-card p-2 font-mono text-xs">
                            {explanation.diff_preview ?? "Diff preview unavailable for this source format."}
                          </pre>
                        </div>
                      </>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
