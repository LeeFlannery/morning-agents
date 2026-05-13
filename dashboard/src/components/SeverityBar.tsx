import type { Severity } from "../schemas";

const SEV_ORDER: Severity[] = ["action_needed", "warning", "info"];
const SEV_COLOR: Record<Severity, string> = {
  action_needed: "var(--color-action)",
  warning: "var(--color-warning)",
  info: "var(--color-info)",
};
const SEV_LABEL: Record<Severity, string> = {
  action_needed: "action",
  warning: "warn",
  info: "info",
};

export function SeverityBar({
  bySeverity,
}: {
  bySeverity: Record<string, number>;
}) {
  const entries = SEV_ORDER.map((s) => ({
    sev: s,
    count: bySeverity[s] ?? 0,
  })).filter((e) => e.count > 0);

  if (entries.length === 0) return null;

  return (
    <div className="flex items-center gap-3">
      {entries.map(({ sev, count }) => (
        <span
          key={sev}
          className="flex items-center gap-1 text-xs"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ background: SEV_COLOR[sev as Severity] }}
          />
          <span style={{ color: SEV_COLOR[sev as Severity] }}>{count}</span>
          <span style={{ color: "var(--color-text-muted)" }}>
            {SEV_LABEL[sev as Severity]}
          </span>
        </span>
      ))}
    </div>
  );
}
