import os
from mcp.server.fastmcp import FastMCP
from app.agent import read_github_repo

# Initialize the FastMCP server
mcp = FastMCP("github-repo-server", host="127.0.0.1", port=8081)

@mcp.tool(
    name="read_github_repo",
    description="Reads all Python files (.py) and the README.md from the provided public GitHub repository URL."
)
def read_github_repo_tool(url: str) -> str:
    """Reads all Python files (.py) and the README.md from the provided public GitHub repository URL.

    Args:
        url: The public GitHub repository URL (e.g., https://github.com/owner/repo)
    """
    return read_github_repo(url)

if __name__ == "__main__":
    print("[MCP Server] Starting on http://127.0.0.1:8081")
    mcp.run("sse")
