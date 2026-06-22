import copy
import json
from pathlib import Path
import subprocess
import sys

from scripts.validate_financial_provider_approval_evidence import validate


ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = ROOT / "production" / "qa" / "evidence" / "provider" / (
    "financial-provider-approval-template-2026-06-22.json"
)


def _template() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def _approved() -> dict:
    payload = copy.deepcopy(_template())
    payload["result"] = "approved"
    payload["approved_at"] = "2026-06-22T09:00:00Z"
    payload["operator"] = {"role": "product-owner", "initials": "PO"}
    payload["blockers"] = []
    payload["redaction_review"]["repository_storage_approved"] = True
    for decision in payload["decisions"]:
        decision["decision_status"] = "approved"
        decision["approved_provider"] = f"approved-{decision['capability']}-provider"
        decision["license_scope"] = "test_fixture_and_local_demo_only"
        decision["fixture_storage_policy"] = "synthetic_safe_samples_only_until_provider_written_approval"
        decision["freshness_requirement"] = "as_of and retrieved_at required on every fixture"
        decision["provenance_requirement"] = "source_id or source_url required on every fixture"
    return payload


def test_template_requires_explicit_allow_template():
    payload = _template()

    assert validate(payload, allow_template=True) == []
    errors = validate(payload)

    assert any("not_run evidence" in error for error in errors)


def test_approved_provider_evidence_validates():
    assert validate(_approved()) == []


def test_approved_evidence_rejects_pending_license_scope():
    payload = _approved()
    payload["decisions"][0]["license_scope"] = "pending"

    errors = validate(payload)

    assert any("license_scope must be filled" in error for error in errors)


def test_approved_evidence_requires_repository_storage_approval():
    payload = _approved()
    payload["redaction_review"]["repository_storage_approved"] = False

    errors = validate(payload)

    assert any("repository_storage_approved=true" in error for error in errors)


def test_contract_paths_are_checked():
    payload = _approved()
    payload["contract"]["synthetic_samples"] = "tests/fixtures/financial_connectors/missing.json"

    errors = validate(payload)

    assert any("synthetic samples not found" in error for error in errors)


def test_secret_like_values_are_rejected():
    payload = _approved()
    payload["decisions"][0]["notes"] = "MOONSHOT_API_KEY=sk-live-secret-value"

    errors = validate(payload)

    assert any("appears to contain" in error for error in errors)
    assert any("unredacted secret assignment" in error for error in errors)
    assert any("provider-style API key" in error for error in errors)
    assert not any("sk-live-secret-value" in error for error in errors)


def test_completed_evidence_rejects_unresolved_template_placeholder():
    payload = _approved()
    payload["operator"]["initials"] = "<initials>"

    errors = validate(payload)

    assert any("unresolved placeholder: <initials>" in error for error in errors)


def test_cli_allows_template_only_with_flag():
    script = ROOT / "scripts" / "validate_financial_provider_approval_evidence.py"
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
