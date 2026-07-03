@echo off
echo Starting vibe-to-spec-agent...

if "%GOOGLE_API_KEY%"=="" (
    echo WARNING: GOOGLE_API_KEY environment variable is not set.
)
if "%GITHUB_TOKEN%"=="" (
    echo WARNING: GITHUB_TOKEN environment variable is not set.
)

echo Starting MCP server in background...
start /b uv run python app/mcp_server.py

echo Starting ADK web server...
uv run adk web app --host 127.0.0.1 --port 8080
