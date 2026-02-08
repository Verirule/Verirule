import clsx from "clsx";

type Violation = {
  id: string;
  message: string;
  severity: "low" | "medium" | "high";
  detected_at: string;
};

type Props = {
  items: Violation[];
};

const severityStyles: Record<Violation["severity"], string> = {
  low: "bg-amber-100 text-amber-800",
  medium: "bg-orange-100 text-orange-800",
  high: "bg-rose-100 text-rose-800",
};

export default function ViolationsList({ items }: Props) {
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.id} className="rounded-md border border-brand-100 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-brand-900">{item.message}</p>
              <p className="mt-1 text-xs text-brand-700">
                Detected: {new Date(item.detected_at).toLocaleString()}
              </p>
            </div>
            <span
              className={clsx(
                "rounded-full px-2 py-1 text-xs font-semibold",
                severityStyles[item.severity]
              )}
            >
              {item.severity}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
