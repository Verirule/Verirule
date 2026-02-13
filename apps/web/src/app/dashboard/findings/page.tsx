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

type ControlConfidence = "low" | "medium" | "high";

type OrgControlCatalogRecord = {
  id: string;
  control_id: string;
  framework_slug: string;
  control_key: string;
  title: string;
  status: "not_started" | "in_progress" | "implemented" | "needs_review";
};

type FindingControlRecord = {
  id: string;
  org_id: string;
  finding_id: string;
  control_id: string;
  confidence: ControlConfidence;
  created_at: string;
  framework_slug: string;
  control_key: string;
  title: string;
  severity_default: "low" | "medium" | "high";
  tags: string[];
};

type ControlSuggestionRecord = {
  control_id: string;
  framework_slug: string;
  control_key: string;
  title: string;
  confidence: ControlConfidence;
  reasons: string[];
};

type OrgsResponse = { orgs: OrgRecord[] };
type FindingsResponse = { findings: FindingRecord[] };
type OrgControlsResponse = { controls: OrgControlCatalogRecord[] };
type FindingControlsResponse = { controls: FindingControlRecord[] };
type ControlSuggestResponse = { suggestions: ControlSuggestionRecord[] };
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
  const [orgControlsCatalog, setOrgControlsCatalog] = useState<OrgControlCatalogRecord[]>([]);
  const [mappedControls, setMappedControls] = useState<FindingControlRecord[]>([]);
  const [controlSuggestions, setControlSuggestions] = useState<ControlSuggestionRecord[]>([]);
  const [manualControlSearch, setManualControlSearch] = useState("");
  const [selectedManualControlId, setSelectedManualControlId] = useState("");
  const [linkConfidence, setLinkConfidence] = useState<ControlConfidence>("medium");
  const [isLoadingMappings, setIsLoadingMappings] = useState(false);
  const [isSuggestingControls, setIsSuggestingControls] = useState(false);
  const [isLinkingControl, setIsLinkingControl] = useState(false);
  const [mappingError, setMappingError] = useState<string | null>(null);

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

  const loadOrgControlsCatalog = async (orgId: string) => {
    if (!orgId) {
      setOrgControlsCatalog([]);
      return;
    }

    try {
      const response = await fetch(`/api/orgs/${encodeURIComponent(orgId)}/controls`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<OrgControlsResponse>;

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.controls)) {
        setOrgControlsCatalog([]);
        return;
      }

      setOrgControlsCatalog(body.controls);
    } catch {
      setOrgControlsCatalog([]);
    }
  };

  const loadMappedControls = async (findingId: string, orgId: string) => {
    if (!findingId || !orgId) {
      setMappedControls([]);
      return;
    }

    setIsLoadingMappings(true);
    setMappingError(null);
    try {
      const response = await fetch(
        `/api/findings/${encodeURIComponent(findingId)}/controls?org_id=${encodeURIComponent(orgId)}`,
        {
          method: "GET",
          cache: "no-store",
        },
      );
      const body = (await response.json().catch(() => ({}))) as Partial<FindingControlsResponse> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.controls)) {
        const message = typeof body.message === "string" ? body.message : "Unable to load mapped controls right now.";
        setMappingError(message);
        setMappedControls([]);
        return;
      }

      setMappedControls(body.controls);
    } catch {
      setMappingError("Unable to load mapped controls right now.");
      setMappedControls([]);
    } finally {
      setIsLoadingMappings(false);
    }
  };

  useEffect(() => {
    void loadOrgs();
  }, []);

  useEffect(() => {
    if (!selectedOrgId) {
      setFindings([]);
      setOrgControlsCatalog([]);
      return;
    }
    void loadFindings(selectedOrgId);
    void loadOrgControlsCatalog(selectedOrgId);
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
    setMappedControls([]);
    setControlSuggestions([]);
    setManualControlSearch("");
    setSelectedManualControlId("");
    setMappingError(null);
    if (selectedOrgId) {
      void loadMappedControls(finding.id, selectedOrgId);
    }
  };

  const suggestControls = async () => {
    if (!selectedFinding || !selectedOrgId) {
      setMappingError("Select a workspace and finding before requesting suggestions.");
      return;
    }

    setIsSuggestingControls(true);
    setMappingError(null);
    try {
      const response = await fetch(
        `/api/findings/${encodeURIComponent(selectedFinding.id)}/controls/suggest?org_id=${encodeURIComponent(selectedOrgId)}`,
        {
          method: "GET",
          cache: "no-store",
        },
      );
      const body = (await response.json().catch(() => ({}))) as Partial<ControlSuggestResponse> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.suggestions)) {
        const message = typeof body.message === "string" ? body.message : "Unable to suggest controls right now.";
        setMappingError(message);
        setControlSuggestions([]);
        return;
      }

      setControlSuggestions(body.suggestions);
    } catch {
      setMappingError("Unable to suggest controls right now.");
      setControlSuggestions([]);
    } finally {
      setIsSuggestingControls(false);
    }
  };

  const linkControl = async (controlId: string, confidence: ControlConfidence) => {
    if (!selectedFinding || !selectedOrgId || !controlId) {
      setMappingError("Select a control before linking.");
      return;
    }

    setIsLinkingControl(true);
    setMappingError(null);
    try {
      const response = await fetch(`/api/findings/${encodeURIComponent(selectedFinding.id)}/controls`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          org_id: selectedOrgId,
          control_id: controlId,
          confidence,
        }),
      });
      const body = (await response.json().catch(() => ({}))) as { message?: unknown };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        const message = typeof body.message === "string" ? body.message : "Unable to link control right now.";
        setMappingError(message);
        return;
      }

      await loadMappedControls(selectedFinding.id, selectedOrgId);
      setControlSuggestions((current) => current.filter((item) => item.control_id !== controlId));
      setSelectedManualControlId("");
    } catch {
      setMappingError("Unable to link control right now.");
    } finally {
      setIsLinkingControl(false);
    }
  };

  const availableManualControls = useMemo(() => {
    const query = manualControlSearch.trim().toLowerCase();
    const mappedIds = new Set(mappedControls.map((item) => item.control_id));
    return orgControlsCatalog
      .filter((item) => !mappedIds.has(item.control_id))
      .filter((item) => {
        if (!query) {
          return true;
        }
        return (
          item.control_key.toLowerCase().includes(query) ||
          item.title.toLowerCase().includes(query) ||
          item.framework_slug.toLowerCase().includes(query)
        );
      })
      .slice(0, 100);
  }, [manualControlSearch, mappedControls, orgControlsCatalog]);

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
                <div className="space-y-3 rounded-md border border-border/70 bg-background p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium">Mapped controls</p>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={isSuggestingControls || isLinkingControl || isLoadingMappings}
                      onClick={() => void suggestControls()}
                    >
                      {isSuggestingControls ? "Suggesting..." : "Suggest controls"}
                    </Button>
                  </div>

                  {isLoadingMappings ? <p className="text-sm text-muted-foreground">Loading mapped controls...</p> : null}
                  {!isLoadingMappings && mappedControls.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No controls are linked to this finding.</p>
                  ) : null}
                  {!isLoadingMappings && mappedControls.length > 0 ? (
                    <ul className="space-y-2">
                      {mappedControls.map((control) => (
                        <li key={control.id} className="rounded border border-border/60 bg-card px-2 py-2">
                          <p className="text-sm font-medium">
                            {control.control_key} - {control.title}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {control.framework_slug} | confidence {control.confidence}
                          </p>
                        </li>
                      ))}
                    </ul>
                  ) : null}

                  {controlSuggestions.length > 0 ? (
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">Suggested controls</p>
                      <ul className="space-y-2">
                        {controlSuggestions.map((suggestion) => (
                          <li key={suggestion.control_id} className="rounded border border-border/60 bg-card px-2 py-2">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div>
                                <p className="text-sm font-medium">
                                  {suggestion.control_key} - {suggestion.title}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                  {suggestion.framework_slug} | confidence {suggestion.confidence}
                                </p>
                              </div>
                              <Button
                                type="button"
                                size="sm"
                                disabled={isLinkingControl}
                                onClick={() => void linkControl(suggestion.control_id, suggestion.confidence)}
                              >
                                Link
                              </Button>
                            </div>
                            {suggestion.reasons.length > 0 ? (
                              <p className="mt-1 text-xs text-muted-foreground">{suggestion.reasons.join(" | ")}</p>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  <div className="space-y-2 rounded-md border border-border/60 bg-card p-2">
                    <p className="text-sm text-muted-foreground">Manual link</p>
                    <Input
                      value={manualControlSearch}
                      onChange={(event) => setManualControlSearch(event.target.value)}
                      placeholder="Search control key, title, or framework"
                      maxLength={160}
                    />
                    <select
                      value={selectedManualControlId}
                      onChange={(event) => setSelectedManualControlId(event.target.value)}
                      className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    >
                      <option value="">Select control</option>
                      {availableManualControls.map((control) => (
                        <option key={control.id} value={control.control_id}>
                          {control.control_key} - {control.title}
                        </option>
                      ))}
                    </select>
                    <div className="grid gap-2 sm:grid-cols-[160px_1fr]">
                      <select
                        value={linkConfidence}
                        onChange={(event) => setLinkConfidence(event.target.value as ControlConfidence)}
                        className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                      >
                        <option value="low">Low confidence</option>
                        <option value="medium">Medium confidence</option>
                        <option value="high">High confidence</option>
                      </select>
                      <Button
                        type="button"
                        disabled={!selectedManualControlId || isLinkingControl}
                        onClick={() => void linkControl(selectedManualControlId, linkConfidence)}
                      >
                        {isLinkingControl ? "Linking..." : "Link selected control"}
                      </Button>
                    </div>
                  </div>

                  {mappingError ? <p className="text-sm text-destructive">{mappingError}</p> : null}
                </div>

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
