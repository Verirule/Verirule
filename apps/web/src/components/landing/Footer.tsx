import Link from "next/link";

import { SocialIcons } from "@/src/components/SocialIcons";

export function Footer() {
  return (
    <footer className="border-t border-gray-200 bg-white py-10 text-slate-700">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 sm:px-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-gray-200 bg-slate-50 p-2">
              <img src="/logo.svg" alt="Verirule" className="h-full w-full object-contain" />
            </span>
            <span className="text-lg font-semibold text-slate-900">Verirule</span>
          </div>
          <p className="max-w-md text-sm text-slate-600">
            Compliance operations for controls, findings, evidence collection, and audit preparation.
          </p>
          <SocialIcons />
        </div>

        <div className="space-y-3 text-sm">
          <div className="flex flex-wrap gap-4">
            <Link
              href="https://github.com/Verirule/Verirule/blob/main/docs/SECURITY.md"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-slate-700 hover:text-blue-700"
            >
              Security
            </Link>
            <Link href="/privacy" className="font-medium text-slate-700 hover:text-blue-700">
              Privacy
            </Link>
            <Link href="/policy" className="font-medium text-slate-700 hover:text-blue-700">
              Policy
            </Link>
            <Link href="/terms" className="font-medium text-slate-700 hover:text-blue-700">
              Terms
            </Link>
            <Link href="/service" className="font-medium text-slate-700 hover:text-blue-700">
              Service
            </Link>
            <Link
              href="https://www.gnu.org/licenses/agpl-3.0.en.html"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-slate-700 hover:text-blue-700"
            >
              License
            </Link>
          </div>
          <p className="text-slate-500">&copy; Verirule</p>
        </div>
      </div>
    </footer>
  );
}
