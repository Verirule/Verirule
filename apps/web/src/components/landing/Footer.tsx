import Link from "next/link";

import { LogoMark } from "@/src/components/brand/LogoMark";
import { SocialIcons } from "@/src/components/SocialIcons";

export function Footer() {
  return (
    <footer className="border-t border-slate-800 bg-[#0A1527] py-12 text-slate-300">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 sm:px-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <LogoMark className="h-8 w-8 text-slate-200" />
            <span className="text-lg font-semibold text-white">Verirule</span>
          </div>
          <p className="max-w-md text-sm text-slate-400">
            Regulatory monitoring and evidence workflows for teams operating in audited environments.
          </p>
          <SocialIcons />
        </div>

        <div className="space-y-4 text-sm">
          <div className="flex flex-wrap gap-5">
            <Link
              href="https://github.com/Verirule/Verirule/blob/main/docs/SECURITY.md"
              target="_blank"
              rel="noopener noreferrer"
              className="transition-colors hover:text-white"
            >
              Security
            </Link>
            <Link href="/privacy" className="transition-colors hover:text-white">
              Privacy
            </Link>
            <Link href="/policy" className="transition-colors hover:text-white">
              Policy
            </Link>
            <Link href="/terms" className="transition-colors hover:text-white">
              Terms
            </Link>
            <Link href="/service" className="transition-colors hover:text-white">
              Service
            </Link>
            <Link
              href="https://www.gnu.org/licenses/agpl-3.0.en.html"
              target="_blank"
              rel="noopener noreferrer"
              className="transition-colors hover:text-white"
            >
              License (GNU AGPLv3)
            </Link>
          </div>
          <p className="text-slate-500">&copy; Verirule</p>
        </div>
      </div>
    </footer>
  );
}
