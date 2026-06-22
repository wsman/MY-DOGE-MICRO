import copy
import json
from pathlib import Path
import subprocess
import sys

from scripts.validate_enterprise_production_validation_evidence import validate


ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = ROOT / "production" / "qa" / "evidence" / "enterprise" / (
    "enterprise-production-validation-template-2026-06-22.json"
)


def _template() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def _passed() -> dict:
    payload = copy.deepcopy(_template())
    payload["result"] = "passed"
    payload["executed_at"] = "2026-06-22T09:00:00Z"
    payload["operator"] = {"role": "platform-operator", "initials": "OPS"}
    payload["blockers"] = []
    for check in payload["checks"]:
        check["status"] = "passed"
        check["evidence_ref"] = f"operator-secure-store://enterprise/{check['id']}"
        check["notes"] = "Validated in an operator-approved environment; no secrets recorded."
    return payload


def test_template_requires_explicit_allow_template():
    payload = _template()

    assert validate(payload, allow_template=True) == []
    errors = validate(payload)

    assert any("not_run evidence" in error for error in errors)


def test_passed_enterprise_production_validation_evidence_validates():
    assert validate(_passed()) == []


def test_passed_evidence_requires_every_check_to_pass():
    payload = _passed()
    payload["checks"][0]["status"] = "blocked"

    errors = validate(payload)

    assert any("requires every check to pass" in error for error in errors)


def test_failed_or_blocked_check_requires_issue_ref_when_result_failed():
    payload = _passed()
    payload["result"] = "failed"
    payload["checks"][0]["status"] = "failed"

    errors = validate(payload)

    assert any("requires issue_ref" in error for error in errors)
    assert any("failed evidence requires issue_refs" in error for error in errors)


def test_local_evidence_paths_are_checked():
    payload = _passed()
    payload["local_evidence"]["local_jwks_smoke"] = "production/qa/evidence/manual/missing.json"

    errors = validate(payload)

    assert any("local evidence not found" in error for error in errors)


def test_secret_like_values_are_rejected():
    payload = _passed()
    payload["checks"][0]["notes"] = "Observed Authorization: Bearer abc.def.ghi"

    errors = validate(payload)

    assert any("appears to contain" in error for error in errors)


def test_cli_allows_template_only_with_flag():
    script = ROOT / "scripts" / "validate_enterprise_production_validation_evidence.py"
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
