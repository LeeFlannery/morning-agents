import type { Severity } from "../schemas";

const SEVERITY_CONFIG: Record<
  Severity,
  { label: string; color: string; bg: string }
> = {
  info: {
    label: "INFO",
    color: "var(--color-info)",
    bg: "var(--color-info-dim)",
  },
  warning: {
    label: "WARN",
    color: "var(--color-warning)",
    bg: "var(--color-warning-dim)",
  },
  action_needed: {
    label: "ACTION",
    color: "var(--color-action)",
    bg: "var(--color-action-dim)",
  },
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  const cfg = SEVERITY_CONFIG[severity];
  return (
    <span
      className="inline-flex items-center text-xs font-medium px-1.5 py-0.5 rounded shrink-0"
      style={{
        fontFamily: "var(--font-mono)",
        color: cfg.color,
        background: cfg.bg,
        border: `1px solid ${cfg.color}30`,
        letterSpacing: "0.03em",
        minWidth: "52px",
        justifyContent: "center",
      }}
    >
      {cfg.label}
    </span>
  );
}
