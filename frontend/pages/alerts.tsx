import { useEffect, useState } from "react";

import Layout from "../components/Layout";
import { api } from "../lib/api";
import { isTokenValid } from "../utils/auth";

const severityOrder = { high: 0, medium: 1, low: 2 } as const;

type AlertItem = {
  id: string;
  severity: "low" | "medium" | "high";
  title: string;
  message: string;
  acknowledged: boolean;
  created_at: string;
};

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isTokenValid()) {
      window.location.assign("/login");
      return;
    }

    const load = async () => {
      try {
        const result = await api.get<{ data: AlertItem[] }>("/alerts?limit=50&offset=0");
        const sorted = [...result.data].sort((a, b) => {
          if (a.acknowledged !== b.acknowledged) return a.acknowledged ? 1 : -1;
          const severityDiff = severityOrder[a.severity] - severityOrder[b.severity];
          if (severityDiff !== 0) return severityDiff;
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
        setAlerts(sorted);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const acknowledge = async (id: string) => {
    setAlerts((prev) =>
      prev.map((alert) => (alert.id === id ? { ...alert, acknowledged: true } : alert))
    );
    try {
      await api.post(/alerts//acknowledge);
    } catch {
      setAlerts((prev) =>
        prev.map((alert) => (alert.id === id ? { ...alert, acknowledged: false } : alert))
      );
    }
  };

  return (
    <Layout>
      <main className="mx-auto max-w-4xl px-4 py-8 sm:py-10">
        <h1 className="text-2xl font-semibold text-brand-900 sm:text-3xl">Alerts</h1>
        <p className="mt-2 text-sm text-brand-700">
          Review and acknowledge compliance alerts.
        </p>

        <div className="mt-6 space-y-4">
          {alerts.map((alert) => (
            <div key={alert.id} className="rounded-md border border-brand-100 p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-brand-900">{alert.title}</p>
                  <p className="mt-1 text-xs text-brand-700">{alert.message}</p>
                  <p className="mt-2 text-xs text-brand-700">
                    {new Date(alert.created_at).toLocaleString()} • {alert.severity}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => acknowledge(alert.id)}
                  disabled={alert.acknowledged}
                  className="rounded-md border border-brand-100 px-3 py-2 text-sm text-brand-900 disabled:opacity-50"
                >
                  {alert.acknowledged ? "Acknowledged" : "Acknowledge"}
                </button>
              </div>
            </div>
          ))}
          {!loading && alerts.length === 0 && (
            <p className="text-sm text-brand-700">No alerts to display.</p>
          )}
        </div>
      </main>
    </Layout>
  );
}
