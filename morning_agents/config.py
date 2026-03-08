from mcp import StdioServerParameters

HOMEBREW_MCP = StdioServerParameters(
    command="bun",
    args=["run", "mcp-servers/homebrew-mcp/index.ts"],
)

MODEL = "claude-sonnet-4-6"
