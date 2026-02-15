"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { usePlan } from "@/src/components/billing/usePlan";
import { getPlanDisplayPrice, getPlanIncludedItems, type BillingPlan } from "@/src/lib/billing";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type BillingEventRecord = {
  id: string;
  org_id: string;
  stripe_event_id: string;
  event_type: string;
  created_at: string;
  processed_at: string | null;
  status: "received" | "processed" | "failed";
  error: string | null;
};

type OrgsResponse = { orgs: OrgRecord[] };
type BillingEventsResponse = { events: BillingEventRecord[] };
type PlanCard = { plan: BillingPlan; label: string };

const PLAN_CARDS: PlanCard[] = [
  { plan: "free", label: "Free" },
  { plan: "pro", label: "Pro" },
  { plan: "business", label: "Business" },
];

function planBadgeClass(plan: BillingPlan): string {
  if (plan === "business") {
    return "bg-emerald-100 text-emerald-800";
  }
  if (plan === "pro") {
    return "bg-blue-100 text-blue-800";
  }
  return "bg-slate-100 text-slate-700";
}

function statusBadgeClass(status: string): string {
  if (status === "active") return "bg-emerald-100 text-emerald-800";
  if (status === "trialing") return "bg-blue-100 text-blue-800";
  if (status === "past_due") return "bg-amber-100 text-amber-800";
  return "bg-red-100 text-red-800";
}

function eventStatusClass(status: BillingEventRecord["status"]): string {
  if (status === "processed") return "bg-emerald-100 text-emerald-800";
  if (status === "failed") return "bg-red-100 text-red-800";
  return "bg-slate-100 text-slate-700";
}

function formatDate(value: string | null): string {
  if (!value) return "N/A";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "N/A";
  return parsed.toLocaleDateString();
}

function formatDateTime(value: string | null): string {
  if (!value) return "N/A";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "N/A";
  return parsed.toLocaleString();
}

export default function DashboardBillingPage() {
  const searchParams = useSearchParams();
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [events, setEvents] = useState<BillingEventRecord[]>([]);
  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);
  const [isCheckoutLoading, setIsCheckoutLoading] = useState<null | BillingPlan>(null);
  const [isPortalLoading, setIsPortalLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { plan, status, currentPeriodEnd, features, loading, error: planError, refresh } = usePlan(selectedOrgId);

  const successMessage = searchParams.get("success") === "1" ? "Checkout complete." : null;
  const canceledMessage = searchParams.get("canceled") === "1" ? "Checkout canceled." : null;
  const featureBadges = useMemo(
    () => [
      { label: "Integrations", enabled: features.canUseIntegrations },
      { label: "Exports", enabled: features.canUseExports },
      { label: "Scheduling", enabled: features.canUseScheduledRuns },
    ],
    [features.canUseIntegrations, features.canUseExports, features.canUseScheduledRuns],
  );
  const planCards = useMemo(
    () =>
      PLAN_CARDS.map((item) => ({
        ...item,
        displayPrice: getPlanDisplayPrice(item.plan),
        included: getPlanIncludedItems(item.plan),
      })),
    [],
  );

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

  const loadEvents = async (orgId: string) => {
    if (!orgId) {
      setEvents([]);
      return;
    }

    setIsLoadingEvents(true);
    setError(null);
    try {
      const response = await fetch(
        `/api/billing/events?org_id=${encodeURIComponent(orgId)}&limit=25`,
        { method: "GET", cache: "no-store" },
      );
      const body = (await response.json().catch(() => ({}))) as Partial<BillingEventsResponse> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.events)) {
        const message = typeof body.message === "string" ? body.message : "Unable to load billing events.";
        setError(message);
        setEvents([]);
        return;
      }

      setEvents(body.events);
    } catch {
      setError("Unable to load billing events.");
      setEvents([]);
    } finally {
      setIsLoadingEvents(false);
    }
  };

  useEffect(() => {
    void loadOrgs();
  }, []);

  useEffect(() => {
    if (!selectedOrgId) {
      setEvents([]);
      return;
    }
    void loadEvents(selectedOrgId);
  }, [selectedOrgId]);

  useEffect(() => {
    if (!selectedOrgId) return;
    const interval = window.setInterval(() => {
      void loadEvents(selectedOrgId);
    }, 20000);
    return () => window.clearInterval(interval);
  }, [selectedOrgId]);

  const startCheckout = async (targetPlan: Exclude<BillingPlan, "free">) => {
    if (!selectedOrgId) {
      setError("Select a workspace first.");
      return;
    }

    setError(null);
    setIsCheckoutLoading(targetPlan);
    try {
      const response = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ org_id: selectedOrgId, plan: targetPlan }),
      });
      const body = (await response.json().catch(() => ({}))) as { url?: unknown; message?: unknown };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || typeof body.url !== "string") {
        setError(typeof body.message === "string" ? body.message : "Unable to start checkout.");
        return;
      }

      window.location.href = body.url;
    } catch {
      setError("Unable to start checkout.");
    } finally {
      setIsCheckoutLoading(null);
    }
  };

  const openPortal = async () => {
    if (!selectedOrgId) {
      setError("Select a workspace first.");
      return;
    }

    setError(null);
    setIsPortalLoading(true);
    try {
      const response = await fetch("/api/billing/portal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ org_id: selectedOrgId }),
      });
      const body = (await response.json().catch(() => ({}))) as { url?: unknown; message?: unknown };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || typeof body.url !== "string") {
        setError(typeof body.message === "string" ? body.message : "Unable to open billing portal.");
        return;
      }

      window.location.href = body.url;
    } catch {
      setError("Unable to open billing portal.");
    } finally {
      setIsPortalLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Billing</h1>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/settings">Back to settings</Link>
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          Stripe plan status and entitlements for each workspace.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Workspace</CardTitle>
          <CardDescription>Select the workspace to view billing status and events.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingOrgs ? <p className="text-sm text-muted-foreground">Loading organizations...</p> : null}
          {!isLoadingOrgs && orgs.length > 0 ? (
            <div className="space-y-2">
              <Label htmlFor="billing-org-selector">Workspace</Label>
              <select
                id="billing-org-selector"
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
          <CardTitle>Current Plan</CardTitle>
          <CardDescription>Server-validated entitlements from FastAPI billing endpoints.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded px-2 py-1 text-xs font-medium ${planBadgeClass(plan)}`}>{plan}</span>
            <span className={`rounded px-2 py-1 text-xs font-medium ${statusBadgeClass(status)}`}>{status}</span>
            {loading ? <span className="text-muted-foreground">Refreshing...</span> : null}
          </div>
          <p>
            <span className="font-medium">Renewal date:</span> {formatDate(currentPeriodEnd)}
          </p>
          <div className="flex flex-wrap gap-2">
            {featureBadges.map((feature) => (
              <span
                key={feature.label}
                className={`rounded px-2 py-1 text-xs font-medium ${
                  feature.enabled ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700"
                }`}
              >
                {feature.label}: {feature.enabled ? "enabled" : "locked"}
              </span>
            ))}
          </div>
          <div className="space-y-1 rounded-md border border-border/70 bg-muted/30 p-3 text-xs">
            <p>
              <span className="font-medium">Max sources:</span>{" "}
              {features.maxSources === null ? "Unlimited" : features.maxSources}
            </p>
            <p>
              <span className="font-medium">Max exports per month:</span>{" "}
              {features.maxExportsPerMonth === null ? "Unlimited" : features.maxExportsPerMonth}
            </p>
            <p>
              <span className="font-medium">Max members:</span>{" "}
              {features.maxMembers === null ? "Unlimited" : features.maxMembers}
            </p>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={() => void refresh()}>
            Refresh billing status
          </Button>
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Plans</CardTitle>
          <CardDescription>
            Free, Pro, and Business plans with Stripe checkout for paid upgrades.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 md:grid-cols-3">
            {planCards.map((card) => {
              const isCurrentPlan = plan === card.plan;
              const canCheckout = card.plan === "pro" || card.plan === "business";
              const isLoadingTarget = canCheckout && isCheckoutLoading === card.plan;
              return (
                <article key={card.plan} className="rounded-lg border border-border/70 bg-card p-4">
                  <div className="mb-2 flex items-center justify-between">
                    <h3 className="text-sm font-semibold">{card.label}</h3>
                    {isCurrentPlan ? (
                      <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                        Current
                      </span>
                    ) : null}
                  </div>
                  {card.displayPrice ? (
                    <p className="text-xl font-semibold">
                      {card.displayPrice}
                      <span className="ml-1 text-xs font-medium text-muted-foreground">/mo</span>
                    </p>
                  ) : (
                    <p className="text-xs font-medium text-muted-foreground">Price shown at checkout</p>
                  )}
                  <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
                    {card.included.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                  <div className="mt-4">
                    {isCurrentPlan ? (
                      <Button type="button" variant="outline" className="w-full" disabled>
                        Current plan
                      </Button>
                    ) : canCheckout ? (
                      <Button
                        type="button"
                        className="w-full"
                        disabled={isCheckoutLoading !== null || !selectedOrgId}
                        onClick={() => void startCheckout(card.plan as Exclude<BillingPlan, "free">)}
                      >
                        {isLoadingTarget ? "Redirecting..." : `Upgrade to ${card.label}`}
                      </Button>
                    ) : (
                      <Button
                        type="button"
                        variant="outline"
                        className="w-full"
                        disabled={isPortalLoading || !selectedOrgId}
                        onClick={openPortal}
                      >
                        {isPortalLoading ? "Opening..." : "Manage in Stripe"}
                      </Button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
          <div className="pt-1">
            <Button type="button" variant="outline" disabled={isPortalLoading || !selectedOrgId} onClick={openPortal}>
              {isPortalLoading ? "Opening..." : "Manage billing"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Recent Webhook Events</CardTitle>
          <CardDescription>Most recent Stripe webhook processing records for this workspace.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingEvents ? <p className="text-sm text-muted-foreground">Loading events...</p> : null}
          {!isLoadingEvents && events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No billing events yet.</p>
          ) : null}

          {!isLoadingEvents && events.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-border/70 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-2 py-2">Type</th>
                    <th className="px-2 py-2">Status</th>
                    <th className="px-2 py-2">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((event) => (
                    <tr key={event.id} className="border-b border-border/50">
                      <td className="px-2 py-2">{event.event_type}</td>
                      <td className="px-2 py-2">
                        <span className={`rounded px-2 py-1 text-xs font-medium ${eventStatusClass(event.status)}`}>
                          {event.status}
                        </span>
                      </td>
                      <td className="px-2 py-2">{formatDateTime(event.processed_at ?? event.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {successMessage ? <p className="text-sm text-emerald-700">{successMessage}</p> : null}
      {canceledMessage ? <p className="text-sm text-amber-700">{canceledMessage}</p> : null}
      {planError ? <p className="text-sm text-destructive">{planError}</p> : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}
