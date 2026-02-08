import { useEffect } from "react";
import { useRouter } from "next/router";

import { isTokenValid } from "../utils/auth";

export default function DashboardPage() {
  const router = useRouter();

  useEffect(() => {
    if (!isTokenValid()) {
      router.replace("/login");
    }
  }, [router]);

  return (
    <main style={{ maxWidth: 640, margin: "64px auto", padding: 16 }}>
      <h1>Dashboard</h1>
      <p>Authenticated access only.</p>
    </main>
  );
}
