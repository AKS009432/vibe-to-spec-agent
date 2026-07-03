# conftest.py
import os
import sys
import json
from unittest.mock import MagicMock

# Set environment variables BEFORE importing any app modules
os.environ["INTEGRATION_TEST"] = "TRUE"
os.environ["GOOGLE_CLOUD_PROJECT"] = "dummy-project"
os.environ["GCLOUD_PROJECT"] = "dummy-project"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

# Mock google.auth.default
try:
    import google.auth
    mock_creds = MagicMock()
    google.auth.default = lambda *args, **kwargs: (mock_creds, "dummy-project")
except ImportError:
    pass

# Mock vertexai.init
try:
    import vertexai
    vertexai.init = lambda *args, **kwargs: None
except ImportError:
    pass

# Mock litellm.acompletion to avoid hitting real OpenAI endpoint
try:
    import litellm
    from litellm.types.utils import ModelResponse, Choices, Message, ChatCompletionMessageToolCall, Function

    original_acompletion = litellm.acompletion

    async def mock_acompletion(*args, **kwargs):
        messages = kwargs.get("messages", [])
        
        # Extract last user message to see the request
        user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content")
                if isinstance(content, list):
                    user_msg = " ".join([p.get("text", "") for p in content if isinstance(p, dict) and "text" in p])
                elif isinstance(content, str):
                    user_msg = content
                elif msg.get("parts"):
                    user_msg = " ".join([p.get("text", "") for p in msg.get("parts") if isinstance(p, dict) and "text" in p])
                break

        # Check if the query is a Quick Scan / Deep Audit
        is_deep_audit = any(k in user_msg.lower() for k in ["deep audit", "deep scan", "full audit"])
        is_quick_scan = "github.com" in user_msg.lower() and not is_deep_audit

        # Let's inspect the history of tools called
        tool_called_names = []
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg.get("tool_calls"):
                    if isinstance(tc, dict):
                        tool_called_names.append(tc.get("function", {}).get("name"))
                    else:
                        tool_called_names.append(getattr(tc, "function", MagicMock()).name)

        if is_quick_scan:
            # Quick Scan sequence:
            # 1. First call: return read_github_repo tool call
            if "read_github_repo" not in tool_called_names:
                tc = ChatCompletionMessageToolCall(
                    id="call_read_repo",
                    type="function",
                    function=Function(
                        name="read_github_repo",
                        arguments=json.dumps({"github_url": "https://github.com/user/repo"})
                    )
                )
                return ModelResponse(choices=[Choices(finish_reason="tool_calls", index=0, message=Message(content=None, role="assistant", tool_calls=[tc]))])
            # 2. Second call: return save_report tool call
            elif "save_report" not in tool_called_names:
                tc = ChatCompletionMessageToolCall(
                    id="call_save_report",
                    type="function",
                    function=Function(
                        name="save_report",
                        arguments=json.dumps({"repo_name_or_url": user_msg, "report_content": "# Quick Scan Findings\n- CRITICAL: Missing guardrails\n- HIGH: No authentication\n"})
                    )
                )
                return ModelResponse(choices=[Choices(finish_reason="tool_calls", index=0, message=Message(content=None, role="assistant", tool_calls=[tc]))])
            # 3. Third call: return final text
            else:
                return ModelResponse(choices=[Choices(finish_reason="stop", index=0, message=Message(content="Quick Scan complete. SCAN_REPORT.md saved.", role="assistant"))])

        elif is_deep_audit:
            # Deep Audit sequence:
            # 1. First call: return read_project (or read_github_repo if URL is in user_msg)
            if "read_project" not in tool_called_names and "read_github_repo" not in tool_called_names:
                if "github.com" in user_msg.lower():
                    tc = ChatCompletionMessageToolCall(
                        id="call_read_repo",
                        type="function",
                        function=Function(
                            name="read_github_repo",
                            arguments=json.dumps({"github_url": "https://github.com/user/repo"})
                        )
                    )
                else:
                    tc = ChatCompletionMessageToolCall(
                        id="call_read_project",
                        type="function",
                        function=Function(
                            name="read_project",
                            arguments=json.dumps({"input": user_msg})
                        )
                    )
                return ModelResponse(choices=[Choices(finish_reason="tool_calls", index=0, message=Message(content=None, role="assistant", tool_calls=[tc]))])
            # 2. If read_github_repo/read_project has run, but request_intent_interview hasn't:
            elif "request_intent_interview" not in tool_called_names:
                tc = ChatCompletionMessageToolCall(
                    id="call_interview",
                    type="function",
                    function=Function(
                        name="request_intent_interview",
                        arguments=json.dumps({"project_summary": "Summary of agent"})
                    )
                )
                return ModelResponse(choices=[Choices(finish_reason="tool_calls", index=0, message=Message(content=None, role="assistant", tool_calls=[tc]))])
            # 3. If interview answers are present:
            else:
                if "save_deep_audit_report" not in tool_called_names:
                    tc = ChatCompletionMessageToolCall(
                        id="call_save_deep_report",
                        type="function",
                        function=Function(
                            name="save_deep_audit_report",
                            arguments=json.dumps({
                                "repo_name_or_url": user_msg,
                                "spec_content": "# SPEC.md\nDummy Spec",
                                "gap_report_content": "# GAP_REPORT.md\nDummy Gap Report",
                                "eval_rubric_content": "# EVAL_RUBRIC.md\nDummy Eval Rubric"
                            })
                        )
                    )
                    return ModelResponse(choices=[Choices(finish_reason="tool_calls", index=0, message=Message(content=None, role="assistant", tool_calls=[tc]))])
                else:
                    return ModelResponse(choices=[Choices(finish_reason="stop", index=0, message=Message(content="Deep Audit report generated.", role="assistant"))])

        # Default fallback for simple questions (e.g. test_agent_stream)
        if "mock_response" not in kwargs:
            kwargs["mock_response"] = "This is a mock response from the LLM."
        return await original_acompletion(*args, **kwargs)

    litellm.acompletion = mock_acompletion
except ImportError:
    pass
