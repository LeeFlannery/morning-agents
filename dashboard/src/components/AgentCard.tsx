import { useState } from "react";
import type { AgentResult } from "../schemas";
import { StatusIndicator } from "./StatusIndicator";
import { FindingRow } from "./FindingRow";
import { SeverityBar } from "./SeverityBar";

function fmtMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function AgentCard({ result }: { result: AgentResult }) {
  const [toolsOpen, setToolsOpen] = useState(false);
  const isError = result.status === "error";

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{
        background: "var(--color-surface)",
        border: `1px solid ${isError ? "var(--color-error)40" : "var(--color-border)"}`,
      }}
    >
      {/* Card header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: isError ? "var(--color-error)20" : "var(--color-border)" }}
      >
        <div className="flex items-center gap-3">
          <span
            className="text-sm font-medium"
            style={{ color: "var(--color-text-primary)" }}
          >
            {result.agent_display_name}
          </span>
          <StatusIndicator status={result.status} />
        </div>
        <div className="flex items-center gap-4">
          {result.summary && (
            <SeverityBar bySeverity={result.summary.by_severity} />
          )}
          <span
            className="text-xs"
            style={{
              fontFamily: "var(--font-mono)",
              color: "var(--color-text-muted)",
            }}
          >
            {fmtMs(result.duration_ms)}
          </span>
        </div>
      </div>

      {/* Error state */}
      {isError && (
        <div
          className="px-4 py-3 text-sm"
          style={{ color: "var(--color-error)" }}
        >
          {result.error ?? "Unknown error"}
        </div>
      )}

      {/* Findings */}
      {!isError && result.findings.length > 0 && (
        <div className="py-1 px-1">
          {result.findings.map((f) => (
            <FindingRow key={f.id} finding={f} />
          ))}
        </div>
      )}

      {!isError && result.findings.length === 0 && (
        <div
          className="px-4 py-3 text-sm"
          style={{ color: "var(--color-text-muted)" }}
        >
          No findings
        </div>
      )}

      {/* Tool calls (collapsible) */}
      {result.tool_calls.length > 0 && (
        <div
          className="border-t"
          style={{ borderColor: "var(--color-border-subtle)" }}
        >
          <button
            onClick={() => setToolsOpen((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-2 text-xs transition-colors"
            style={{
              color: "var(--color-text-muted)",
              background: "transparent",
              cursor: "pointer",
              border: "none",
            }}
          >
            <span style={{ fontFamily: "var(--font-mono)" }}>
              {result.tool_calls.length} tool call
              {result.tool_calls.length !== 1 ? "s" : ""}
            </span>
            <span style={{ transform: toolsOpen ? "rotate(180deg)" : "none" }}>
              ▾
            </span>
          </button>

          {toolsOpen && (
            <div className="px-4 pb-3">
              <table className="w-full text-xs" style={{ fontFamily: "var(--font-mono)" }}>
                <thead>
                  <tr style={{ color: "var(--color-text-muted)" }}>
                    <th className="text-left pb-1 font-normal">tool</th>
                    <th className="text-left pb-1 font-normal">server</th>
                    <th className="text-right pb-1 font-normal">ms</th>
                    <th className="text-right pb-1 font-normal">ok</th>
                  </tr>
                </thead>
                <tbody>
                  {result.tool_calls.map((tc, i) => (
                    <tr
                      key={i}
                      style={{ color: "var(--color-text-secondary)", borderTop: "1px solid var(--color-border-subtle)" }}
                    >
                      <td className="py-1 pr-4">{tc.tool}</td>
                      <td className="py-1 pr-4" style={{ color: "var(--color-text-muted)" }}>
                        {tc.server}
                      </td>
                      <td className="py-1 text-right">{tc.duration_ms}</td>
                      <td
                        className="py-1 text-right"
                        style={{
                          color: tc.success
                            ? "var(--color-success)"
                            : "var(--color-error)",
                        }}
                      >
                        {tc.success ? "✓" : "✗"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
