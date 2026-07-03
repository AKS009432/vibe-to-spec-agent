import os
import shutil
import datetime
import pytest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent


@pytest.fixture(autouse=True)
def cleanup_audit_reports() -> None:
    """Fixture to ensure audit_reports directory is removed after the test run."""
    yield
    if os.path.exists("audit_reports"):
        try:
            shutil.rmtree("audit_reports")
        except Exception:
            pass


def test_quick_scan_mode() -> None:
    """Verify that providing a GitHub URL triggers Quick Scan and saves to structured folders."""
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Audit this: https://github.com/myowner/myrepo")]
    )

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
        )
    )

    assert len(events) > 0

    ddmmyy = datetime.datetime.now().strftime("%d%m%y")
    expected_path = os.path.join("audit_reports", "quick_scan", f"myrepo_{ddmmyy}_scan.md")
    
    assert os.path.exists(expected_path), f"Scan report should be created at {expected_path}"
    with open(expected_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Quick Scan Findings" in content


def test_deep_audit_mode() -> None:
    """Verify that deep audit mode processes the request and saves all 3 files."""
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Please run deep audit on my agent")]
    )

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
        )
    )

    assert len(events) > 0

    # Confirm all 3 files are saved under deep_audit
    ddmmyy = datetime.datetime.now().strftime("%d%m%y")
    expected_repo_name = "please_run_deep"
    
    folder = os.path.join("audit_reports", "deep_audit")
    spec_path = os.path.join(folder, f"{expected_repo_name}_{ddmmyy}_spec.md")
    gap_path = os.path.join(folder, f"{expected_repo_name}_{ddmmyy}_gap_report.md")
    eval_path = os.path.join(folder, f"{expected_repo_name}_{ddmmyy}_eval_rubric.md")

    assert os.path.exists(spec_path), f"SPEC file should be created at {spec_path}"
    assert os.path.exists(gap_path), f"GAP report file should be created at {gap_path}"
    assert os.path.exists(eval_path), f"EVAL rubric file should be created at {eval_path}"

    with open(spec_path, "r", encoding="utf-8") as f:
        assert "Dummy Spec" in f.read()
