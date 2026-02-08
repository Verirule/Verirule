import { FormEvent, useState } from "react";
import { useRouter } from "next/router";

import Layout from "../components/Layout";
import { login } from "../utils/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <main className="mx-auto max-w-md px-4 py-12">
        <h1 className="text-2xl font-semibold text-brand-900 sm:text-3xl">Login</h1>
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <label className="block text-sm text-brand-700">
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-1 w-full rounded-md border border-brand-100 px-3 py-2"
            />
          </label>
          <label className="block text-sm text-brand-700">
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="mt-1 w-full rounded-md border border-brand-100 px-3 py-2"
            />
          </label>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-brand-900 px-4 py-2 text-white"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </main>
    </Layout>
  );
}
