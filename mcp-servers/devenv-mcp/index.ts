import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new McpServer({
  name: "devenv-mcp",
  version: "0.1.0",
});

const ENV = { ...process.env, PATH: "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" };

async function spawnCmd(cmd: string, args: string[]): Promise<{ stdout: string; stderr: string; ok: boolean }> {
  const proc = Bun.spawn([cmd, ...args], { env: ENV, stderr: "pipe" });
  const [stdout, stderr] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
  ]);
  const code = await proc.exited;
  return { stdout: stdout.trim(), stderr: stderr.trim(), ok: code === 0 };
}

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, {
      headers: { "User-Agent": "morning-agents/0.1.0" },
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) return null;
    return await res.json() as T;
  } catch {
    return null;
  }
}

// ─── check_xcode_version ──────────────────────────────────────────────────────

server.tool(
  "check_xcode_version",
  "Check installed vs latest Xcode and CLI Tools status",
  {},
  async () => {
    const [xcodeResult, selectResult, xcodeData] = await Promise.all([
      spawnCmd("xcodebuild", ["-version"]),
      spawnCmd("xcode-select", ["-p"]),
      fetchJson<Array<{ version: { release: { release: boolean }; number: string } }>>(
        "https://xcodereleases.com/data.json"
      ),
    ]);

    let installed = "not_installed";
    if (xcodeResult.ok) {
      const match = xcodeResult.stdout.match(/Xcode\s+(\S+)/);
      if (match) installed = match[1];
    }

    let latest = "unknown";
    if (xcodeData) {
      const stable = xcodeData.find((entry) => entry.version?.release?.release === true);
      if (stable?.version?.number) latest = stable.version.number;
    }

    const cli_tools_installed = selectResult.ok && selectResult.stdout.length > 0;

    return {
      content: [{ type: "text", text: JSON.stringify({ installed, latest, cli_tools_installed }) }],
    };
  }
);

// ─── check_vscode_version ─────────────────────────────────────────────────────

server.tool(
  "check_vscode_version",
  "Check installed vs latest VS Code",
  {},
  async () => {
    const [codeResult, release] = await Promise.all([
      spawnCmd("code", ["--version"]),
      fetchJson<{ tag_name: string }>(
        "https://api.github.com/repos/microsoft/vscode/releases/latest"
      ),
    ]);

    let installed = "not_installed";
    if (codeResult.ok) {
      const firstLine = codeResult.stdout.split("\n")[0].trim();
      if (firstLine) installed = firstLine;
    }

    const latest = release?.tag_name ?? "unknown";

    return {
      content: [{ type: "text", text: JSON.stringify({ installed, latest }) }],
    };
  }
);

// ─── check_node_version ───────────────────────────────────────────────────────

server.tool(
  "check_node_version",
  "Check installed vs latest LTS Node.js",
  {},
  async () => {
    const [nodeResult, releases] = await Promise.all([
      spawnCmd("node", ["--version"]),
      fetchJson<Array<{ version: string; lts: string | false }>>(
        "https://nodejs.org/dist/index.json"
      ),
    ]);

    let installed = "not_installed";
    if (nodeResult.ok) {
      installed = nodeResult.stdout.replace(/^v/, "");
    }

    let latest_lts = "unknown";
    if (releases) {
      const lts = releases.find((r) => r.lts !== false);
      if (lts) latest_lts = lts.version.replace(/^v/, "");
    }

    return {
      content: [{ type: "text", text: JSON.stringify({ installed, latest_lts }) }],
    };
  }
);

// ─── check_python_version ─────────────────────────────────────────────────────

server.tool(
  "check_python_version",
  "Check installed vs latest Python 3",
  {},
  async () => {
    const [pyResult, eolData] = await Promise.all([
      spawnCmd("python3", ["--version"]),
      fetchJson<Array<{ cycle: string; latest: string; eol: string }>>(
        "https://endoflife.date/api/python.json"
      ),
    ]);

    let installed = "not_installed";
    if (pyResult.ok) {
      const match = pyResult.stdout.match(/Python\s+(\S+)/);
      if (match) installed = match[1];
    }

    let latest = "unknown";
    if (eolData && eolData.length > 0) {
      const now = new Date();
      const active = eolData.filter((e) => new Date(e.eol) > now);
      if (active.length > 0) latest = active[0].latest;
    }

    return {
      content: [{ type: "text", text: JSON.stringify({ installed, latest }) }],
    };
  }
);

// ─── Start server ─────────────────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);
