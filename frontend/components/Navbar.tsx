import Link from "next/link";
import { useEffect, useState } from "react";

import { isTokenValid } from "../utils/auth";

export default function Navbar() {
  const [href, setHref] = useState("/");

  useEffect(() => {
    setHref(isTokenValid() ? "/dashboard" : "/");
  }, []);

  return (
    <header className="w-full border-b border-brand-100">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link href={href} className="flex items-center gap-3">
          <img
            src="/branding/logo-mark.svg"
            alt="Verirule"
            className="h-8 w-8"
          />
          <img
            src="/branding/logo.svg"
            alt="Verirule"
            className="hidden h-8 sm:block"
          />
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link className="text-brand-700 hover:text-brand-900" href="/login">
            Login
          </Link>
          <Link className="rounded-md bg-brand-900 px-3 py-2 text-white" href="/dashboard">
            Dashboard
          </Link>
        </nav>
      </div>
    </header>
  );
}
