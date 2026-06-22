import json
from pathlib import Path
import subprocess
import sys

from scripts.validate_screen_reader_evidence import validate


ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = ROOT / "production" / "qa" / "evidence" / "manual" / (
    "research-agent-screen-reader-manual-template-2026-06-22.json"
)


def _template() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def _completed(status: str = "passed") -> dict:
    payload = _template()
    payload["result"] = status
    payload["executed_at"] = "2026-06-22T09:00:00Z"
    payload["operator"]["initials"] = "QA"
    payload["environment"].update(
        {
            "platform": "Windows 11",
            "browser": "Chrome",
            "browser_version": "126.0",
            "screen_reader": "NVDA",
            "screen_reader_version": "2024.4",
            "web_url": "http://127.0.0.1:5173/",
            "doged_base_url": "http://127.0.0.1:8901",
        }
    )
    payload["summary"] = "Manual screen-reader evidence completed."
    for check in payload["checks"]:
        check["status"] = "passed"
    return payload


def test_template_requires_explicit_allow_template():
    payload = _template()

    assert validate(payload, allow_template=True) == []
    errors = validate(payload)
    assert any("not_run evidence" in error for error in errors)


def test_completed_passed_evidence_validates():
    assert validate(_completed()) == []


def test_completed_evidence_requires_created_at():
    payload = _completed()
    payload.pop("created_at")

    errors = validate(payload)

    assert any("created_at is required" in error for error in errors)


def test_passed_evidence_rejects_failed_check():
    payload = _completed()
    payload["checks"][0]["status"] = "failed"

    errors = validate(payload)

    assert any("requires every check to pass" in error for error in errors)


def test_failed_evidence_requires_issue_reference():
    payload = _completed(status="failed")
    payload["checks"][0]["status"] = "failed"

    errors = validate(payload)

    assert any("requires issue_ref" in error for error in errors)
    assert any("requires at least one issue reference" in error for error in errors)


def test_completed_evidence_requires_explicit_redaction_flags():
    payload = _completed()
    payload["redaction_review"].pop("contains_sensitive_documents")

    errors = validate(payload)

    assert any("redaction_review.contains_sensitive_documents must be false" in error for error in errors)


def test_secret_like_values_are_rejected():
    payload = _completed()
    payload["summary"] = "Observed Authorization: Bearer abc.def.ghi in debug text"

    errors = validate(payload)

    assert any("appears to contain" in error for error in errors)


def test_cli_allows_template_only_with_flag():
    script = ROOT / "scripts" / "validate_screen_reader_evidence.py"
    denied = subprocess.run(
        [sys.executable, str(script), str(TEMPLATE_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    allowed = subprocess.run(
        [sys.executable, str(script), str(TEMPLATE_PATH), "--allow-template"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert denied.returncode == 1
    assert "not_run evidence" in denied.stdout
    assert allowed.returncode == 0
    assert json.loads(allowed.stdout)["passed"] is True
