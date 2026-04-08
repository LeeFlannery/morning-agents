import type { AgentStatus } from "../schemas";

const STATUS_COLOR: Record<AgentStatus, string> = {
  success: "var(--color-success)",
  partial: "var(--color-partial)",
  error: "var(--color-error)",
};

export function DagStages({
  stages,
  statusMap,
}: {
  stages: string[][];
  statusMap: Record<string, AgentStatus>;
}) {
  if (!stages || stages.length === 0) return null;

  return (
    <div className="flex items-start gap-0">
      {stages.map((tier, i) => (
        <div key={i} className="flex items-center">
          {/* Tier column */}
          <div className="flex flex-col gap-1.5">
            <div
              className="text-xs mb-1.5 text-center"
              style={{
                fontFamily: "var(--font-mono)",
                color: "var(--color-text-muted)",
              }}
            >
              depth {i}
            </div>
            {tier.map((agent) => {
              const status = statusMap[agent];
              return (
                <div
                  key={agent}
                  className="px-3 py-1.5 rounded text-xs"
                  style={{
                    fontFamily: "var(--font-mono)",
                    background: "var(--color-surface-2)",
                    border: `1px solid ${status ? STATUS_COLOR[status] + "40" : "var(--color-border)"}`,
                    color: status ? STATUS_COLOR[status] : "var(--color-text-secondary)",
                    minWidth: "120px",
                    textAlign: "center",
                  }}
                >
                  <span
                    className="inline-block w-1.5 h-1.5 rounded-full mr-1.5 align-middle"
                    style={{
                      background: status
                        ? STATUS_COLOR[status]
                        : "var(--color-text-muted)",
                    }}
                  />
                  {agent}
                </div>
              );
            })}
          </div>

          {/* Arrow between stages */}
          {i < stages.length - 1 && (
            <div
              className="px-3 text-base self-center mt-6"
              style={{ color: "var(--color-text-muted)" }}
            >
              →
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
