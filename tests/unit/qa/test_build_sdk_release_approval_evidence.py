import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.build_sdk_release_approval_evidence import build_evidence
from scripts.validate_sdk_release_approval_evidence import REQUIRED_LANGUAGES, validate


ROOT = Path(__file__).resolve().parents[3]


def test_build_approved_sdk_release_evidence(tmp_path):
    decisions = tmp_path / "sdk-release-decisions.json"
    _write_decisions(decisions, result="approved")

    payload = build_evidence(decisions_path=decisions, created_at="2026-06-22T03:00:00Z")

    assert payload["result"] == "approved"
    assert payload["release_manager"] == {"role": "release-manager", "initials": "RM"}
    assert payload["approved_at"] == "2026-06-22T03:01:00Z"
    assert payload["security_review"]["no_credentials_in_package_config"] is True
    assert {item["language"] for item in payload["packages"]} == REQUIRED_LANGUAGES
    assert all(item["decision_status"] == "approved" for item in payload["packages"])
    assert validate(payload) == []


def test_build_needs_revision_sdk_release_evidence_requires_issue_ref(tmp_path):
    decisions = tmp_path / "sdk-release-decisions.json"
    _write_decisions(decisions, result="needs_revision", issue_refs=["SDK-RELEASE-001"])

    payload = build_evidence(decisions_path=decisions, created_at="2026-06-22T03:00:00Z")

    assert payload["result"] == "needs_revision"
    assert payload["issue_refs"] == ["SDK-RELEASE-001"]
    assert payload["blockers"] == ["SDK release approval result is needs_revision; see issue_refs"]
    assert validate(payload) == []


def test_build_rejects_missing_language_decision(tmp_path):
    decisions = tmp_path / "sdk-release-decisions.json"
    payload = _decision_payload(result="approved")
    payload["packages"].pop("typescript")
    decisions.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="missing packages: typescript"):
        build_evidence(decisions_path=decisions)


def test_build_sdk_release_cli_writes_valid_output(tmp_path):
    decisions = tmp_path / "sdk-release-decisions.json"
    output = tmp_path / "sdk-release-approval-2026-06-22.json"
    _write_decisions(decisions, result="approved")
    script = ROOT / "scripts" / "build_sdk_release_approval_evidence.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--decisions",
            str(decisions),
            "--output",
            str(output),
            "--created-at",
            "2026-06-22T03:00:00Z",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    cli_result = json.loads(result.stdout)
    assert cli_result["result"] == "approved"
    assert cli_result["passed_validation"] is True
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert validate(payload) == []


def _write_decisions(path: Path, *, result: str, issue_refs: list[str] | None = None) -> None:
    path.write_text(json.dumps(_decision_payload(result=result, issue_refs=issue_refs), indent=2), encoding="utf-8")


def _decision_payload(*, result: str, issue_refs: list[str] | None = None) -> dict:
    decision_status = "approved" if result == "approved" else result
    return {
        "result": result,
        "release_manager": {"role": "release-manager", "initials": "RM"},
        "approved_at": "2026-06-22T03:01:00Z",
        "issue_refs": issue_refs or [],
        "security_review": {
            "no_credentials_in_package_config": result == "approved",
            "typescript_sources_excluded_from_tarball": result == "approved",
            "redaction_behavior_documented": result == "approved",
            "contains_credentials": False,
        },
        "packages": {
            language: {
                "decision_status": decision_status,
                "approved_package_name": "doge-sdk" if language == "python" else "@my-doge/doge-sdk",
                "registry_target": "internal-artifact-registry",
                "package_name_ownership": "release-manager approved namespace ownership",
                "version_policy": "semver; 0.1.0 internal preview only",
                "changelog_policy": "changelog required for auth, documents, SSE, approvals, and redaction changes",
                "registry_consumer_smoke": "registry-backed consumer smoke required before publication",
                "notes": "release-manager reviewed SDK release direction",
            }
            for language in sorted(REQUIRED_LANGUAGES)
        },
    }
