"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type TemplateCadence = "manual" | "hourly" | "daily" | "weekly";
type TemplateSourceKind = "web" | "rss" | "atom";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type TemplateSourceRecord = {
  id: string;
  template_id: string;
  title: string;
  url: string;
  kind: TemplateSourceKind;
  cadence: TemplateCadence;
  tags: string[];
  enabled_by_default: boolean;
  created_at: string;
};

type TemplateRecord = {
  id: string;
  slug: string;
  name: string;
  description: string;
  category: string;
  is_public: boolean;
  created_at: string;
  sources: TemplateSourceRecord[];
};

type OrgsResponse = { orgs: OrgRecord[] };
type TemplatesResponse = { templates: TemplateRecord[] };
type TemplateApplyResponse = {
  created: number;
  skipped: number;
  sources: Array<{
    id: string;
    name: string;
    title: string | null;
    url: string;
    kind: string;
    cadence: TemplateCadence;
    is_enabled: boolean;
    tags: string[];
  }>;
  metadata: Record<string, unknown>;
};

function hostFromUrl(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return "Invalid URL";
  }
}

function kindLabel(kind: TemplateSourceKind): string {
  if (kind === "rss") return "RSS";
  if (kind === "atom") return "Atom";
  return "Web";
}

function cadenceNote(sources: TemplateSourceRecord[]): string {
  if (sources.some((source) => source.cadence === "hourly")) {
    return "Includes hourly sources.";
  }
  if (sources.some((source) => source.cadence === "daily")) {
    return "Includes daily sources.";
  }
  if (sources.some((source) => source.cadence === "weekly")) {
    return "Primarily weekly sources.";
  }
  return "Manual cadence only.";
}

export default function DashboardTemplatesPage() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [templates, setTemplates] = useState<TemplateRecord[]>([]);
  const [selectedTemplateSlug, setSelectedTemplateSlug] = useState<string | null>(null);

  const [overrideCadence, setOverrideCadence] = useState<"" | TemplateCadence>("");
  const [enableAllOverride, setEnableAllOverride] = useState(false);

  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true);
  const [applyingSlug, setApplyingSlug] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [lastAppliedTemplateSlug, setLastAppliedTemplateSlug] = useState<string | null>(null);
  const [isInstallingControls, setIsInstallingControls] = useState(false);
  const [controlsInstallMessage, setControlsInstallMessage] = useState<string | null>(null);

  const selectedTemplate = useMemo(() => {
    if (!selectedTemplateSlug) {
      return null;
    }
    return templates.find((item) => item.slug === selectedTemplateSlug) ?? null;
  }, [selectedTemplateSlug, templates]);

  const loadOrgs = async () => {
    setIsLoadingOrgs(true);
    setError(null);

    try {
      const response = await fetch("/api/orgs", { method: "GET", cache: "no-store" });
      const body = (await response.json().catch(() => ({}))) as Partial<OrgsResponse> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.orgs)) {
        setError("Unable to load workspaces right now.");
        setOrgs([]);
        setSelectedOrgId("");
        return;
      }

      setOrgs(body.orgs);
      setSelectedOrgId((current) => {
        if (current && body.orgs?.some((org) => org.id === current)) {
          return current;
        }
        return body.orgs?.[0]?.id ?? "";
      });
    } catch {
      setError("Unable to load workspaces right now.");
      setOrgs([]);
      setSelectedOrgId("");
    } finally {
      setIsLoadingOrgs(false);
    }
  };

  const loadTemplates = async () => {
    setIsLoadingTemplates(true);
    setError(null);

    try {
      const response = await fetch("/api/templates", { method: "GET", cache: "no-store" });
      const body = (await response.json().catch(() => ({}))) as Partial<TemplatesResponse> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.templates)) {
        setError("Unable to load template catalog right now.");
        setTemplates([]);
        return;
      }

      setTemplates(body.templates);
    } catch {
      setError("Unable to load template catalog right now.");
      setTemplates([]);
    } finally {
      setIsLoadingTemplates(false);
    }
  };

  useEffect(() => {
    void loadOrgs();
    void loadTemplates();
  }, []);

  const applyTemplate = async (slug: string) => {
    if (!selectedOrgId) {
      setError("Select a workspace before applying a template.");
      return;
    }

    setApplyingSlug(slug);
    setError(null);
    setSuccessMessage(null);
    setControlsInstallMessage(null);

    const overrides: { cadence?: TemplateCadence; enable_all?: boolean } = {};
    if (overrideCadence) {
      overrides.cadence = overrideCadence;
    }
    if (enableAllOverride) {
      overrides.enable_all = true;
    }

    try {
      const response = await fetch("/api/templates/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          org_id: selectedOrgId,
          template_slug: slug,
          overrides: Object.keys(overrides).length > 0 ? overrides : undefined,
        }),
      });

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      const body = (await response.json().catch(() => ({}))) as Partial<TemplateApplyResponse> & {
        message?: unknown;
      };

      if (!response.ok) {
        const message = typeof body.message === "string" ? body.message : "Unable to apply template right now.";
        setError(message);
        return;
      }

      const created = typeof body.created === "number" ? body.created : 0;
      const skipped = typeof body.skipped === "number" ? body.skipped : 0;
      const templateName = templates.find((item) => item.slug === slug)?.name ?? slug;
      setSuccessMessage(`${templateName} applied. ${created} source(s) created, ${skipped} skipped.`);
      setLastAppliedTemplateSlug(slug);
    } catch {
      setError("Unable to apply template right now.");
    } finally {
      setApplyingSlug(null);
    }
  };

  const installRecommendedControls = async () => {
    if (!selectedOrgId || !lastAppliedTemplateSlug) {
      setError("Apply a template before installing controls.");
      return;
    }

    setIsInstallingControls(true);
    setError(null);
    setControlsInstallMessage(null);

    try {
      const response = await fetch(
        `/api/orgs/${encodeURIComponent(selectedOrgId)}/controls/install-from-template`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ template_slug: lastAppliedTemplateSlug }),
        },
      );
      const body = (await response.json().catch(() => ({}))) as {
        installed?: unknown;
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        const message =
          typeof body.message === "string"
            ? body.message
            : "Unable to install recommended controls right now.";
        setError(message);
        return;
      }

      const installed = typeof body.installed === "number" ? body.installed : 0;
      setControlsInstallMessage(`${installed} control(s) installed for this workspace.`);
    } catch {
      setError("Unable to install recommended controls right now.");
    } finally {
      setIsInstallingControls(false);
    }
  };

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Framework Templates</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Standardized source sets for regulatory and control framework monitoring.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Workspace</CardTitle>
          <CardDescription>Choose the organization where template sources will be provisioned.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoadingOrgs ? <p className="text-sm text-muted-foreground">Loading workspaces...</p> : null}
          {!isLoadingOrgs && orgs.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No workspace found. Create a workspace before applying a framework template.
            </p>
          ) : null}
          {!isLoadingOrgs && orgs.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-[1fr_220px_220px]">
              <div className="space-y-2">
                <Label htmlFor="template-workspace">Workspace</Label>
                <select
                  id="template-workspace"
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
              <div className="space-y-2">
                <Label htmlFor="template-cadence-override">Cadence Override</Label>
                <select
                  id="template-cadence-override"
                  value={overrideCadence}
                  onChange={(event) => setOverrideCadence(event.target.value as "" | TemplateCadence)}
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="">Use template cadence</option>
                  <option value="manual">Manual</option>
                  <option value="hourly">Hourly</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="template-enable-all">Activation</Label>
                <div className="flex h-10 items-center gap-2 rounded-md border border-input px-3">
                  <Checkbox
                    id="template-enable-all"
                    checked={enableAllOverride}
                    onCheckedChange={(checked) => setEnableAllOverride(Boolean(checked))}
                  />
                  <Label htmlFor="template-enable-all" className="cursor-pointer text-sm font-normal">
                    Enable all on apply
                  </Label>
                </div>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Catalog</CardTitle>
          <CardDescription>Review framework-specific monitoring sources before applying.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoadingTemplates ? <p className="text-sm text-muted-foreground">Loading template catalog...</p> : null}
          {!isLoadingTemplates && templates.length === 0 ? (
            <p className="text-sm text-muted-foreground">No framework templates are currently available.</p>
          ) : null}

          {!isLoadingTemplates && templates.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {templates.map((template) => (
                <article key={template.id} className="rounded-lg border border-border/70 bg-card p-4 shadow-sm">
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <h2 className="text-base font-semibold leading-tight">{template.name}</h2>
                      <Badge variant="secondary" className="whitespace-nowrap text-xs">
                        {template.category}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{template.description}</p>
                    <div className="text-xs text-muted-foreground">
                      <p>{template.sources.length} source(s)</p>
                      <p>{cadenceNote(template.sources)}</p>
                    </div>
                  </div>
                  <div className="mt-4 flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedTemplateSlug(template.slug)}
                    >
                      Review Sources
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      disabled={!selectedOrgId || applyingSlug === template.slug}
                      onClick={() => void applyTemplate(template.slug)}
                    >
                      {applyingSlug === template.slug ? "Applying..." : "Apply Template"}
                    </Button>
                  </div>
                </article>
              ))}
            </div>
          ) : null}

          {successMessage ? (
            <div className="space-y-2">
              <p className="text-sm text-emerald-700">
                {successMessage} <Link href="/dashboard/sources" className="underline">View sources</Link>
              </p>
              {lastAppliedTemplateSlug ? (
                <div className="rounded-md border border-border/70 bg-card p-3">
                  <p className="text-sm">Install recommended controls for this template.</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <Button type="button" size="sm" onClick={() => void installRecommendedControls()} disabled={isInstallingControls}>
                      {isInstallingControls ? "Installing..." : "Install controls"}
                    </Button>
                    <Link href="/dashboard/controls" className="text-xs underline">
                      Open controls dashboard
                    </Link>
                  </div>
                  {controlsInstallMessage ? (
                    <p className="mt-2 text-xs text-emerald-700">{controlsInstallMessage}</p>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </CardContent>
      </Card>

      {selectedTemplate ? (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/40">
          <div className="h-full w-full max-w-2xl overflow-y-auto bg-background p-4 sm:p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">{selectedTemplate.name}</h2>
                <p className="text-sm text-muted-foreground">{selectedTemplate.category}</p>
              </div>
              <Button type="button" variant="outline" size="sm" onClick={() => setSelectedTemplateSlug(null)}>
                Close
              </Button>
            </div>

            <div className="space-y-4 rounded-lg border border-border/70 p-4">
              <p className="text-sm text-muted-foreground">{selectedTemplate.description}</p>
              <ul className="space-y-2">
                {selectedTemplate.sources.map((source) => (
                  <li key={source.id} className="rounded-md border border-border/60 bg-card p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-medium">{source.title}</p>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs">
                          {kindLabel(source.kind)}
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          {source.cadence}
                        </Badge>
                      </div>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{hostFromUrl(source.url)}</p>
                    <p className="mt-1 break-all text-xs text-muted-foreground">{source.url}</p>
                    {source.tags.length > 0 ? (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {source.tags.map((tag) => (
                          <Badge key={`${source.id}-${tag}`} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
              <div className="flex justify-end">
                <Button
                  type="button"
                  disabled={!selectedOrgId || applyingSlug === selectedTemplate.slug}
                  onClick={() => void applyTemplate(selectedTemplate.slug)}
                >
                  {applyingSlug === selectedTemplate.slug ? "Applying..." : "Apply Template"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
