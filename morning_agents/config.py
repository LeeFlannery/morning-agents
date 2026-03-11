import os

from mcp import StdioServerParameters

HOMEBREW_MCP = StdioServerParameters(
    command="bun",
    args=["run", "mcp-servers/homebrew-mcp/index.ts"],
)

DEVENV_MCP = StdioServerParameters(
    command="bun",
    args=["run", "mcp-servers/devenv-mcp/index.ts"],
)

GITHUB_MCP = StdioServerParameters(
    command="github-mcp-server",
    args=["stdio"],
    env={
        "GITHUB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITHUB_TOKEN", ""),
        "GITHUB_READ_ONLY": "1",
        "GITHUB_TOOLSETS": "pull_requests,notifications",
    },
)

MODEL = "claude-sonnet-4-6"
VERSION = "0.1.0"

SERVER_REGISTRY: dict[str, StdioServerParameters] = {
    "homebrew-mcp": HOMEBREW_MCP,
    "devenv-mcp": DEVENV_MCP,
    "github-mcp": GITHUB_MCP,
}
