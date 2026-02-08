import { useEffect, useMemo, useState } from "react";

import Layout from "../components/Layout";
import ComplianceStatusCard from "../components/ComplianceStatusCard";
import ViolationsList from "../components/ViolationsList";
import { api } from "../lib/api";
import { isTokenValid } from "../utils/auth";

const statusOrder = {
  compliant: 0,
  unknown: 1,
  non_compliant: 2,
} as const;

type ComplianceStatus = {
  id: string;
  regulation_title: string;
  status: "compliant" | "non_compliant" | "unknown";
  last_checked_at: string | null;
};

type Violation = {
  id: string;
  message: string;
  severity: "low" | "medium" | "high";
  detected_at: string;
};

type Regulation = {
  id: string;
  title: string;
  last_updated_at: string | null;
};

type BusinessProfile = {
  id: string;
  business_name: string;
  industry: string;
  jurisdiction: string;
};

export default function DashboardPage() {
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [compliance, setCompliance] = useState<ComplianceStatus[]>([]);
  const [violations, setViolations] = useState<Violation[]>([]);
  const [regulations, setRegulations] = useState<Regulation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isTokenValid()) {
      window.location.assign("/login");
      return;
    }

    const load = async () => {
      try {
        const business = await api.get<{ data: BusinessProfile }>("/business/profile");
        setProfile(business.data);

        const summary = await api.get<{ data: ComplianceStatus[] }>(
          /compliance/status?business_id=
        );
        setCompliance(summary.data);

        const violationsResult = await api.get<{ data: Violation[] }>(
          /violations?business_id=
        );
        const sortedViolations = [...violationsResult.data].sort((a, b) => {
          const severityRank = { high: 0, medium: 1, low: 2 } as const;
          const diff = severityRank[a.severity] - severityRank[b.severity];
          if (diff !== 0) return diff;
          return new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime();
        });
        setViolations(sortedViolations);

        const recentRegs = await api.get<{ data: Regulation[] }>(
          "/regulations?limit=5&offset=0"
        );
        setRegulations(recentRegs.data);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const summaryCounts = useMemo(() => {
    const counts = { compliant: 0, non_compliant: 0, unknown: 0 };
    for (const item of compliance) {
      counts[item.status] += 1;
    }
    return counts;
  }, [compliance]);

  const orderedCompliance = useMemo(() => {
    return [...compliance].sort(
      (a, b) => statusOrder[a.status] - statusOrder[b.status]
    );
  }, [compliance]);

  return (
    <Layout>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:py-10">
        <div className="flex flex-col gap-6">
          <div>
            <h1 className="text-2xl font-semibold text-brand-900 sm:text-3xl">
              Verirule Dashboard
            </h1>
            <p className="mt-2 text-brand-700">
              {profile ? profile.business_name : "Loading business"}
            </p>
          </div>

          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-md border border-brand-100 p-4">
              <p className="text-xs text-brand-700">Compliant</p>
              <p className="text-2xl font-semibold text-emerald-700">
                {summaryCounts.compliant}
              </p>
            </div>
            <div className="rounded-md border border-brand-100 p-4">
              <p className="text-xs text-brand-700">Unknown</p>
              <p className="text-2xl font-semibold text-amber-700">
                {summaryCounts.unknown}
              </p>
            </div>
            <div className="rounded-md border border-brand-100 p-4">
              <p className="text-xs text-brand-700">Non-compliant</p>
              <p className="text-2xl font-semibold text-rose-700">
                {summaryCounts.non_compliant}
              </p>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <div>
              <h2 className="text-lg font-semibold text-brand-900">Compliance status</h2>
              <div className="mt-4 grid gap-3">
                {orderedCompliance.map((item) => (
                  <ComplianceStatusCard
                    key={item.id}
                    title={item.regulation_title}
                    status={item.status}
                    lastCheckedAt={item.last_checked_at}
                  />
                ))}
                {!loading && orderedCompliance.length === 0 && (
                  <p className="text-sm text-brand-700">No compliance data yet.</p>
                )}
              </div>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-brand-900">Recent updates</h2>
              <div className="mt-4 space-y-3">
                {regulations.map((reg) => (
                  <div key={reg.id} className="rounded-md border border-brand-100 p-4">
                    <p className="text-sm font-medium text-brand-900">{reg.title}</p>
                    <p className="mt-1 text-xs text-brand-700">
                      Updated: {reg.last_updated_at ? new Date(reg.last_updated_at).toLocaleString() : "-"}
                    </p>
                  </div>
                ))}
                {!loading && regulations.length === 0 && (
                  <p className="text-sm text-brand-700">No updates available.</p>
                )}
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-brand-900">Violations</h2>
            <div className="mt-4">
              {violations.length ? (
                <ViolationsList items={violations} />
              ) : (
                <p className="text-sm text-brand-700">No violations detected.</p>
              )}
            </div>
          </section>
        </div>
      </main>
    </Layout>
  );
}
