import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.build_enterprise_production_validation_evidence import build_evidence
from scripts.validate_enterprise_production_validation_evidence import REQUIRED_CHECK_IDS, validate


ROOT = Path(__file__).resolve().parents[3]


def test_build_passed_enterprise_production_evidence(tmp_path):
    observations = tmp_path / "enterprise-production-observations.json"
    _write_observations(observations, result="passed")

    payload = build_evidence(observations_path=observations, created_at="2026-06-22T05:00:00Z")

    assert payload["result"] == "passed"
    assert payload["operator"] == {"role": "platform-operator", "initials": "OPS"}
    assert {item["id"] for item in payload["checks"]} == REQUIRED_CHECK_IDS
    assert all(item["status"] == "passed" for item in payload["checks"])
    assert payload["blockers"] == []
    assert validate(payload) == []


def test_build_failed_enterprise_production_evidence_requires_issue_refs(tmp_path):
    observations = tmp_path / "enterprise-production-observations.json"
    _write_observations(observations, result="failed", issue_ref="AUTH-PROD-101")

    payload = build_evidence(observations_path=observations, created_at="2026-06-22T05:00:00Z")

    assert payload["result"] == "failed"
    assert payload["issue_refs"] == ["AUTH-PROD-101"]
    failed = [item for item in payload["checks"] if item["status"] == "failed"]
    assert failed[0]["issue_ref"] == "AUTH-PROD-101"
    assert payload["blockers"] == ["Enterprise production validation failed; see issue_refs"]
    assert validate(payload) == []


def test_build_rejects_missing_check(tmp_path):
    observations = tmp_path / "enterprise-production-observations.json"
    payload = _observation_payload(result="passed")
    payload["checks"].pop("siem_worm_export")
    observations.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="missing checks: siem_worm_export"):
        build_evidence(observations_path=observations)


def test_build_rejects_not_run_result(tmp_path):
    observations = tmp_path / "enterprise-production-observations.json"
    _write_observations(observations, result="not_run")

    with pytest.raises(ValueError, match="observation result must be one of"):
        build_evidence(observations_path=observations)


def test_build_rejects_missing_evidence_ref(tmp_path):
    observations = tmp_path / "enterprise-production-observations.json"
    payload = _observation_payload(result="passed")
    payload["checks"]["live_idp_jwks"]["evidence_ref"] = ""
    observations.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="evidence_ref is required"):
        build_evidence(observations_path=observations)


def test_build_rejects_missing_enterprise_redaction_flag(tmp_path):
    observations = tmp_path / "enterprise-production-observations.json"
    payload = _observation_payload(result="passed")
    payload["redaction_review"].pop("contains_proprietary_customer_data")
    observations.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="redaction_review.contains_proprietary_customer_data must be an explicit boolean",
    ):
        build_evidence(observations_path=observations)


def test_build_enterprise_production_cli_writes_valid_output(tmp_path):
    observations = tmp_path / "enterprise-production-observations.json"
    output = tmp_path / "enterprise-production-validation-2026-06-22.json"
    _write_observations(observations, result="passed")
    script = ROOT / "scripts" / "build_enterprise_production_validation_evidence.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--observations",
            str(observations),
            "--output",
            str(output),
            "--created-at",
            "2026-06-22T05:00:00Z",
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
    failed_check = "siem_worm_export" if result == "failed" else None
    return {
        "result": result,
        "executed_at": "2026-06-22T05:01:00Z",
        "operator": {"role": "platform-operator", "initials": "OPS"},
        "checks": {
            check_id: _check_payload(check_id, failed_check, issue_ref)
            for check_id in sorted(REQUIRED_CHECK_IDS)
        },
        "issue_refs": [issue_ref] if issue_ref else [],
        "redaction_review": {
            "contains_credentials": False,
            "contains_raw_subjects": False,
            "contains_proprietary_customer_data": False,
            "notes": "Operator confirmed only redacted production validation IDs are recorded.",
        },
    }


def _check_payload(check_id: str, failed_check: str | None, issue_ref: str | None) -> dict:
    status = "failed" if check_id == failed_check else "passed"
    item = {
        "status": status,
        "evidence_ref": f"operator-secure-store://enterprise/{check_id}",
        "notes": f"{check_id} observed in an operator-approved environment; no secrets recorded.",
    }
    if status == "failed" and issue_ref:
        item["issue_ref"] = issue_ref
    return item
