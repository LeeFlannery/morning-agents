import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "spike-mcp",
  version: "0.1.0",
});

server.tool(
  "hello",
  "Say hello with a name",
  { name: z.string().describe("Name to greet") },
  async ({ name }) => ({
    content: [{ type: "text", text: `Hello from TypeScript MCP, ${name}! The bridge works.` }],
  })
);

server.tool(
  "add",
  "Add two numbers",
  { a: z.number(), b: z.number() },
  async ({ a, b }) => ({
    content: [{ type: "text", text: String(a + b) }],
  })
);

const transport = new StdioServerTransport();
await server.connect(transport);
