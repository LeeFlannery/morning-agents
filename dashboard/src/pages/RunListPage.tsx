import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useRunManifest } from "../api";
import { SeverityBar } from "../components/SeverityBar";
import { fmtDate, fmtDuration } from "../utils";
import type { RunManifestEntry } from "../schemas";

export function RunListPage() {
  const { data: runs, isLoading, error } = useRunManifest();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggleSelect = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else if (next.size < 2) {
        next.add(id);
      }
      return next;
    });
  };

  const handleCompare = () => {
    const [a, b] = [...selected];
    navigate({ to: "/diff", search: { a, b } });
  };

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center py-24 text-sm"
        style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}
      >
        loading runs...
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="py-24 text-center text-sm"
        style={{ color: "var(--color-error)" }}
      >
        Failed to load runs: {String(error)}
      </div>
    );
  }

  if (!runs || runs.length === 0) {
    return (
      <div className="py-24 text-center">
        <div
          className="text-sm mb-3"
          style={{ color: "var(--color-text-muted)" }}
        >
          No briefing runs found.
        </div>
        <div
          className="text-xs"
          style={{
            fontFamily: "var(--font-mono)",
            color: "var(--color-text-muted)",
          }}
        >
          Run{" "}
          <code
            className="px-1.5 py-0.5 rounded"
            style={{
              background: "var(--color-surface-2)",
              color: "var(--color-text-secondary)",
            }}
          >
            morning-agents
          </code>{" "}
          to generate your first briefing.
        </div>
      </div>
    );
  }

  // Check if any run has cross-references
  const hasXrefs = runs.some((r) => r.cross_reference_count > 0);

  return (
    <div>
      {/* Page header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1
            className="text-lg font-semibold m-0"
            style={{ color: "var(--color-text-primary)" }}
          >
            Briefing History
          </h1>
          <p
            className="text-xs mt-0.5"
            style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}
          >
            {runs.length} run{runs.length !== 1 ? "s" : ""}
          </p>
        </div>

        {selected.size === 2 && (
          <button
            onClick={handleCompare}
            className="flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-colors"
            style={{
              background: "var(--color-accent)",
              color: "#fff",
              border: "none",
              cursor: "pointer",
            }}
          >
            Compare selected →
          </button>
        )}
        {selected.size === 1 && (
          <p
            className="text-xs"
            style={{ color: "var(--color-text-muted)" }}
          >
            Select one more to compare
          </p>
        )}
      </div>

      {/* Table */}
      <div
        className="rounded-lg overflow-hidden"
        style={{ border: "1px solid var(--color-border)" }}
      >
        <table className="w-full border-collapse">
          <thead>
            <tr
              style={{
                background: "var(--color-surface)",
                borderBottom: "1px solid var(--color-border)",
              }}
            >
              <th className="w-8 px-4 py-3" />
              <th
                className="text-left px-4 py-3 text-xs font-medium"
                style={{
                  color: "var(--color-text-muted)",
                  fontFamily: "var(--font-mono)",
                  letterSpacing: "0.05em",
                }}
              >
                TIMESTAMP
              </th>
              <th
                className="text-left px-4 py-3 text-xs font-medium"
                style={{
                  color: "var(--color-text-muted)",
                  fontFamily: "var(--font-mono)",
                  letterSpacing: "0.05em",
                }}
              >
                AGENTS
              </th>
              <th
                className="text-left px-4 py-3 text-xs font-medium"
                style={{
                  color: "var(--color-text-muted)",
                  fontFamily: "var(--font-mono)",
                  letterSpacing: "0.05em",
                }}
              >
                FINDINGS
              </th>
              {hasXrefs && (
                <th
                  className="text-left px-4 py-3 text-xs font-medium"
                  style={{
                    color: "var(--color-text-muted)",
                    fontFamily: "var(--font-mono)",
                    letterSpacing: "0.05em",
                  }}
                >
                  X-REFS
                </th>
              )}
              <th
                className="text-right px-4 py-3 text-xs font-medium"
                style={{
                  color: "var(--color-text-muted)",
                  fontFamily: "var(--font-mono)",
                  letterSpacing: "0.05em",
                }}
              >
                DURATION
              </th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run: RunManifestEntry, i: number) => {
              const isSelected = selected.has(run.id);
              const hasFailed = run.agents_failed > 0;

              return (
                <tr
                  key={run.id}
                  onClick={() =>
                    navigate({ to: "/run/$runId", params: { runId: run.id } })
                  }
                  className="cursor-pointer transition-colors"
                  style={{
                    background: isSelected
                      ? "var(--color-accent-dim)"
                      : i % 2 === 0
                      ? "var(--color-surface)"
                      : "transparent",
                    borderTop: "1px solid var(--color-border-subtle)",
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected)
                      (e.currentTarget as HTMLElement).style.background =
                        "var(--color-hover)";
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected)
                      (e.currentTarget as HTMLElement).style.background =
                        i % 2 === 0
                          ? "var(--color-surface)"
                          : "transparent";
                  }}
                >
                  {/* Checkbox */}
                  <td className="px-4 py-3" onClick={(e) => toggleSelect(run.id, e)}>
                    <div
                      className="w-4 h-4 rounded flex items-center justify-center"
                      style={{
                        border: `1px solid ${isSelected ? "var(--color-accent)" : "var(--color-border)"}`,
                        background: isSelected ? "var(--color-accent)" : "transparent",
                      }}
                    >
                      {isSelected && (
                        <span className="text-white text-xs leading-none">✓</span>
                      )}
                    </div>
                  </td>

                  {/* Timestamp */}
                  <td className="px-4 py-3">
                    <span
                      className="text-xs"
                      style={{
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-text-secondary)",
                      }}
                    >
                      {fmtDate(run.generated_at)}
                    </span>
                  </td>

                  {/* Agents */}
                  <td className="px-4 py-3">
                    <span
                      className="text-xs"
                      style={{
                        fontFamily: "var(--font-mono)",
                        color: hasFailed ? "var(--color-error)" : "var(--color-text-secondary)",
                      }}
                    >
                      {run.agents_succeeded}/{run.agents_run}
                      {hasFailed && (
                        <span
                          className="ml-2"
                          style={{ color: "var(--color-error)" }}
                        >
                          {run.agents_failed} failed
                        </span>
                      )}
                    </span>
                  </td>

                  {/* Findings */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <span
                        className="text-xs"
                        style={{
                          fontFamily: "var(--font-mono)",
                          color: "var(--color-text-secondary)",
                        }}
                      >
                        {run.total_findings}
                      </span>
                      <SeverityBar bySeverity={run.by_severity} />
                    </div>
                  </td>

                  {/* X-refs */}
                  {hasXrefs && (
                    <td className="px-4 py-3">
                      <span
                        className="text-xs"
                        style={{
                          fontFamily: "var(--font-mono)",
                          color:
                            run.cross_reference_count > 0
                              ? "var(--color-accent)"
                              : "var(--color-text-muted)",
                        }}
                      >
                        {run.cross_reference_count > 0
                          ? run.cross_reference_count
                          : "—"}
                      </span>
                    </td>
                  )}

                  {/* Duration */}
                  <td className="px-4 py-3 text-right">
                    <span
                      className="text-xs"
                      style={{
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-text-muted)",
                      }}
                    >
                      {fmtDuration(run.duration_ms)}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {selected.size > 0 && selected.size < 2 && (
        <p
          className="mt-3 text-xs text-center"
          style={{ color: "var(--color-text-muted)" }}
        >
          Select 2 runs to enable comparison
        </p>
      )}
    </div>
  );
}
