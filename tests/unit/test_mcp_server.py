import pytest
from unittest.mock import patch
from app.mcp_server import mcp

@pytest.mark.asyncio
async def test_mcp_server_lists_tool() -> None:
    # Get the list of tools from the FastMCP server
    tools = await mcp.list_tools()
    
    # Verify that 'read_github_repo' is in the registered tools
    tool_names = [tool.name for tool in tools]
    assert "read_github_repo" in tool_names

    # Find the specific tool and verify its details
    target_tool = next(t for t in tools if t.name == "read_github_repo")
    assert target_tool.description is not None
    assert "Reads all Python files" in target_tool.description

@pytest.mark.asyncio
async def test_mcp_server_calls_tool() -> None:
    # Mock read_github_repo to return a dummy string
    with patch("app.mcp_server.read_github_repo") as mock_read:
        mock_read.return_value = "Mocked Repository Content"
        
        # Call the tool via FastMCP's call_tool
        result = await mcp.call_tool("read_github_repo", arguments={"url": "https://github.com/owner/repo"})
        
        # Verify call was routed correctly to the underlying function
        mock_read.assert_called_once_with("https://github.com/owner/repo")
        assert len(result) > 0
        assert result[0][0].text == "Mocked Repository Content"
