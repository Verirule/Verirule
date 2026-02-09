"use client";

import Link from "next/link";

export default function ErrorPage() {
  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-lg rounded-lg border p-6 space-y-3">
        <h1 className="text-2xl font-semibold">Something went wrong</h1>
        <p className="text-sm text-muted-foreground">
          Check Supabase environment variables and redirect URLs.
        </p>
        <Link href="/" className="text-sm underline underline-offset-4">
          Back to home
        </Link>
      </div>
    </main>
  );
}
