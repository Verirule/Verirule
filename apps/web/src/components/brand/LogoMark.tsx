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
        d="M128 20c34 22 64 28 84 32v90c0 47-30 80-84 94-54-14-84-47-84-94V52c20-4 50-10 84-32Z"
        fill="currentColor"
      />
      <path
        d="M72 86h112"
        stroke="#FFFFFF"
        strokeOpacity="0.35"
        strokeWidth="12"
        strokeLinecap="round"
      />
      <path
        d="M76 132l34 34 70-70"
        stroke="#FFFFFF"
        strokeWidth="16"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
