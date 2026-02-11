import Link from "next/link";

import { LogoMark } from "@/src/components/brand/LogoMark";
import { SocialIcons } from "@/src/components/SocialIcons";

export function Footer() {
  return (
    <footer className="border-t border-blue-200 bg-[#0B3B8C] py-12 text-blue-100">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 sm:px-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <LogoMark className="h-8 w-8 text-blue-200" />
            <span className="text-lg font-semibold text-white">Verirule</span>
          </div>
          <p className="max-w-md text-sm text-blue-100/85">
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
              className="transition-colors hover:text-blue-200"
            >
              Security
            </Link>
            <Link href="/privacy" className="transition-colors hover:text-blue-200">
              Privacy
            </Link>
            <Link href="/policy" className="transition-colors hover:text-blue-200">
              Policy
            </Link>
            <Link href="/terms" className="transition-colors hover:text-blue-200">
              Terms
            </Link>
            <Link href="/service" className="transition-colors hover:text-blue-200">
              Service
            </Link>
            <Link
              href="https://www.gnu.org/licenses/agpl-3.0.en.html"
              target="_blank"
              rel="noopener noreferrer"
              className="transition-colors hover:text-blue-200"
            >
              License (GNU AGPLv3)
            </Link>
          </div>
          <p className="text-blue-200/70">&copy; Verirule</p>
        </div>
      </div>
    </footer>
  );
}
