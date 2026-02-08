import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { isTokenValid, logout } from "../utils/auth";

export default function Navbar() {
  const [authed, setAuthed] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setAuthed(isTokenValid());
  }, []);

  const logoHref = useMemo(() => (authed ? "/dashboard" : "/"), [authed]);

  const handleLogout = async () => {
    await logout();
    setAuthed(false);
    setOpen(false);
  };

  return (
    <header className="w-full border-b border-brand-100">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link href={logoHref} className="flex items-center gap-3">
          <img
            src="/branding/logo-mark.svg"
            alt="Verirule"
            className="h-8 w-8 sm:h-9 sm:w-9"
          />
          <img
            src="/branding/logo.svg"
            alt="Verirule"
            className="hidden h-6 sm:block sm:h-7 lg:h-8"
          />
        </Link>

        <nav className="hidden items-center gap-4 text-sm md:flex">
          {authed ? (
            <>
              <Link className="text-brand-700 hover:text-brand-900" href="/dashboard">
                Dashboard
              </Link>
              <Link className="text-brand-700 hover:text-brand-900" href="/alerts">
                Alerts
              </Link>
              <Link className="text-brand-700 hover:text-brand-900" href="/business">
                Business
              </Link>
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-md border border-brand-100 px-3 py-2 text-brand-900"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link className="text-brand-700 hover:text-brand-900" href="/login">
                Login
              </Link>
              <Link className="rounded-md bg-brand-900 px-3 py-2 text-white" href="/login">
                Get Started
              </Link>
            </>
          )}
        </nav>

        <button
          type="button"
          aria-label="Open menu"
          className="inline-flex items-center rounded-md border border-brand-100 p-2 text-brand-900 md:hidden"
          onClick={() => setOpen((prev) => !prev)}
        >
          <span className="block h-0.5 w-5 bg-brand-900" />
          <span className="mt-1 block h-0.5 w-5 bg-brand-900" />
          <span className="mt-1 block h-0.5 w-5 bg-brand-900" />
        </button>
      </div>

      {open && (
        <div className="border-t border-brand-100 bg-white md:hidden">
          <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-4 text-sm">
            {authed ? (
              <>
                <Link className="text-brand-900" href="/dashboard" onClick={() => setOpen(false)}>
                  Dashboard
                </Link>
                <Link className="text-brand-900" href="/alerts" onClick={() => setOpen(false)}>
                  Alerts
                </Link>
                <Link className="text-brand-900" href="/business" onClick={() => setOpen(false)}>
                  Business
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="rounded-md border border-brand-100 px-3 py-2 text-brand-900"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link className="text-brand-900" href="/login" onClick={() => setOpen(false)}>
                  Login
                </Link>
                <Link
                  className="rounded-md bg-brand-900 px-3 py-2 text-center text-white"
                  href="/login"
                  onClick={() => setOpen(false)}
                >
                  Get Started
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
