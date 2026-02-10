import { cn } from "@/lib/utils";

type LogoMarkProps = {
  className?: string;
};

export function LogoMark({ className }: LogoMarkProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 256 256"
      fill="none"
      className={cn("shrink-0", className)}
      aria-hidden
    >
      <path
        d="M128 18c34 22 70 26 94 30v72c0 64-44 108-94 118C78 228 34 184 34 120V48c24-4 60-8 94-30Z"
        stroke="currentColor"
        strokeWidth="14"
        strokeLinejoin="round"
      />
      <path
        d="M128 84a44 44 0 1 1-44 44"
        stroke="currentColor"
        strokeWidth="14"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.55"
      />
      <path
        d="M58 138h32l16-26 22 52 18-34h52"
        stroke="currentColor"
        strokeWidth="14"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="198" cy="88" r="8" fill="currentColor" />
      <circle cx="84" cy="138" r="6" fill="currentColor" opacity="0.9" />
    </svg>
  );
}
