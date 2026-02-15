import { AuthButton } from "@/components/auth-button";
import { EnvVarWarning } from "@/components/env-var-warning";
import { hasEnvVars } from "@/lib/utils";
import Link from "next/link";
import { Suspense } from "react";

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="min-h-screen flex flex-col items-center bg-white">
      <div className="flex-1 w-full flex flex-col gap-10 items-center">
        <nav className="vr-surface h-20 w-full border-b border-gray-200">
          <div className="w-full max-w-5xl flex justify-between items-center p-3 px-5 text-sm">
            <Link href="/" className="flex items-center gap-3 font-semibold">
              <span className="vr-brand-chip h-11 w-11">
                <img src="/logo.svg" alt="Verirule" className="h-full w-full object-contain" />
              </span>
              <span className="text-lg font-bold">Verirule</span>
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
        <div className="flex-1 flex flex-col gap-8 w-full max-w-5xl p-5">{children}</div>
        <footer className="vr-surface mx-auto flex w-full items-center justify-center border-t border-gray-200 py-8 text-center text-xs text-slate-600">
          <p>Verirule dashboard</p>
        </footer>
      </div>
    </main>
  );
}
