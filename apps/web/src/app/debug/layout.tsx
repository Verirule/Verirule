import { notFound } from "next/navigation";

type DebugLayoutProps = {
  children: React.ReactNode;
};

export default function DebugLayout({ children }: DebugLayoutProps) {
  if (process.env.VERIRULE_ENABLE_DEBUG_PAGES !== "true") {
    notFound();
  }

  return <>{children}</>;
}
