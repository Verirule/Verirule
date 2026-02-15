import { cn } from "@/lib/utils";
import Image from "next/image";

type LogoMarkProps = {
  className?: string;
};

export function LogoMark({ className }: LogoMarkProps) {
  return (
    <Image
      src="/brand/icon.svg"
      alt="Verirule"
      width={256}
      height={256}
      className={cn("shrink-0 object-contain", className)}
    />
  );
}
