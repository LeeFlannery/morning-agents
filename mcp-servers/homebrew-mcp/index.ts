import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "homebrew-mcp",
  version: "0.1.0",
});

async function brewExec(args: string[]): Promise<{ stdout: string; stderr: string }> {
  const proc = Bun.spawn(["brew", ...args], {
    env: { ...process.env, PATH: "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" },
    stderr: "pipe",
  });

  const [stdout, stderr] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
  ]);

  await proc.exited;
  return { stdout, stderr };
}

// ─── list_outdated ────────────────────────────────────────────────────────────

server.tool(
  "list_outdated",
  "List all outdated Homebrew formulae and casks",
  {},
  async () => {
    const { stdout, stderr } = await brewExec(["outdated", "--json=v2"]);

    if (!stdout.trim()) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({ error: "brew not available or no output", stderr }),
        }],
      };
    }

    let parsed: { formulae?: any[]; casks?: any[] };
    try {
      parsed = JSON.parse(stdout);
    } catch {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({ error: "Failed to parse brew output", raw: stdout }),
        }],
      };
    }

    const formulae = (parsed.formulae ?? []).map((f: any) => ({
      name: f.name,
      current: f.installed_versions?.[0] ?? "unknown",
      latest: f.current_version,
      pinned: f.pinned ?? false,
    }));

    const casks = (parsed.casks ?? []).map((c: any) => ({
      name: c.name,
      current: c.installed_versions?.[0] ?? "unknown",
      latest: c.current_version,
    }));

    return {
      content: [{
        type: "text",
        text: JSON.stringify({ formulae, casks }),
      }],
    };
  }
);

// ─── get_package_info ─────────────────────────────────────────────────────────

server.tool(
  "get_package_info",
  "Get details about a specific Homebrew package",
  { name: z.string().describe("Package name (formula or cask)") },
  async ({ name }) => {
    const { stdout, stderr } = await brewExec(["info", "--json=v2", name]);

    if (!stdout.trim()) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({ error: `Package '${name}' not found or brew unavailable`, stderr }),
        }],
      };
    }

    let parsed: { formulae?: any[]; casks?: any[] };
    try {
      parsed = JSON.parse(stdout);
    } catch {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({ error: "Failed to parse brew info output", raw: stdout }),
        }],
      };
    }

    const item = parsed.formulae?.[0] ?? parsed.casks?.[0];
    if (!item) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({ error: `No info found for '${name}'` }),
        }],
      };
    }

    const info = {
      name: item.name ?? item.token,
      version: item.versions?.stable ?? item.version ?? "unknown",
      desc: item.desc ?? "",
      homepage: item.homepage ?? "",
      dependencies: item.dependencies ?? [],
      installed_on: item.installed?.[0]?.installed_on_request
        ? item.installed[0].built_as_bottle
          ? "bottle"
          : "source"
        : null,
    };

    return {
      content: [{ type: "text", text: JSON.stringify(info) }],
    };
  }
);

// ─── get_doctor_status ────────────────────────────────────────────────────────

server.tool(
  "get_doctor_status",
  "Run brew doctor and return health warnings",
  {},
  async () => {
    const { stdout, stderr } = await brewExec(["doctor"]);
    const combined = (stdout + "\n" + stderr).trim();
    const healthy = combined.includes("Your system is ready to brew");

    const warnings: string[] = [];
    const lines = combined.split("\n");
    let currentWarning: string[] = [];

    for (const line of lines) {
      if (line.startsWith("Warning:")) {
        if (currentWarning.length > 0) warnings.push(currentWarning.join("\n").trim());
        currentWarning = [line];
      } else if (currentWarning.length > 0 && line.trim() !== "") {
        currentWarning.push(line);
      } else if (currentWarning.length > 0 && line.trim() === "") {
        warnings.push(currentWarning.join("\n").trim());
        currentWarning = [];
      }
    }
    if (currentWarning.length > 0) warnings.push(currentWarning.join("\n").trim());

    return {
      content: [{
        type: "text",
        text: JSON.stringify({ healthy, warnings }),
      }],
    };
  }
);

// ─── Start server ─────────────────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);
