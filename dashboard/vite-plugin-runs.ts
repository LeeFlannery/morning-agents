import type { Plugin } from "vite";
import fs from "node:fs";
import path from "node:path";

const RUNS_DIR = path.resolve(__dirname, "../runs");

export function runsPlugin(): Plugin {
  return {
    name: "morning-agents-runs",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url === "/api/runs") {
          if (!fs.existsSync(RUNS_DIR)) {
            res.setHeader("Content-Type", "application/json");
            res.end("[]");
            return;
          }

          const files = fs
            .readdirSync(RUNS_DIR)
            .filter((f) => f.startsWith("brief-") && f.endsWith(".json"))
            .sort()
            .reverse();

          const manifest = files.map((f) => {
            const raw = JSON.parse(
              fs.readFileSync(path.join(RUNS_DIR, f), "utf-8")
            );
            return {
              id: raw.briefing_id,
              file: f,
              generated_at: raw.generated_at,
              duration_ms: raw.duration_ms,
              agents_run: raw.summary?.agents_run ?? 0,
              agents_succeeded: raw.summary?.agents_succeeded ?? 0,
              agents_failed: raw.summary?.agents_failed ?? 0,
              total_findings: raw.summary?.total_findings ?? 0,
              by_severity: raw.summary?.by_severity ?? {},
              cross_reference_count: raw.cross_references?.length ?? 0,
            };
          });

          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(manifest));
          return;
        }

        const match = req.url?.match(/^\/api\/runs\/(.+\.json)$/);
        if (match) {
          const filepath = path.join(RUNS_DIR, match[1]);
          if (filepath.startsWith(RUNS_DIR) && fs.existsSync(filepath)) {
            res.setHeader("Content-Type", "application/json");
            res.end(fs.readFileSync(filepath, "utf-8"));
            return;
          }
          res.statusCode = 404;
          res.end("Not found");
          return;
        }

        next();
      });
    },
  };
}
