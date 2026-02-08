import { useEffect } from "react";
import { useRouter } from "next/router";

import Navbar from "../components/Navbar";
import { isTokenValid } from "../utils/auth";

export default function DashboardPage() {
  const router = useRouter();

  useEffect(() => {
    if (!isTokenValid()) {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div>
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-12">
        <h1 className="text-2xl font-semibold text-brand-900">Dashboard</h1>
        <p className="mt-2 text-brand-700">Authenticated access only.</p>
      </main>
    </div>
  );
}
