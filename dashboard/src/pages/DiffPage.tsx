import { useSearch, useNavigate } from "@tanstack/react-router";
import { useRun } from "../api";
import { SeverityBadge } from "../components/SeverityBadge";
import { DagStages } from "../components/DagStages";
import type { AgentResult, AgentStatus, BriefingOutput, Severity } from "../schemas";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
}

function Delta({ before, after, label }: { before: number; after: number; label: string }) {
  const diff = after - before;
  const color =
    diff > 0 ? "var(--color-error)" : diff < 0 ? "var(--color-success)" : "var(--color-text-muted)";
  return (
    <div className="text-center">
      <div
        className="text-2xl font-semibold"
        style={{ fontFamily: "var(--font-mono)", color }}
      >
        {diff > 0 ? "+" : ""}{diff}
      </div>
      <div className="text-xs mt-0.5" style={{ color: "var(--color-text-muted)" }}>
        {label}
      </div>
      <div className="text-xs" style={{ color: "var(--color-text-secondary)", fontFamily: "var(--font-mono)" }}>
        {before} → {after}
      </div>
    </div>
  );
}

function AgentDiff({ nameA, resultA, resultB }: {
  nameA: string;
  resultA: AgentResult | undefined;
  resultB: AgentResult | undefined;
}) {
  const onlyInA = resultA && !resultB;
  const onlyInB = !resultA && resultB;
  const regression = resultA?.status === "success" && resultB?.status === "error";
  const recovered = resultA?.status === "error" && resultB?.status === "success";

  const findingsA = new Map((resultA?.findings ?? []).map((f) => [f.id, f]));
  const findingsB = new Map((resultB?.findings ?? []).map((f) => [f.id, f]));

  const allIds = new Set([...findingsA.keys(), ...findingsB.keys()]);
  const newFindings = [...findingsB.values()].filter((f) => !findingsA.has(f.id));
  const removedFindings = [...findingsA.values()].filter((f) => !findingsB.has(f.id));
  const unchanged = [...allIds].filter((id) => findingsA.has(id) && findingsB.has(id)).length;

  const displayName = resultA?.agent_display_name ?? resultB?.agent_display_name ?? nameA;

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{
        border: `1px solid ${
          regression
            ? "var(--color-error)60"
            : recovered
            ? "var(--color-success)40"
            : "var(--color-border)"
        }`,
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{
          background: "var(--color-surface)",
          borderColor: "var(--color-border-subtle)",
        }}
      >
        <span className="text-sm font-medium" style={{ color: "var(--color-text-primary)" }}>
          {displayName}
        </span>

        <div className="flex items-center gap-3 text-xs" style={{ fontFamily: "var(--font-mono)" }}>
          {onlyInA && (
            <span style={{ color: "var(--color-text-muted)" }}>not in B</span>
          )}
          {onlyInB && (
            <span style={{ color: "var(--color-accent)" }}>new in B</span>
          )}
          {regression && (
            <span
              className="px-2 py-0.5 rounded font-semibold"
              style={{ background: "var(--color-action-dim)", color: "var(--color-action)" }}
            >
              REGRESSION
            </span>
          )}
          {recovered && (
            <span
              className="px-2 py-0.5 rounded font-semibold"
              style={{ background: "var(--color-info-dim)", color: "var(--color-info)" }}
            >
              RECOVERED
            </span>
          )}
          {!regression && !recovered && !onlyInA && !onlyInB && (
            <span style={{ color: "var(--color-text-muted)" }}>
              {newFindings.length > 0 && (
                <span style={{ color: "var(--color-success)" }}>+{newFindings.length} </span>
              )}
              {removedFindings.length > 0 && (
                <span style={{ color: "var(--color-error)" }}>-{removedFindings.length} </span>
              )}
              {unchanged} unchanged
            </span>
          )}
        </div>
      </div>

      {/* New findings in B */}
      {newFindings.length > 0 && (
        <div>
          {newFindings.map((f) => (
            <div
              key={f.id}
              className="flex items-start gap-3 px-4 py-2 border-l-2"
              style={{
                borderLeftColor: "var(--color-success)",
                background: "var(--color-info-dim)",
              }}
            >
              <SeverityBadge severity={f.severity} />
              <span className="text-xs" style={{ color: "var(--color-text-primary)" }}>
                {f.title}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Removed findings from A */}
      {removedFindings.length > 0 && (
        <div>
          {removedFindings.map((f) => (
            <div
              key={f.id}
              className="flex items-start gap-3 px-4 py-2 border-l-2 opacity-50"
              style={{
                borderLeftColor: "var(--color-error)",
                background: "var(--color-action-dim)",
              }}
            >
              <SeverityBadge severity={f.severity} />
              <span className="text-xs line-through" style={{ color: "var(--color-text-secondary)" }}>
                {f.title}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function DiffPage() {
  const search = useSearch({ from: "/diff" });
  const navigate = useNavigate();
  const { a, b } = search;

  const { data: runA, isLoading: loadingA } = useRun(a || undefined);
  const { data: runB, isLoading: loadingB } = useRun(b || undefined);

  if (!a || !b) {
    return (
      <div className="py-24 text-center">
        <div className="text-sm mb-2" style={{ color: "var(--color-text-muted)" }}>
          Select two runs from the run list to compare.
        </div>
        <button
          onClick={() => navigate({ to: "/" })}
          className="text-xs"
          style={{
            color: "var(--color-accent)",
            background: "none",
            border: "none",
            cursor: "pointer",
          }}
        >
          ← Back to list
        </button>
      </div>
    );
  }

  if (loadingA || loadingB) {
    return (
      <div
        className="flex items-center justify-center py-24 text-sm"
        style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}
      >
        loading runs...
      </div>
    );
  }

  if (!runA || !runB) {
    return (
      <div className="py-24 text-center text-sm" style={{ color: "var(--color-error)" }}>
        One or both runs could not be loaded.
      </div>
    );
  }

  const statusMapA = Object.fromEntries(runA.agent_results.map((r) => [r.agent_name, r.status as AgentStatus]));
  const statusMapB = Object.fromEntries(runB.agent_results.map((r) => [r.agent_name, r.status as AgentStatus]));

  const allAgentNames = [
    ...new Set([
      ...runA.agent_results.map((r) => r.agent_name),
      ...runB.agent_results.map((r) => r.agent_name),
    ]),
  ];

  const stagesChanged =
    runA.execution &&
    runB.execution &&
    JSON.stringify(runA.execution.stages) !== JSON.stringify(runB.execution.stages);

  return (
    <div className="space-y-6">
      {/* Breadcrumb + back */}
      <div className="flex items-center gap-2 text-xs" style={{ color: "var(--color-text-muted)" }}>
        <button
          onClick={() => navigate({ to: "/" })}
          className="hover:underline"
          style={{ color: "var(--color-text-muted)", background: "none", border: "none", cursor: "pointer", padding: 0 }}
        >
          Runs
        </button>
        <span>/</span>
        <span>Diff</span>
      </div>

      {/* Run labels */}
      <div className="grid grid-cols-2 gap-4">
        {([runA, runB] as BriefingOutput[]).map((run, idx) => (
          <div
            key={idx}
            className="rounded-lg px-4 py-3"
            style={{
              background: "var(--color-surface)",
              border: `1px solid ${idx === 0 ? "var(--color-border)" : "var(--color-accent)40"}`,
            }}
          >
            <div
              className="text-xs mb-0.5"
              style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}
            >
              {idx === 0 ? "A (baseline)" : "B (current)"}
            </div>
            <div
              className="text-sm font-medium"
              style={{ fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}
            >
              {run.briefing_id}
            </div>
            <div className="text-xs mt-0.5" style={{ color: "var(--color-text-secondary)" }}>
              {fmtDate(run.generated_at)} UTC · {run.summary.total_findings} findings
            </div>
          </div>
        ))}
      </div>

      {/* Summary deltas */}
      <div
        className="rounded-lg px-6 py-5"
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
        }}
      >
        <div className="text-xs font-medium mb-4 uppercase tracking-wider" style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
          Summary Delta
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 divide-x divide-[var(--color-border)]">
          <Delta
            before={runA.summary.total_findings}
            after={runB.summary.total_findings}
            label="total findings"
          />
          {(["action_needed", "warning", "info"] as Severity[]).map((sev) => (
            <Delta
              key={sev}
              before={runA.summary.by_severity[sev] ?? 0}
              after={runB.summary.by_severity[sev] ?? 0}
              label={sev.replace("_", " ")}
            />
          ))}
        </div>
      </div>

      {/* Per-agent diff */}
      <div>
        <div
          className="text-xs font-medium mb-3 uppercase tracking-wider"
          style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}
        >
          Agent Comparison
        </div>
        <div className="space-y-3">
          {allAgentNames.map((name) => {
            const rA = runA.agent_results.find((r) => r.agent_name === name);
            const rB = runB.agent_results.find((r) => r.agent_name === name);
            return <AgentDiff key={name} nameA={name} resultA={rA} resultB={rB} />;
          })}
        </div>
      </div>

      {/* DAG comparison */}
      {runA.execution && runB.execution && (
        <div>
          <div
            className="text-xs font-medium mb-3 uppercase tracking-wider"
            style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}
          >
            DAG Comparison
            {stagesChanged && (
              <span
                className="ml-2 px-1.5 py-0.5 rounded"
                style={{
                  color: "var(--color-warning)",
                  background: "var(--color-warning-dim)",
                  fontSize: "10px",
                }}
              >
                changed
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4">
            {([
              { label: "A (baseline)", run: runA, statusMap: statusMapA },
              { label: "B (current)", run: runB, statusMap: statusMapB },
            ] as { label: string; run: BriefingOutput; statusMap: Record<string, AgentStatus> }[]).map(({ label, run, statusMap }) => (
              <div
                key={label}
                className="rounded-lg px-4 py-3"
                style={{
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <div
                  className="text-xs mb-3"
                  style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}
                >
                  {label}
                </div>
                {run.execution && (
                  <DagStages stages={run.execution.stages} statusMap={statusMap} />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
