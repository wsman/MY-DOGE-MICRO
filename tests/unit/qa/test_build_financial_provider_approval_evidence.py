import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.build_financial_provider_approval_evidence import build_evidence
from scripts.validate_financial_provider_approval_evidence import REQUIRED_CAPABILITIES, validate


ROOT = Path(__file__).resolve().parents[3]


def test_build_approved_provider_approval_evidence(tmp_path):
    decisions = tmp_path / "provider-decisions.json"
    _write_decisions(decisions, result="approved")

    payload = build_evidence(decisions_path=decisions, created_at="2026-06-22T02:00:00Z")

    assert payload["result"] == "approved"
    assert payload["operator"] == {"role": "product-owner", "initials": "PO"}
    assert payload["approved_at"] == "2026-06-22T02:01:00Z"
    assert payload["redaction_review"]["repository_storage_approved"] is True
    assert {item["capability"] for item in payload["decisions"]} == REQUIRED_CAPABILITIES
    assert all(item["decision_status"] == "approved" for item in payload["decisions"])
    assert validate(payload) == []


def test_build_needs_revision_provider_evidence_requires_issue_ref(tmp_path):
    decisions = tmp_path / "provider-decisions.json"
    _write_decisions(decisions, result="needs_revision", issue_refs=["PROVIDER-APPROVAL-001"])

    payload = build_evidence(decisions_path=decisions, created_at="2026-06-22T02:00:00Z")

    assert payload["result"] == "needs_revision"
    assert payload["issue_refs"] == ["PROVIDER-APPROVAL-001"]
    assert payload["blockers"] == ["provider approval result is needs_revision; see issue_refs"]
    assert validate(payload) == []


def test_build_rejects_missing_capability_decision(tmp_path):
    decisions = tmp_path / "provider-decisions.json"
    payload = _decision_payload(result="approved")
    payload["decisions"].pop("risk_factors")
    decisions.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="missing decisions: risk_factors"):
        build_evidence(decisions_path=decisions)


def test_build_rejects_missing_provider_redaction_flag(tmp_path):
    decisions = tmp_path / "provider-decisions.json"
    payload = _decision_payload(result="approved")
    payload["redaction_review"].pop("contains_credentials")
    decisions.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="redaction_review.contains_credentials must be an explicit boolean"):
        build_evidence(decisions_path=decisions)


def test_build_provider_approval_cli_writes_valid_output(tmp_path):
    decisions = tmp_path / "provider-decisions.json"
    output = tmp_path / "financial-provider-approval-2026-06-22.json"
    _write_decisions(decisions, result="approved")
    script = ROOT / "scripts" / "build_financial_provider_approval_evidence.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--decisions",
            str(decisions),
            "--output",
            str(output),
            "--created-at",
            "2026-06-22T02:00:00Z",
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
        "operator": {"role": "product-owner", "initials": "PO"},
        "approved_at": "2026-06-22T02:01:00Z",
        "issue_refs": issue_refs or [],
        "redaction_review": {
            "contains_credentials": False,
            "contains_proprietary_data": False,
            "repository_storage_approved": result == "approved",
        },
        "decisions": {
            capability: {
                "decision_status": decision_status,
                "approved_provider": f"{capability}-licensed-provider",
                "license_scope": "repository_synthetic_and_operator_approved_fixture_storage",
                "fixture_storage_policy": "store redacted fixtures only after provider license review",
                "freshness_requirement": "provider_timestamp and retrieved_at required",
                "provenance_requirement": "source_url or provider_document_id required",
                "notes": "operator-reviewed provider direction",
            }
            for capability in sorted(REQUIRED_CAPABILITIES)
        },
    }
