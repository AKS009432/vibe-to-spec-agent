import os
import datetime
from unittest.mock import patch, mock_open
from app.agent import save_report, save_deep_audit_report, extract_repo_name


def test_extract_repo_name() -> None:
    assert extract_repo_name("https://github.com/myowner/myrepo") == "myrepo"
    assert extract_repo_name("https://github.com/myowner/my-cool-repo.git") == "my-cool-repo"
    assert extract_repo_name("My simple project description") == "my_simple_project"
    assert extract_repo_name("") == "project"


@patch("os.makedirs")
@patch("builtins.open", new_callable=mock_open)
def test_save_report_success(mock_file, mock_makedirs) -> None:
    repo_url = "https://github.com/myowner/myrepo"
    report_content = "# Test Scan Report\nSome mock findings."
    ddmmyy = datetime.datetime.now().strftime("%d%m%y")
    expected_path = os.path.join("audit_reports", "quick_scan", f"myrepo_{ddmmyy}_scan.md")
    
    result = save_report(repo_url, report_content)
    
    assert "Success" in result
    mock_makedirs.assert_called_once_with(os.path.join("audit_reports", "quick_scan"), exist_ok=True)
    mock_file.assert_called_once_with(expected_path, "w", encoding="utf-8")
    mock_file().write.assert_called_once_with(report_content)


@patch("os.makedirs")
@patch("builtins.open", new_callable=mock_open)
def test_save_deep_audit_report_success(mock_file, mock_makedirs) -> None:
    repo_url = "https://github.com/myowner/my-deep-repo"
    spec = "# SPEC\ncontent"
    gap = "# GAP\ncontent"
    rubric = "# RUBRIC\ncontent"
    ddmmyy = datetime.datetime.now().strftime("%d%m%y")
    
    result = save_deep_audit_report(repo_url, spec, gap, rubric)
    
    assert "Success" in result
    mock_makedirs.assert_called_once_with(os.path.join("audit_reports", "deep_audit"), exist_ok=True)
    
    assert mock_file.call_count == 3
    
    expected_folder = os.path.join("audit_reports", "deep_audit")
    mock_file.assert_any_call(os.path.join(expected_folder, f"my-deep-repo_{ddmmyy}_spec.md"), "w", encoding="utf-8")
    mock_file.assert_any_call(os.path.join(expected_folder, f"my-deep-repo_{ddmmyy}_gap_report.md"), "w", encoding="utf-8")
    mock_file.assert_any_call(os.path.join(expected_folder, f"my-deep-repo_{ddmmyy}_eval_rubric.md"), "w", encoding="utf-8")
