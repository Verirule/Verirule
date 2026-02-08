import { FormEvent, useEffect, useState } from "react";

import Layout from "../components/Layout";
import { api } from "../lib/api";
import { isTokenValid } from "../utils/auth";

type BusinessProfile = {
  id?: string;
  business_name: string;
  industry: string;
  jurisdiction: string;
};

export default function BusinessPage() {
  const [profile, setProfile] = useState<BusinessProfile>({
    business_name: "",
    industry: "",
    jurisdiction: "",
  });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<"idle" | "saved" | "error">("idle");

  useEffect(() => {
    if (!isTokenValid()) {
      window.location.assign("/login");
      return;
    }

    const load = async () => {
      try {
        const result = await api.get<{ data: BusinessProfile }>("/business/profile");
        if (result.data) {
          setProfile(result.data);
        }
      } catch {
        setStatus("error");
      }
    };

    load();
  }, []);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setStatus("idle");
    try {
      const result = await api.post<{ data: BusinessProfile }>(
        "/business/profile",
        profile
      );
      if (result.data) {
        setProfile(result.data);
      }
      setStatus("saved");
    } catch {
      setStatus("error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout>
      <main className="mx-auto max-w-xl px-4 py-8 sm:py-10">
        <h1 className="text-2xl font-semibold text-brand-900 sm:text-3xl">Business</h1>
        <p className="mt-2 text-sm text-brand-700">
          Keep your business profile up to date for accurate compliance monitoring.
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <label className="block text-sm text-brand-700">
            Business name
            <input
              type="text"
              value={profile.business_name}
              onChange={(e) => setProfile({ ...profile, business_name: e.target.value })}
              required
              className="mt-1 w-full rounded-md border border-brand-100 px-3 py-2"
            />
          </label>
          <label className="block text-sm text-brand-700">
            Industry
            <input
              type="text"
              value={profile.industry}
              onChange={(e) => setProfile({ ...profile, industry: e.target.value })}
              required
              className="mt-1 w-full rounded-md border border-brand-100 px-3 py-2"
            />
          </label>
          <label className="block text-sm text-brand-700">
            Jurisdiction
            <input
              type="text"
              value={profile.jurisdiction}
              onChange={(e) => setProfile({ ...profile, jurisdiction: e.target.value })}
              required
              className="mt-1 w-full rounded-md border border-brand-100 px-3 py-2"
            />
          </label>

          <button
            type="submit"
            disabled={saving}
            className="w-full rounded-md bg-brand-900 px-4 py-2 text-white"
          >
            {saving ? "Saving..." : "Save profile"}
          </button>
          {status === "saved" && (
            <p className="text-sm text-emerald-700">Profile saved.</p>
          )}
          {status === "error" && (
            <p className="text-sm text-rose-700">Unable to save profile.</p>
          )}
        </form>
      </main>
    </Layout>
  );
}
