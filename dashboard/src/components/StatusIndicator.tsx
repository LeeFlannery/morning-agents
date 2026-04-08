import type { AgentStatus } from "../schemas";

const STATUS_CONFIG: Record<AgentStatus, { color: string; label: string }> = {
  success: { color: "var(--color-success)", label: "ok" },
  partial: { color: "var(--color-partial)", label: "partial" },
  error: { color: "var(--color-error)", label: "error" },
};

export function StatusIndicator({ status }: { status: AgentStatus }) {
  const cfg = STATUS_CONFIG[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs"
      style={{ color: cfg.color, fontFamily: "var(--font-mono)" }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ background: cfg.color }}
      />
      {cfg.label}
    </span>
  );
}
