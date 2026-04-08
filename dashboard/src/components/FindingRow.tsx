import { useState } from "react";
import type { Finding } from "../schemas";
import { SeverityBadge } from "./SeverityBadge";

export function FindingRow({
  finding,
  defaultExpanded = false,
}: {
  finding: Finding;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const url = finding.metadata?.url as string | undefined;

  return (
    <div className="group">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-start gap-3 py-2 px-3 rounded text-left transition-colors"
        style={{
          background: expanded ? "var(--color-surface-2)" : "transparent",
        }}
        onMouseEnter={(e) =>
          !expanded &&
          ((e.currentTarget as HTMLElement).style.background =
            "var(--color-hover)")
        }
        onMouseLeave={(e) =>
          !expanded &&
          ((e.currentTarget as HTMLElement).style.background = "transparent")
        }
      >
        <SeverityBadge severity={finding.severity} />
        <div className="flex-1 min-w-0">
          <div
            className="text-sm leading-snug"
            style={{ color: "var(--color-text-primary)" }}
          >
            {finding.title}
          </div>
          {expanded && finding.detail && (
            <div
              className="mt-1.5 text-xs leading-relaxed"
              style={{ color: "var(--color-text-secondary)" }}
            >
              {finding.detail}
              {url && (
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-2 inline-flex items-center gap-0.5"
                  style={{ color: "var(--color-accent)", textDecoration: "none" }}
                  onClick={(e) => e.stopPropagation()}
                >
                  view ↗
                </a>
              )}
            </div>
          )}
        </div>
        <span
          className="text-xs mt-0.5 shrink-0 transition-transform"
          style={{
            color: "var(--color-text-muted)",
            transform: expanded ? "rotate(90deg)" : "none",
          }}
        >
          ›
        </span>
      </button>
    </div>
  );
}
