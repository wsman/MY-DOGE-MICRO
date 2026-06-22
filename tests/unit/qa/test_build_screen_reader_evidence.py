import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.build_screen_reader_evidence import build_evidence
from scripts.validate_screen_reader_evidence import REQUIRED_CHECK_IDS, validate


ROOT = Path(__file__).resolve().parents[3]


def test_build_passed_screen_reader_evidence(tmp_path):
    observations = tmp_path / "screen-reader-observations.json"
    _write_observations(observations, result="passed")

    payload = build_evidence(observations_path=observations, created_at="2026-06-22T04:00:00Z")

    assert payload["result"] == "passed"
    assert payload["operator"] == {"role": "accessibility-specialist", "initials": "QA"}
    assert payload["environment"]["screen_reader"] == "NVDA"
    assert {item["id"] for item in payload["checks"]} == REQUIRED_CHECK_IDS
    assert all(item["status"] == "passed" for item in payload["checks"])
    assert validate(payload) == []


def test_build_failed_screen_reader_evidence_requires_issue_refs(tmp_path):
    observations = tmp_path / "screen-reader-observations.json"
    _write_observations(observations, result="failed", issue_ref="A11Y-101")

    payload = build_evidence(observations_path=observations, created_at="2026-06-22T04:00:00Z")

    assert payload["result"] == "failed"
    assert payload["issues"] == ["A11Y-101"]
    failed = [item for item in payload["checks"] if item["status"] == "failed"]
    assert failed[0]["issue_ref"] == "A11Y-101"
    assert validate(payload) == []


def test_build_rejects_missing_check(tmp_path):
    observations = tmp_path / "screen-reader-observations.json"
    payload = _observation_payload(result="passed")
    payload["checks"].pop("sr_no_keyboard_trap")
    observations.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="missing checks: sr_no_keyboard_trap"):
        build_evidence(observations_path=observations)


def test_build_rejects_not_run_result(tmp_path):
    observations = tmp_path / "screen-reader-observations.json"
    _write_observations(observations, result="not_run")

    with pytest.raises(ValueError, match="observation result must be one of"):
        build_evidence(observations_path=observations)


def test_build_rejects_missing_screen_reader_redaction_flag(tmp_path):
    observations = tmp_path / "screen-reader-observations.json"
    payload = _observation_payload(result="passed")
    payload["redaction_review"].pop("contains_sensitive_documents")
    observations.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="redaction_review.contains_sensitive_documents must be an explicit boolean",
    ):
        build_evidence(observations_path=observations)


def test_build_screen_reader_cli_writes_valid_output(tmp_path):
    observations = tmp_path / "screen-reader-observations.json"
    output = tmp_path / "research-agent-screen-reader-manual-2026-06-22.json"
    _write_observations(observations, result="passed")
    script = ROOT / "scripts" / "build_screen_reader_evidence.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--observations",
            str(observations),
            "--output",
            str(output),
            "--created-at",
            "2026-06-22T04:00:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    cli_result = json.loads(result.stdout)
    assert cli_result["result"] == "passed"
    assert cli_result["passed_validation"] is True
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert validate(payload) == []


def _write_observations(path: Path, *, result: str, issue_ref: str | None = None) -> None:
    path.write_text(json.dumps(_observation_payload(result=result, issue_ref=issue_ref), indent=2), encoding="utf-8")


def _observation_payload(*, result: str, issue_ref: str | None = None) -> dict:
    failed_check = "sr_status_announcements" if result == "failed" else None
    return {
        "result": result,
        "executed_at": "2026-06-22T04:01:00Z",
        "summary": "Manual screen-reader session completed with non-sensitive fixtures.",
        "operator": {"role": "accessibility-specialist", "initials": "QA"},
        "environment": {
            "platform": "Windows 11",
            "browser": "Chrome",
            "browser_version": "126.0",
            "screen_reader": "NVDA",
            "screen_reader_version": "2024.4",
            "web_url": "http://127.0.0.1:5173/research-agent",
            "doged_base_url": "http://127.0.0.1:8901",
            "live_kimi": False,
        },
        "fixtures": {
            "documents": ["non-sensitive-text-fixture.md"],
            "portfolio": "non-sensitive-portfolio.csv",
            "execution_profile": "financial_research",
        },
        "checks": {
            check_id: _check_payload(check_id, failed_check, issue_ref)
            for check_id in sorted(REQUIRED_CHECK_IDS)
        },
        "issues": [issue_ref] if issue_ref else [],
        "attachments": ["production/qa/evidence/manual/research-agent-ax-tree-2026-06-22.md"],
        "redaction_review": {
            "contains_secrets": False,
            "contains_sensitive_documents": False,
            "notes": "Operator confirmed no secrets or sensitive source documents are present.",
        },
    }


def _check_payload(check_id: str, failed_check: str | None, issue_ref: str | None) -> dict:
    status = "failed" if check_id == failed_check else "passed"
    item = {
        "status": status,
        "severity": "major" if status == "failed" else None,
        "notes": f"{check_id} observed during manual screen-reader pass.",
    }
    if status == "failed" and issue_ref:
        item["issue_ref"] = issue_ref
    return item
