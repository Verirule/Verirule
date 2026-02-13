"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePlan } from "@/src/components/billing/usePlan";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

type IntegrationType = "slack" | "jira";
type IntegrationStatus = "connected" | "disabled";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type IntegrationRecord = {
  id: string;
  org_id: string;
  type: IntegrationType;
  status: IntegrationStatus;
  config: Record<string, unknown>;
  updated_at: string;
};

type OrgsResponse = { orgs: OrgRecord[] };
type IntegrationsResponse = { integrations: IntegrationRecord[] };

function statusClass(status: IntegrationStatus | "not_connected"): string {
  if (status === "connected") {
    return "bg-emerald-100 text-emerald-800";
  }
  if (status === "disabled") {
    return "bg-amber-100 text-amber-800";
  }
  return "bg-slate-100 text-slate-700";
}

export default function DashboardIntegrationsPage() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [integrations, setIntegrations] = useState<IntegrationRecord[]>([]);

  const [slackWebhookUrl, setSlackWebhookUrl] = useState("");
  const [jiraBaseUrl, setJiraBaseUrl] = useState("");
  const [jiraEmail, setJiraEmail] = useState("");
  const [jiraApiToken, setJiraApiToken] = useState("");
  const [jiraProjectKey, setJiraProjectKey] = useState("");

  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingIntegrations, setIsLoadingIntegrations] = useState(false);
  const [isConnectingSlack, setIsConnectingSlack] = useState(false);
  const [isTestingSlack, setIsTestingSlack] = useState(false);
  const [isConnectingJira, setIsConnectingJira] = useState(false);
  const [isTestingJira, setIsTestingJira] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const slackIntegration = useMemo(
    () => integrations.find((integration) => integration.type === "slack") ?? null,
    [integrations],
  );
  const jiraIntegration = useMemo(
    () => integrations.find((integration) => integration.type === "jira") ?? null,
    [integrations],
  );
  const { features: planFeatures } = usePlan(selectedOrgId);

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
  }, []);

  const loadIntegrations = useCallback(async (orgId: string) => {
    if (!orgId) {
      setIntegrations([]);
      return;
    }
    setIsLoadingIntegrations(true);
    setError(null);

    try {
      const response = await fetch(`/api/integrations?org_id=${encodeURIComponent(orgId)}`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<IntegrationsResponse> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.integrations)) {
        setError(typeof body.message === "string" ? body.message : "Unable to load integrations.");
        setIntegrations([]);
        return;
      }

      const rows = body.integrations;
      setIntegrations(rows);

      const jira = rows.find((integration) => integration.type === "jira");
      const jiraConfig = jira?.config ?? {};
      const baseUrl = typeof jiraConfig.base_url === "string" ? jiraConfig.base_url : "";
      const projectKey = typeof jiraConfig.project_key === "string" ? jiraConfig.project_key : "";
      if (baseUrl) {
        setJiraBaseUrl(baseUrl);
      }
      if (projectKey) {
        setJiraProjectKey(projectKey);
      }
    } catch {
      setError("Unable to load integrations.");
      setIntegrations([]);
    } finally {
      setIsLoadingIntegrations(false);
    }
  }, []);

  useEffect(() => {
    void loadOrgs();
  }, [loadOrgs]);

  useEffect(() => {
    if (!selectedOrgId) {
      setIntegrations([]);
      return;
    }
    if (!planFeatures.canUseIntegrations) {
      setIntegrations([]);
      return;
    }
    void loadIntegrations(selectedOrgId);
  }, [selectedOrgId, planFeatures.canUseIntegrations, loadIntegrations]);

  const connectSlack = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!planFeatures.canUseIntegrations) {
      setError("Upgrade to Pro to enable integrations.");
      return;
    }

    if (!selectedOrgId || !slackWebhookUrl.trim()) {
      setError("Slack webhook URL is required.");
      return;
    }

    setIsConnectingSlack(true);
    try {
      const response = await fetch("/api/integrations/slack/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ org_id: selectedOrgId, webhook_url: slackWebhookUrl.trim() }),
      });
      const body = (await response.json().catch(() => ({}))) as { message?: unknown };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }
      if (!response.ok) {
        setError(typeof body.message === "string" ? body.message : "Unable to connect Slack.");
        return;
      }

      setSlackWebhookUrl("");
      setSuccess("Slack connected.");
      await loadIntegrations(selectedOrgId);
    } catch {
      setError("Unable to connect Slack.");
    } finally {
      setIsConnectingSlack(false);
    }
  };

  const connectJira = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!planFeatures.canUseIntegrations) {
      setError("Upgrade to Pro to enable integrations.");
      return;
    }

    if (!selectedOrgId || !jiraBaseUrl.trim() || !jiraEmail.trim() || !jiraApiToken.trim() || !jiraProjectKey.trim()) {
      setError("Jira base URL, email, API token, and project key are required.");
      return;
    }

    setIsConnectingJira(true);
    try {
      const response = await fetch("/api/integrations/jira/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          org_id: selectedOrgId,
          base_url: jiraBaseUrl.trim(),
          email: jiraEmail.trim(),
          api_token: jiraApiToken.trim(),
          project_key: jiraProjectKey.trim(),
        }),
      });
      const body = (await response.json().catch(() => ({}))) as { message?: unknown };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }
      if (!response.ok) {
        setError(typeof body.message === "string" ? body.message : "Unable to connect Jira.");
        return;
      }

      setJiraApiToken("");
      setSuccess("Jira connected.");
      await loadIntegrations(selectedOrgId);
    } catch {
      setError("Unable to connect Jira.");
    } finally {
      setIsConnectingJira(false);
    }
  };

  const testSlack = async () => {
    setError(null);
    setSuccess(null);

    if (!planFeatures.canUseIntegrations) {
      setError("Upgrade to Pro to enable integrations.");
      return;
    }

    if (!selectedOrgId) {
      setError("Select an organization first.");
      return;
    }

    setIsTestingSlack(true);
    try {
      const response = await fetch("/api/integrations/slack/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ org_id: selectedOrgId }),
      });
      const body = (await response.json().catch(() => ({}))) as { message?: unknown };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }
      if (!response.ok) {
        setError(typeof body.message === "string" ? body.message : "Slack test failed.");
        return;
      }
      setSuccess("Slack test message sent.");
    } catch {
      setError("Slack test failed.");
    } finally {
      setIsTestingSlack(false);
    }
  };

  const testJira = async () => {
    setError(null);
    setSuccess(null);

    if (!planFeatures.canUseIntegrations) {
      setError("Upgrade to Pro to enable integrations.");
      return;
    }

    if (!selectedOrgId) {
      setError("Select an organization first.");
      return;
    }

    setIsTestingJira(true);
    try {
      const response = await fetch("/api/integrations/jira/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ org_id: selectedOrgId }),
      });
      const body = (await response.json().catch(() => ({}))) as { message?: unknown };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }
      if (!response.ok) {
        setError(typeof body.message === "string" ? body.message : "Jira test failed.");
        return;
      }
      setSuccess("Jira test succeeded.");
    } catch {
      setError("Jira test failed.");
    } finally {
      setIsTestingJira(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Integrations</h1>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/settings">Back to settings</Link>
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          Configure Slack and Jira per workspace. Secrets are encrypted server-side and never returned.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Workspace</CardTitle>
          <CardDescription>Choose org scope for integrations.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingOrgs ? <p className="text-sm text-muted-foreground">Loading organizations...</p> : null}
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

      {!planFeatures.canUseIntegrations && selectedOrgId ? (
        <Card className="border-border/70">
          <CardHeader>
            <CardTitle>Upgrade Required</CardTitle>
            <CardDescription>Integrations are available on Pro and Business plans.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild size="sm">
              <Link href="/dashboard/billing">Upgrade plan</Link>
            </Button>
          </CardContent>
        </Card>
      ) : null}

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Slack</CardTitle>
          <CardDescription>Incoming webhook for alert notifications.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-medium">Status:</span>
            <span
              className={`rounded px-2 py-1 text-xs font-medium ${statusClass(
                slackIntegration?.status ?? "not_connected",
              )}`}
            >
              {slackIntegration?.status ?? "not_connected"}
            </span>
            {isLoadingIntegrations ? <span className="text-muted-foreground">Refreshing...</span> : null}
          </div>

          <form onSubmit={connectSlack} className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="slack-webhook-url">Webhook URL</Label>
              <Input
                id="slack-webhook-url"
                type="password"
                value={slackWebhookUrl}
                onChange={(event) => setSlackWebhookUrl(event.target.value)}
                placeholder="https://hooks.slack.com/services/..."
                autoComplete="off"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="submit"
                disabled={isConnectingSlack || !selectedOrgId || !planFeatures.canUseIntegrations}
                title={!planFeatures.canUseIntegrations ? "Upgrade to Pro to enable integrations." : undefined}
              >
                {isConnectingSlack ? "Connecting..." : "Connect"}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={
                  isTestingSlack ||
                  !selectedOrgId ||
                  slackIntegration?.status !== "connected" ||
                  !planFeatures.canUseIntegrations
                }
                title={!planFeatures.canUseIntegrations ? "Upgrade to Pro to enable integrations." : undefined}
                onClick={testSlack}
              >
                {isTestingSlack ? "Testing..." : "Test"}
              </Button>
            </div>
            {!planFeatures.canUseIntegrations ? (
              <p className="text-xs text-muted-foreground">Upgrade to Pro to enable integrations.</p>
            ) : null}
          </form>
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Jira</CardTitle>
          <CardDescription>Atlassian Cloud issue creation integration.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-medium">Status:</span>
            <span
              className={`rounded px-2 py-1 text-xs font-medium ${statusClass(
                jiraIntegration?.status ?? "not_connected",
              )}`}
            >
              {jiraIntegration?.status ?? "not_connected"}
            </span>
            {isLoadingIntegrations ? <span className="text-muted-foreground">Refreshing...</span> : null}
          </div>

          <form onSubmit={connectJira} className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="jira-base-url">Base URL</Label>
              <Input
                id="jira-base-url"
                value={jiraBaseUrl}
                onChange={(event) => setJiraBaseUrl(event.target.value)}
                placeholder="https://yourdomain.atlassian.net"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="jira-email">Email</Label>
              <Input
                id="jira-email"
                value={jiraEmail}
                onChange={(event) => setJiraEmail(event.target.value)}
                placeholder="you@company.com"
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="jira-api-token">API Token</Label>
              <Input
                id="jira-api-token"
                type="password"
                value={jiraApiToken}
                onChange={(event) => setJiraApiToken(event.target.value)}
                placeholder="Atlassian API token"
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="jira-project-key">Project Key</Label>
              <Input
                id="jira-project-key"
                value={jiraProjectKey}
                onChange={(event) => setJiraProjectKey(event.target.value)}
                placeholder="SEC"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="submit"
                disabled={isConnectingJira || !selectedOrgId || !planFeatures.canUseIntegrations}
                title={!planFeatures.canUseIntegrations ? "Upgrade to Pro to enable integrations." : undefined}
              >
                {isConnectingJira ? "Connecting..." : "Connect"}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={
                  isTestingJira ||
                  !selectedOrgId ||
                  jiraIntegration?.status !== "connected" ||
                  !planFeatures.canUseIntegrations
                }
                title={!planFeatures.canUseIntegrations ? "Upgrade to Pro to enable integrations." : undefined}
                onClick={testJira}
              >
                {isTestingJira ? "Testing..." : "Test"}
              </Button>
            </div>
            {!planFeatures.canUseIntegrations ? (
              <p className="text-xs text-muted-foreground">Upgrade to Pro to enable integrations.</p>
            ) : null}
          </form>
        </CardContent>
      </Card>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {success ? <p className="text-sm text-emerald-700">{success}</p> : null}
    </div>
  );
}
