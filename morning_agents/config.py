from mcp import StdioServerParameters

HOMEBREW_MCP = StdioServerParameters(
    command="bun",
    args=["run", "mcp-servers/homebrew-mcp/index.ts"],
)

MODEL = "claude-sonnet-4-6"

SERVER_REGISTRY: dict[str, StdioServerParameters] = {
    "homebrew-mcp": HOMEBREW_MCP,
    # "devenv-mcp": ...,
    # "github-mcp": ...,
}
