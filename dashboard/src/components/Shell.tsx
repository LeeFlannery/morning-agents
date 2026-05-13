import { Link } from "@tanstack/react-router";

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--color-base)" }}>
      {/* Top bar */}
      <header
        className="sticky top-0 z-50 flex items-center justify-between px-6 py-3 border-b"
        style={{
          background: "var(--color-surface)",
          borderColor: "var(--color-border)",
        }}
      >
        <Link
          to="/"
          className="flex items-center gap-3 no-underline"
          style={{ textDecoration: "none" }}
        >
          <span
            className="text-base font-semibold tracking-tight"
            style={{ color: "var(--color-text-primary)", fontFamily: "var(--font-sans)" }}
          >
            Morning Agents
          </span>
          <span
            className="text-xs px-1.5 py-0.5 rounded"
            style={{
              fontFamily: "var(--font-mono)",
              color: "var(--color-text-muted)",
              background: "var(--color-surface-2)",
              border: "1px solid var(--color-border)",
            }}
          >
            v0.1.002
          </span>
        </Link>

        <nav className="flex items-center gap-6">
          <Link
            to="/"
            className="text-sm no-underline transition-colors"
            style={{ color: "var(--color-text-secondary)", textDecoration: "none" }}
            activeProps={{ style: { color: "var(--color-text-primary)" } }}
          >
            Runs
          </Link>
          <a
            href="https://leeflannery.github.io/morning-agents/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm no-underline transition-colors"
            style={{ color: "var(--color-text-secondary)", textDecoration: "none" }}
          >
            Docs ↗
          </a>
        </nav>
      </header>

      {/* Main content */}
      <main className="flex-1 px-6 py-6 max-w-6xl mx-auto w-full">{children}</main>
    </div>
  );
}
