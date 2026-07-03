# ruff: noqa
# Vibe-to-Spec Agent — Capstone Project
# Google 5-Day AI Agents Intensive (June 2026)
#
# Audits vibe-coded agents and generates:
#   - Living SPEC.md (intent vs implementation)
#   - Gap report with 7-pillar security check
#   - Eval rubric with test cases and trajectory checks

import os
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

import datetime
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.google_llm import Gemini
from google.adk.tools import LongRunningFunctionTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams


# ── Tools ────────────────────────────────────────────────────────────────────

def read_github_repo(github_url: str) -> str:
    """Fetches README.md and all Python (.py) files from a GitHub repository.

    Args:
        github_url: The URL of the GitHub repository.

    Returns:
        The combined contents of README.md and all .py files in the repository.
    """
    # Validate GitHub URL domain and structure
    url_lower = github_url.lower().strip()
    temp = url_lower
    for prefix in ["https://", "http://", "www."]:
        if temp.startswith(prefix):
            temp = temp[len(prefix):]
    if not temp.startswith("github.com/"):
        return "Error: Invalid GitHub URL. Please provide a valid GitHub repository URL."

    # Parse repository owner and name from URL
    match = re.search(r"github\.com/([^/]+)/([^/]+)", github_url, re.IGNORECASE)
    if not match:
        return "Error: Invalid GitHub URL. Please provide a valid GitHub repository URL."
    
    owner = match.group(1)
    repo = match.group(2)
    if repo.endswith(".git"):
        repo = repo[:-4]

    token = os.environ.get("GITHUB_TOKEN")
    
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Vibe-To-Spec-Agent"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        # Get repository details to find default branch
        repo_url = f"https://api.github.com/repos/{owner}/{repo}"
        req = urllib.request.Request(repo_url, headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            repo_data = json.loads(response.read().decode('utf-8'))
        default_branch = repo_data.get("default_branch", "main")
    except urllib.error.HTTPError as e:
        if e.code in (404, 403):
            return f"Error: Repository not found or is private. Please ensure a valid GITHUB_TOKEN is configured. (HTTP {e.code})"
        return f"Error accessing repository metadata: {e.reason} (HTTP {e.code})"
    except Exception as e:
        return f"Error accessing repository: {str(e)}"

    try:
        # Get directory tree recursively
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        req = urllib.request.Request(tree_url, headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            tree_data = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return f"Error fetching repository file tree: {str(e)}"

    files_to_fetch = []
    readme_path = None

    for item in tree_data.get("tree", []):
        if item.get("type") == "blob":
            path = item.get("path", "")
            if path.lower() == "readme.md":
                readme_path = path
            elif path.endswith(".py"):
                files_to_fetch.append(path)

    if readme_path:
        files_to_fetch.insert(0, readme_path)

    if not files_to_fetch:
        return "Repository is empty or does not contain README.md or any .py files."

    combined_contents = []
    for path in files_to_fetch:
        # Fetch individual file raw content
        quoted_path = urllib.parse.quote(path, safe='/')
        file_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{quoted_path}?ref={default_branch}"
        
        file_headers = {
            "Accept": "application/vnd.github.raw",
            "User-Agent": "Vibe-To-Spec-Agent"
        }
        if token:
            file_headers["Authorization"] = f"Bearer {token}"
            
        try:
            file_req = urllib.request.Request(file_url, headers=file_headers)
            with urllib.request.urlopen(file_req, context=ssl_context) as response:
                content = response.read().decode('utf-8', errors='replace')
            combined_contents.append(f"=== File: {path} ===\n{content}\n")
        except Exception as e:
            combined_contents.append(f"=== File: {path} ===\n[Error fetching file content: {str(e)}]\n")

    return "\n".join(combined_contents)


def read_project(input: str) -> str:
    """Reads and summarises a vibe-coded project from a URL or description.

    Args:
        input: GitHub URL, Kaggle notebook URL, or plain text description
               of the agent/project to audit.

    Returns:
        A structured summary of what the code does.
    """
    return f"""PROJECT INPUT RECEIVED:
{input}

[Code Reader Analysis]
- Input type: {'URL' if input.startswith('http') else 'Description'}
- Content: {input[:200]}...
- Status: Ready for intent interview
"""


def request_intent_interview(project_summary: str) -> dict:
    """Presents 5 targeted questions to the builder. Human-in-the-loop gate.
    Pauses execution until the builder responds with their answers.

    Args:
        project_summary: Summary of the project from read_project tool.

    Returns:
        Pending status with the 5 interview questions.
    """
    questions = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  INTENT INTERVIEW — Human-in-the-Loop Gate
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I've analysed your project. Now I need your intent.
Please answer all 5 questions:

Q1. GOAL: What did you want this agent to achieve?

Q2. AUDIENCE: Who will use this?
    (developer / end-user / enterprise team)

Q3. CRITICAL ACTION: What is the most dangerous
    thing this agent can do?

Q4. SUCCESS: How do you define success for this agent?

Q5. KNOWN GAPS: What do you already know is
    missing or broken?

Reply in this exact format:
A1: ...
A2: ...
A3: ...
A4: ...
A5: ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return {"status": "pending", "message": questions}


def extract_repo_name(repo_name_or_url: str) -> str:
    """Helper to extract repository name from GitHub URL or description."""
    text = repo_name_or_url.strip()
    match = re.search(r"github\.com/([^/]+)/([^/]+)", text, re.IGNORECASE)
    if match:
        name = match.group(2)
        if name.endswith(".git"):
            name = name[:-4]
        if "/" in name:
            name = name.split("/")[0]
        return re.sub(r"[^a-zA-Z0-9_\-]", "", name)
    
    words = re.findall(r"\w+", text)
    if words:
        name = "_".join(words[:3])
        return re.sub(r"[^a-zA-Z0-9_\-]", "", name).lower()
    return "project"


def save_report(repo_name_or_url: str, report_content: str) -> str:
    """Saves the generated Quick Scan findings report to a markdown file inside the audit_reports/quick_scan folder.

    Args:
        repo_name_or_url: The GitHub URL or project description to extract the repo name.
        report_content: The markdown content of the generated scan report.

    Returns:
        A confirmation message indicating that the report has been successfully saved.
    """
    try:
        repo_name = extract_repo_name(repo_name_or_url)
        ddmmyy = datetime.datetime.now().strftime("%d%m%y")
        
        folder = os.path.join("audit_reports", "quick_scan")
        os.makedirs(folder, exist_ok=True)
        
        filename = f"{repo_name}_{ddmmyy}_scan.md"
        filepath = os.path.join(folder, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_content)
        return f"Success: Quick Scan report has been saved to {filepath}."
    except Exception as e:
        return f"Error saving report: {str(e)}"


def save_deep_audit_report(repo_name_or_url: str, spec_content: str, gap_report_content: str, eval_rubric_content: str) -> str:
    """Saves the generated SPEC.md, GAP_REPORT.md, and EVAL_RUBRIC.md contents as separate files in the audit_reports/deep_audit folder.

    Args:
        repo_name_or_url: The GitHub URL or project description to extract the repo name.
        spec_content: The markdown content of the SPEC.md document.
        gap_report_content: The markdown content of the GAP_REPORT.md document.
        eval_rubric_content: The markdown content of the EVAL_RUBRIC.md document.

    Returns:
        A confirmation message indicating that all three reports have been successfully saved.
    """
    try:
        repo_name = extract_repo_name(repo_name_or_url)
        ddmmyy = datetime.datetime.now().strftime("%d%m%y")
        
        folder = os.path.join("audit_reports", "deep_audit")
        os.makedirs(folder, exist_ok=True)
        
        spec_path = os.path.join(folder, f"{repo_name}_{ddmmyy}_spec.md")
        gap_path = os.path.join(folder, f"{repo_name}_{ddmmyy}_gap_report.md")
        eval_path = os.path.join(folder, f"{repo_name}_{ddmmyy}_eval_rubric.md")
        
        with open(spec_path, "w", encoding="utf-8") as f:
            f.write(spec_content)
        with open(gap_path, "w", encoding="utf-8") as f:
            f.write(gap_report_content)
        with open(eval_path, "w", encoding="utf-8") as f:
            f.write(eval_rubric_content)
            
        return f"Success: Deep Audit reports have been successfully saved to {folder} as separate files."
    except Exception as e:
        return f"Error saving deep audit reports: {str(e)}"


if os.environ.get("GOOGLE_API_KEY"):
    gkey = os.environ.get("GOOGLE_API_KEY", "")
    print(f"[Model Selection] GOOGLE_API_KEY is set (len={len(gkey)}). Prefix: {gkey[:12] if len(gkey) >= 12 else gkey}...")
    gemkey = os.environ.get("GEMINI_API_KEY", "")
    if gemkey:
        print(f"[Model Selection] GEMINI_API_KEY is also set (len={len(gemkey)}). Prefix: {gemkey[:12] if len(gemkey) >= 12 else gemkey}...")
    
    # Always use Google AI Studio developer endpoint for key-based auth
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
    print("[Model Selection] Routing all requests to Google AI Studio endpoint (generativelanguage.googleapis.com).")

    # Disable default GCP credentials detection to prevent OAuth 401 errors
    try:
        import google.auth
        google.auth.default = lambda *args, **kwargs: (None, None)
        print("[Model Selection] Patched google.auth.default to prevent GCP credentials resolution.")
    except ImportError:
        pass

    # Debug headers by monkey-patching BaseApiClient
    try:
        from google.genai._api_client import BaseApiClient
        original_request_once = BaseApiClient._request_once
        original_async_request_once = BaseApiClient._async_request_once

        def patched_request_once(self, http_request, stream=False):
            print(f"[Debug Client Headers] Requesting URL: {http_request.url}")
            print(f"[Debug Client Headers] Headers: {dict(http_request.headers)}")
            return original_request_once(self, http_request, stream)

        async def patched_async_request_once(self, http_request, stream=False):
            print(f"[Debug Client Headers] Async Requesting URL: {http_request.url}")
            print(f"[Debug Client Headers] Async Headers: {dict(http_request.headers)}")
            return await original_async_request_once(self, http_request, stream)

        BaseApiClient._request_once = patched_request_once
        BaseApiClient._async_request_once = patched_async_request_once
        print("[Model Selection] Patched BaseApiClient to print headers.")
    except Exception as e:
        print("[Model Selection] Failed to patch BaseApiClient:", e)

    # Allow custom Gemini model name override, default to gemini-2.5-flash (modern stable model)
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    selected_model = Gemini(model=gemini_model)
    print(f"[Model] Gemini model initialized: {gemini_model}")
else:
    selected_model = LiteLlm(model="openai/gpt-4o-mini")
    print("[Model] OpenAI GPT-4o-mini")


# ── MCP Server Toolset ─────────────────────────────────────────────────────────

mcp_toolset = McpToolset(
    connection_params=SseConnectionParams(
        url="http://127.0.0.1:8081/sse"
    )
)

class DualToolSource(BaseToolset):
    def __init__(self, mcp_toolset, local_tool):
        super().__init__()
        self.mcp_toolset = mcp_toolset
        self.local_tool = local_tool

    async def get_tools(self, readonly_context=None):
        from google.adk.tools.function_tool import FunctionTool
        try:
            mcp_tools = await self.mcp_toolset.get_tools(readonly_context)
            if mcp_tools:
                print("[MCP] Successfully connected to MCP server. Using MCP tools.")
                return mcp_tools
        except Exception as e:
            print(f"[MCP] Could not connect to MCP server: {e}. Falling back to local tool.")
        return [FunctionTool(func=self.local_tool)]

github_tool_source = DualToolSource(mcp_toolset, read_github_repo)


# ── Root Agent ────────────────────────────────────────────────────────────────

root_agent = Agent(
    name="AKS009432",
    model=selected_model,
    description="Audits vibe-coded agents. Generates a living spec, gap report, and eval rubric.",
    instruction="""IMPORTANT: If the user's message starts with or contains the words 'deep audit', 'deep scan', or 'full audit', ALWAYS use MODE 2 regardless of whether a URL is present. Check for these keywords FIRST before checking for URLs.

CRITICAL RULE FOR TOOL EXECUTION: You MUST execute tool calls sequentially. NEVER call save_report() or save_deep_audit_report() in the same turn as read_github_repo() or read_project(). You must first call read_github_repo() or read_project(), wait for the execution results to load the codebase files into your history, perform your analysis, and then call save_report() or save_deep_audit_report() in a subsequent separate turn with the fully generated content.

You are the Vibe-to-Spec Agent. Analyze the user's input to automatically determine the audit mode:

- MODE 1: Quick Scan (Triggered when the user provides a GitHub URL, unless they explicitly say "deep audit" or request a deep audit).
  1. Call read_github_repo() with the GitHub URL.
  2. Skip the intent interview entirely (do NOT call request_intent_interview()).
  3. Analyze the repository files and generate a Quick Scan findings report.
     * Categorize findings as: CRITICAL / HIGH / MEDIUM / LOW.
     * For each gap include:
       - What it is (one line)
       - What it means in plain English
       - Real-world exploit scenario
       - Affected file and location (with path and line numbers)
  4. Call save_report() with the user's GitHub URL and the generated findings to write them to audit_reports/quick_scan folder.
  5. Present a summary of the report to the user and confirm it has been saved.

- MODE 2: Deep Audit (Triggered when the user explicitly says "deep audit", "deep", or provides a plain description/text input instead of a GitHub URL).
  1. If a GitHub URL is provided in the query, call read_github_repo() first, then call read_project() with the user's input. Otherwise, call read_project() with the user's input.
  2. Call request_intent_interview() and WAIT for A1-A5 answers.
  3. Using the project summary + intent answers, directly generate the full content for the following documents:
     * SPEC.md (a living specification of the agent mapping intent vs implementation)
     * GAP_REPORT.md (list of gaps citing specific filenames and line-level evidence, set risk tier as LOW/MEDIUM/HIGH/CRITICAL, and security flags including permissions, sandboxing, dependencies, and observability)
     * EVAL_RUBRIC.md (evaluation rubric with 3 test cases, 3 trajectory checks, and a final verdict)
  4. Call save_deep_audit_report() as the final mandatory step to save all three files (SPEC.md, GAP_REPORT.md, and EVAL_RUBRIC.md content) to the audit_reports/deep_audit folder. Keep the contents of the files separate and call save_deep_audit_report with the user's input/url as the first argument, followed by the SPEC.md content, the GAP_REPORT.md content, and the EVAL_RUBRIC.md content.

Never skip the interview in Deep Audit mode. Never mark risk tier as LOW if a critical action has no approval gate.
""",
    tools=[
        github_tool_source,
        read_project,
        LongRunningFunctionTool(func=request_intent_interview),
        save_report,
        save_deep_audit_report,
    ],
)

app = App(
    root_agent=root_agent,
    name="AKS009432",
)