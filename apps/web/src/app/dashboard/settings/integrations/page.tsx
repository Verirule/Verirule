"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

type IntegrationStatus = "enabled" | "disabled";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type IntegrationRecord = {
  id: string;
  org_id: string;
  type: "slack" | "jira" | "github";
  status: IntegrationStatus;
  has_secret: boolean;
  created_at: string;
  updated_at: string;
};

type OrgsResponse = { orgs: OrgRecord[] };
type IntegrationsResponse = { integrations: IntegrationRecord[] };

function formatTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown time";
  }
  return parsed.toLocaleString();
}

export default function DashboardIntegrationsPage() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [integrations, setIntegrations] = useState<IntegrationRecord[]>([]);

  const [slackWebhookUrl, setSlackWebhookUrl] = useState("");
  const [slackStatus, setSlackStatus] = useState<IntegrationStatus>("enabled");
  const [testMessage, setTestMessage] = useState("Verirule Slack integration test.");

  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingIntegrations, setIsLoadingIntegrations] = useState(false);
  const [isSavingSlack, setIsSavingSlack] = useState(false);
  const [isTestingSlack, setIsTestingSlack] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const slackIntegration = useMemo(
    () => integrations.find((integration) => integration.type === "slack") ?? null,
    [integrations],
  );

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

      setOrgs(body.orgs);
      setSelectedOrgId((current) => {
        if (current && body.orgs.some((org) => org.id === current)) {
          return current;
        }
        return body.orgs[0]?.id ?? "";
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
    setSuccess(null);

    try {
      const response = await fetch(`/api/integrations?org_id=${encodeURIComponent(orgId)}`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<IntegrationsResponse>;

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.integrations)) {
        setError("Unable to load integrations right now.");
        setIntegrations([]);
        return;
      }

      setIntegrations(body.integrations);
      const slack = body.integrations.find((integration) => integration.type === "slack");
      if (slack) {
        setSlackStatus(slack.status);
      }
    } catch {
      setError("Unable to load integrations right now.");
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
    void loadIntegrations(selectedOrgId);
  }, [selectedOrgId, loadIntegrations]);

  const connectSlack = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!selectedOrgId) {
      setError("Select an organization first.");
      return;
    }
    if (!slackWebhookUrl.trim()) {
      setError("Slack webhook URL is required.");
      return;
    }

    setIsSavingSlack(true);
    try {
      const response = await fetch("/api/integrations/slack", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          org_id: selectedOrgId,
          webhook_url: slackWebhookUrl.trim(),
          status: slackStatus,
        }),
      });
      const body = (await response.json().catch(() => ({}))) as { message?: unknown };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        setError(
          typeof body.message === "string" ? body.message : "Unable to save Slack integration.",
        );
        return;
      }

      setSlackWebhookUrl("");
      setSuccess("Slack integration saved securely.");
      await loadIntegrations(selectedOrgId);
    } catch {
      setError("Unable to save Slack integration.");
    } finally {
      setIsSavingSlack(false);
    }
  };

  const sendSlackTest = async () => {
    setError(null);
    setSuccess(null);

    if (!selectedOrgId) {
      setError("Select an organization first.");
      return;
    }

    setIsTestingSlack(true);
    try {
      const response = await fetch("/api/integrations/slack/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          org_id: selectedOrgId,
          message: testMessage.trim() || null,
        }),
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
          Configure pluggable alert routing connectors. Secrets are write-only and never returned to the client.
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

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Slack</CardTitle>
          <CardDescription>Configure incoming webhook for alert notifications.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoadingIntegrations ? (
            <p className="text-sm text-muted-foreground">Loading integrations...</p>
          ) : (
            <div className="rounded-lg border border-border/70 bg-card p-3 text-sm">
              <p>
                <span className="font-medium">Current status:</span> {slackIntegration?.status ?? "not configured"}
              </p>
              <p className="text-muted-foreground">
                Secret configured: {slackIntegration?.has_secret ? "yes" : "no"}
              </p>
              {slackIntegration ? (
                <p className="text-xs text-muted-foreground">
                  Updated at {formatTime(slackIntegration.updated_at)}
                </p>
              ) : null}
            </div>
          )}

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
            <div className="space-y-2">
              <Label htmlFor="slack-status">Status</Label>
              <select
                id="slack-status"
                value={slackStatus}
                onChange={(event) => setSlackStatus(event.target.value as IntegrationStatus)}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="enabled">enabled</option>
                <option value="disabled">disabled</option>
              </select>
            </div>
            <Button type="submit" disabled={isSavingSlack || !selectedOrgId}>
              {isSavingSlack ? "Saving..." : "Save Slack Integration"}
            </Button>
          </form>

          <div className="space-y-2 border-t border-border/70 pt-4">
            <Label htmlFor="slack-test-message">Test message</Label>
            <Input
              id="slack-test-message"
              value={testMessage}
              onChange={(event) => setTestMessage(event.target.value)}
              placeholder="Verirule Slack integration test."
            />
            <Button type="button" variant="outline" disabled={isTestingSlack || !selectedOrgId} onClick={sendSlackTest}>
              {isTestingSlack ? "Sending..." : "Send Test Message"}
            </Button>
          </div>

          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {success ? <p className="text-sm text-green-700">{success}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}
