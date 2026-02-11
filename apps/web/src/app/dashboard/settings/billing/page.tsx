"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { usePlan } from "@/src/components/billing/usePlan";
import type { BillingPlan } from "@/src/lib/billing";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type OrgsResponse = { orgs: OrgRecord[] };

function planBadgeClass(plan: BillingPlan): string {
  if (plan === "business") {
    return "bg-emerald-100 text-emerald-800";
  }
  if (plan === "pro") {
    return "bg-blue-100 text-blue-800";
  }
  return "bg-slate-100 text-slate-700";
}

export default function DashboardBillingPage() {
  const searchParams = useSearchParams();
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isCheckoutLoading, setIsCheckoutLoading] = useState<null | BillingPlan>(null);
  const [isPortalLoading, setIsPortalLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { plan, status, currentPeriodEnd, features, loading, error: planError, refresh } = usePlan(selectedOrgId);

  const successMessage = searchParams.get("success") === "1" ? "Checkout complete." : null;
  const canceledMessage = searchParams.get("canceled") === "1" ? "Checkout canceled." : null;
  const periodEndText = useMemo(() => {
    if (!currentPeriodEnd) return "N/A";
    const parsed = new Date(currentPeriodEnd);
    if (Number.isNaN(parsed.getTime())) return "N/A";
    return parsed.toLocaleDateString();
  }, [currentPeriodEnd]);

  useEffect(() => {
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

    void loadOrgs();
  }, []);

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
          Free includes manual runs and core monitoring. Pro unlocks Slack/Jira and scheduled monitoring.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Workspace</CardTitle>
          <CardDescription>Select the workspace to view or change billing.</CardDescription>
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
          <CardDescription>Plan status is synced from Stripe webhooks.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex items-center gap-2">
            <span className="font-medium">Plan:</span>
            <span className={`rounded px-2 py-1 text-xs font-medium ${planBadgeClass(plan)}`}>{plan}</span>
            {loading ? <span className="text-muted-foreground">Refreshing...</span> : null}
          </div>
          <p>
            <span className="font-medium">Subscription status:</span> {status ?? "inactive"}
          </p>
          <p>
            <span className="font-medium">Current period end:</span> {periodEndText}
          </p>
          <p>
            <span className="font-medium">Priority support:</span> {features.prioritySupport ? "enabled" : "not included"}
          </p>
          <Button type="button" variant="outline" size="sm" onClick={() => void refresh()}>
            Refresh billing status
          </Button>
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Plans</CardTitle>
          <CardDescription>Start a subscription or manage an existing one.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              disabled={isCheckoutLoading !== null || !selectedOrgId}
              onClick={() => void startCheckout("pro")}
            >
              {isCheckoutLoading === "pro" ? "Redirecting..." : "Upgrade to Pro"}
            </Button>
            <Button
              type="button"
              disabled={isCheckoutLoading !== null || !selectedOrgId}
              onClick={() => void startCheckout("business")}
            >
              {isCheckoutLoading === "business" ? "Redirecting..." : "Upgrade to Business"}
            </Button>
            <Button type="button" variant="outline" disabled={isPortalLoading || !selectedOrgId} onClick={openPortal}>
              {isPortalLoading ? "Opening..." : "Manage billing"}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Business includes priority support and higher operational limits.
          </p>
        </CardContent>
      </Card>

      {successMessage ? <p className="text-sm text-emerald-700">{successMessage}</p> : null}
      {canceledMessage ? <p className="text-sm text-amber-700">{canceledMessage}</p> : null}
      {planError ? <p className="text-sm text-destructive">{planError}</p> : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}
