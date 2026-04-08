import { useParams, useNavigate } from "@tanstack/react-router";
import { useRun } from "../api";
import { AgentCard } from "../components/AgentCard";
import { DagStages } from "../components/DagStages";
import { SeverityBadge } from "../components/SeverityBadge";
import { fmtDate } from "../utils";
import type { AgentStatus, Severity } from "../schemas";

export function RunDetailPage() {
  const { runId } = useParams({ from: "/run/$runId" });
  const { data: run, isLoading, error } = useRun(runId);
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center py-24 text-sm"
        style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}
      >
        loading...
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="py-24 text-center">
        <div className="text-sm mb-2" style={{ color: "var(--color-error)" }}>
          Run not found
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

  const s = run.summary;
  const statusMap = Object.fromEntries(
    run.agent_results.map((r) => [r.agent_name, r.status as AgentStatus])
  );

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs" style={{ color: "var(--color-text-muted)" }}>
        <button
          onClick={() => navigate({ to: "/" })}
          className="hover:underline"
          style={{
            color: "var(--color-text-muted)",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 0,
          }}
        >
          Runs
        </button>
        <span>/</span>
        <span style={{ fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)" }}>
          {run.briefing_id}
        </span>
      </div>

      {/* Header */}
      <div
        className="rounded-lg px-5 py-4"
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
        }}
      >
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1
              className="text-base font-semibold m-0 mb-1"
              style={{
                fontFamily: "var(--font-mono)",
                color: "var(--color-text-primary)",
              }}
            >
              {run.briefing_id}
            </h1>
            <div
              className="text-xs flex items-center gap-3 flex-wrap"
              style={{ color: "var(--color-text-secondary)" }}
            >
              <span>{fmtDate(run.generated_at)}</span>
              <span style={{ color: "var(--color-text-muted)" }}>·</span>
              <span>
                {s.agents_run} agent{s.agents_run !== 1 ? "s" : ""}
              </span>
              <span style={{ color: "var(--color-text-muted)" }}>·</span>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                }}
              >
                {(run.duration_ms / 1000).toFixed(1)}s
              </span>
              <span style={{ color: "var(--color-text-muted)" }}>·</span>
              <span
                className="text-xs"
                style={{ fontFamily: "var(--font-mono)", color: "var(--color-text-muted)" }}
              >
                v{run.version}
              </span>
            </div>
          </div>

          <div
            className="flex items-center gap-3 flex-wrap"
          >
            <span
              className="text-sm"
              style={{ color: "var(--color-text-secondary)" }}
            >
              {s.total_findings} findings
            </span>
            {(["action_needed", "warning", "info"] as Severity[]).map((sev) => {
              const count = s.by_severity[sev];
              if (!count) return null;
              return (
                <div key={sev} className="flex items-center gap-1.5">
                  <SeverityBadge severity={sev} />
                  <span
                    className="text-sm font-medium"
                    style={{ color: "var(--color-text-primary)" }}
                  >
                    {count}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Agent cards */}
      <div>
        <h2
          className="text-xs font-medium mb-3 uppercase tracking-wider"
          style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}
        >
          Agents
        </h2>
        <div className="space-y-3">
          {run.agent_results.map((result) => (
            <AgentCard key={result.agent_name} result={result} />
          ))}
        </div>
      </div>

      {/* Cross-references */}
      {run.cross_references.length > 0 && (
        <div>
          <h2
            className="text-xs font-medium mb-3 uppercase tracking-wider"
            style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}
          >
            Cross-References
          </h2>
          <div
            className="rounded-lg overflow-hidden divide-y divide-[var(--color-border-subtle)]"
            style={{ border: "1px solid var(--color-border)" }}
          >
            {run.cross_references.map((xref) => (
              <div
                key={xref.id}
                className="px-4 py-3 flex gap-3"
                style={{ background: "var(--color-surface)" }}
              >
                <SeverityBadge severity={xref.severity} />
                <div className="flex-1 min-w-0">
                  <div
                    className="text-sm"
                    style={{ color: "var(--color-text-primary)" }}
                  >
                    {xref.title}
                  </div>
                  {xref.detail && (
                    <div
                      className="text-xs mt-1"
                      style={{ color: "var(--color-text-secondary)" }}
                    >
                      {xref.detail}
                    </div>
                  )}
                  <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                    {xref.source_agents.map((a) => (
                      <span
                        key={a}
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{
                          fontFamily: "var(--font-mono)",
                          color: "var(--color-accent)",
                          background: "var(--color-accent-dim)",
                        }}
                      >
                        {a}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* DAG visualization */}
      {run.execution && (
        <div>
          <h2
            className="text-xs font-medium mb-3 uppercase tracking-wider"
            style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}
          >
            Execution DAG
          </h2>
          <div
            className="rounded-lg px-5 py-4"
            style={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
            }}
          >
            <DagStages stages={run.execution.stages} statusMap={statusMap} />
          </div>
        </div>
      )}
    </div>
  );
}
