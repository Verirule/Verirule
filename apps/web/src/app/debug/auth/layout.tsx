import { notFound } from "next/navigation";

type DebugAuthLayoutProps = {
  children: React.ReactNode;
};

export default function DebugAuthLayout({ children }: DebugAuthLayoutProps) {
  if (process.env.VERIRULE_ENABLE_DEBUG_PAGES !== "true") {
    notFound();
  }

  return <>{children}</>;
}
