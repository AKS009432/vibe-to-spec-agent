from unittest.mock import patch, MagicMock
import urllib.error
import json

from app.agent import read_github_repo


def make_mock_response(content_bytes: bytes) -> MagicMock:
    mock = MagicMock()
    mock.read.return_value = content_bytes
    mock.__enter__.return_value = mock
    return mock


def test_read_github_repo_success() -> None:
    # Mock responses for:
    # 1. Repository metadata request
    # 2. Repository tree recursive list request
    # 3. README.md file content request
    # 4. main.py file content request
    mock_responses = [
        make_mock_response(json.dumps({"default_branch": "main"}).encode('utf-8')),
        make_mock_response(json.dumps({
            "tree": [
                {"path": "README.md", "type": "blob"},
                {"path": "src/main.py", "type": "blob"},
                {"path": "data.json", "type": "blob"}
            ]
        }).encode('utf-8')),
        make_mock_response(b"This is the README content"),
        make_mock_response(b"print('hello world')")
    ]
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = mock_responses
        
        result = read_github_repo("https://github.com/myowner/myrepo")
        
        assert mock_urlopen.call_count == 4
        assert "=== File: README.md ===" in result
        assert "This is the README content" in result
        assert "=== File: src/main.py ===" in result
        assert "print('hello world')" in result
        assert "data.json" not in result


def test_read_github_repo_invalid_url() -> None:
    result = read_github_repo("https://not-github.com/owner/repo")
    assert "Invalid GitHub URL" in result


def test_read_github_repo_not_found() -> None:
    err = urllib.error.HTTPError(
        url="https://api.github.com/repos/owner/repo",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None
    )
    with patch("urllib.request.urlopen", side_effect=err):
        result = read_github_repo("https://github.com/owner/repo")
        assert "Repository not found or is private" in result
        assert "HTTP 404" in result
