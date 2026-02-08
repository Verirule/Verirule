import clsx from "clsx";

type Props = {
  title: string;
  status: "compliant" | "non_compliant" | "unknown";
  lastCheckedAt?: string | null;
};

const statusStyles: Record<Props["status"], string> = {
  compliant: "bg-emerald-100 text-emerald-800",
  non_compliant: "bg-rose-100 text-rose-800",
  unknown: "bg-amber-100 text-amber-800",
};

export default function ComplianceStatusCard({
  title,
  status,
  lastCheckedAt,
}: Props) {
  return (
    <div className="rounded-md border border-brand-100 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-brand-900">{title}</p>
          <p className="mt-1 text-xs text-brand-700">
            Last checked: {lastCheckedAt ? new Date(lastCheckedAt).toLocaleString() : "-"}
          </p>
        </div>
        <span
          className={clsx(
            "rounded-full px-2 py-1 text-xs font-semibold",
            statusStyles[status]
          )}
        >
          {status.replace("_", " ")}
        </span>
      </div>
    </div>
  );
}
