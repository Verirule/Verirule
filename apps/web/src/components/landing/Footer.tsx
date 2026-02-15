import Link from "next/link";
import Image from "next/image";

import { LogoMark } from "@/src/components/brand/LogoMark";
import { SocialIcons } from "@/src/components/SocialIcons";

export function Footer() {
  return (
    <footer className="border-t-2 border-[#1E6B46] bg-[#0A3B27] py-12 text-[#D4F0E0]">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 sm:px-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-12 w-12 items-center justify-center rounded-lg border border-[#2C7B56] bg-[#145636] p-1.5">
              <LogoMark className="h-full w-full" />
            </span>
            <Image
              src="/brand/logo.svg"
              alt="Verirule logo"
              width={180}
              height={56}
              className="h-8 w-auto object-contain"
            />
          </div>
          <p className="max-w-md text-sm text-[#D4F0E0]/85">
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
              className="font-medium transition-colors hover:text-white"
            >
              Security
            </Link>
            <Link href="/privacy" className="font-medium transition-colors hover:text-white">
              Privacy
            </Link>
            <Link href="/policy" className="font-medium transition-colors hover:text-white">
              Policy
            </Link>
            <Link href="/terms" className="font-medium transition-colors hover:text-white">
              Terms
            </Link>
            <Link href="/service" className="font-medium transition-colors hover:text-white">
              Service
            </Link>
            <Link
              href="https://linkedin.com/in/verirule-xyz-0684273b0"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium transition-colors hover:text-white"
            >
              LinkedIn
            </Link>
            <Link
              href="https://www.gnu.org/licenses/agpl-3.0.en.html"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium transition-colors hover:text-white"
            >
              License (GNU AGPLv3)
            </Link>
          </div>
          <p className="text-[#B6DEC9]/80">&copy; Verirule</p>
        </div>
      </div>
    </footer>
  );
}
