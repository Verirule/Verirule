import { useEffect } from "react";
import { useRouter } from "next/router";

import Layout from "../components/Layout";
import { isTokenValid } from "../utils/auth";

export default function DashboardPage() {
  const router = useRouter();

  useEffect(() => {
    if (!isTokenValid()) {
      router.replace("/login");
    }
  }, [router]);

  return (
    <Layout>
      <main className="mx-auto max-w-6xl px-4 py-12">
        <div className="flex flex-col gap-6">
          <div>
            <h1 className="text-2xl font-semibold text-brand-900 sm:text-3xl">Dashboard</h1>
            <p className="mt-2 text-brand-700">Authenticated access only.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-md border border-brand-100 p-4">
              <p className="text-xs text-brand-700">Compliance score</p>
              <p className="text-xl font-semibold text-brand-900">98%</p>
            </div>
            <div className="rounded-md border border-brand-100 p-4">
              <p className="text-xs text-brand-700">Open alerts</p>
              <p className="text-xl font-semibold text-brand-900">3</p>
            </div>
            <div className="rounded-md border border-brand-100 p-4">
              <p className="text-xs text-brand-700">Last audit</p>
              <p className="text-xl font-semibold text-brand-900">Today</p>
            </div>
          </div>
        </div>
      </main>
    </Layout>
  );
}
