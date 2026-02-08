import { AuthButton } from "@/components/auth-button";
import { EnvVarWarning } from "@/components/env-var-warning";
import { Button } from "@/components/ui/button";
import { hasEnvVars } from "@/lib/utils";
import Image from "next/image";
import Link from "next/link";
import { Suspense } from "react";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center">
      <div className="flex-1 w-full flex flex-col gap-12 items-center">
        <nav className="w-full flex justify-center border-b border-b-foreground/10 h-16">
          <div className="w-full max-w-5xl flex justify-between items-center p-3 px-5 text-sm">
            <Link href="/" className="flex items-center gap-3 font-semibold">
              <Image src="/brand/logo.svg" alt="Verirule logo" width={26} height={26} />
              <span>Verirule</span>
            </Link>
            {!hasEnvVars ? (
              <EnvVarWarning />
            ) : (
              <Suspense>
                <AuthButton />
              </Suspense>
            )}
          </div>
        </nav>

        <section className="w-full max-w-5xl px-5 pt-12 pb-20">
          <div className="rounded-2xl border bg-card p-8 md:p-12">
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
              Compliance monitoring with secure, token-verified workflows.
            </h1>
            <p className="mt-4 text-muted-foreground max-w-2xl">
              Verirule combines Supabase authentication with a FastAPI backend to monitor
              regulatory changes and deliver auditable alerts.
            </p>
            <div className="mt-8 flex gap-3">
              <Button asChild>
                <Link href="/protected">Open Dashboard</Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/auth/login">Sign in</Link>
              </Button>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
