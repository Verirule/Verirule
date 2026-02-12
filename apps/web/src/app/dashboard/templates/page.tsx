"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type TemplateCadence = "manual" | "hourly" | "daily" | "weekly";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type TemplateRecord = {
  id: string;
  slug: string;
  name: string;
  description: string;
  default_cadence: TemplateCadence;
  tags: string[];
  source_count: number;
  created_at: string;
};

type OrgsResponse = {
  orgs: OrgRecord[];
};

type TemplatesResponse = {
  templates: TemplateRecord[];
};

type InstallResponse = {
  template_slug: string;
  installed: number;
  org_id: string;
};

export default function DashboardTemplatesPage() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [templates, setTemplates] = useState<TemplateRecord[]>([]);

  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true);
  const [installingSlug, setInstallingSlug] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const templatesBySlug = useMemo(() => {
    const map = new Map<string, TemplateRecord>();
    for (const template of templates) {
      map.set(template.slug, template);
    }
    return map;
  }, [templates]);

  const loadOrgs = async () => {
    setIsLoadingOrgs(true);
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
        setOrgs([]);
        setSelectedOrgId("");
        setError("Unable to load organizations right now.");
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
      setOrgs([]);
      setSelectedOrgId("");
      setError("Unable to load organizations right now.");
    } finally {
      setIsLoadingOrgs(false);
    }
  };

  const loadTemplates = async () => {
    setIsLoadingTemplates(true);
    try {
      const response = await fetch("/api/templates", { method: "GET", cache: "no-store" });
      const body = (await response.json().catch(() => ({}))) as Partial<TemplatesResponse> & {
        message?: unknown;
      };

      if (!response.ok || !Array.isArray(body.templates)) {
        setTemplates([]);
        setError("Unable to load templates right now.");
        return;
      }

      setTemplates(body.templates);
    } catch {
      setTemplates([]);
      setError("Unable to load templates right now.");
    } finally {
      setIsLoadingTemplates(false);
    }
  };

  useEffect(() => {
    setError(null);
    void Promise.all([loadOrgs(), loadTemplates()]);
  }, []);

  const installTemplate = async (slug: string) => {
    if (!selectedOrgId) {
      setError("Select an organization before installing a template.");
      return;
    }

    setInstallingSlug(slug);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await fetch(`/api/templates/${encodeURIComponent(slug)}/install`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ org_id: selectedOrgId }),
      });

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      const body = (await response.json().catch(() => ({}))) as Partial<InstallResponse> & {
        message?: unknown;
      };
      if (!response.ok) {
        const message = typeof body.message === "string" ? body.message : "Unable to install template right now.";
        setError(message);
        return;
      }

      const installedCount = typeof body.installed === "number" ? body.installed : 0;
      const templateName = templatesBySlug.get(slug)?.name ?? slug;
      setSuccessMessage(`Installed ${installedCount} sources from ${templateName}.`);
    } catch {
      setError("Unable to install template right now.");
    } finally {
      setInstallingSlug(null);
    }
  };

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Framework Templates</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Install vetted monitoring sources for common compliance frameworks in one click.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Organization</CardTitle>
          <CardDescription>Select the workspace where template sources will be installed.</CardDescription>
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
              <Label htmlFor="templates-org-selector">Workspace</Label>
              <select
                id="templates-org-selector"
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
          <CardTitle>Templates</CardTitle>
          <CardDescription>Global read-only framework catalog.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoadingTemplates ? <p className="text-sm text-muted-foreground">Loading templates...</p> : null}
          {!isLoadingTemplates && templates.length === 0 ? (
            <p className="text-sm text-muted-foreground">No templates are currently available.</p>
          ) : null}

          {!isLoadingTemplates && templates.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2">
              {templates.map((template) => (
                <article
                  key={template.id}
                  className="space-y-3 rounded-lg border border-border/70 bg-card p-4 shadow-sm"
                >
                  <div className="space-y-1">
                    <h2 className="text-base font-semibold">{template.name}</h2>
                    <p className="text-sm text-muted-foreground">{template.description}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {template.tags.map((tag) => (
                      <Badge key={`${template.slug}-${tag}`} variant="secondary">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    <p>Sources: {template.source_count}</p>
                    <p>Default cadence: {template.default_cadence}</p>
                  </div>
                  <Button
                    type="button"
                    onClick={() => void installTemplate(template.slug)}
                    disabled={!selectedOrgId || installingSlug === template.slug}
                  >
                    {installingSlug === template.slug ? "Installing..." : "Install"}
                  </Button>
                </article>
              ))}
            </div>
          ) : null}

          {successMessage ? (
            <p className="text-sm text-emerald-600">
              {successMessage}{" "}
              <Link href="/dashboard/sources" className="underline">
                Go to Sources
              </Link>
            </p>
          ) : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
