import copy
import json
from pathlib import Path
import subprocess
import sys

from scripts.validate_sdk_release_approval_evidence import validate


ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = ROOT / "production" / "qa" / "evidence" / "sdk" / (
    "sdk-release-approval-template-2026-06-22.json"
)


def _template() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def _approved() -> dict:
    payload = copy.deepcopy(_template())
    payload["result"] = "approved"
    payload["approved_at"] = "2026-06-22T09:00:00Z"
    payload["release_manager"] = {"role": "release-manager", "initials": "RM"}
    payload["blockers"] = []
    payload["security_review"].update(
        {
            "no_credentials_in_package_config": True,
            "typescript_sources_excluded_from_tarball": True,
            "redaction_behavior_documented": True,
        }
    )
    for package in payload["packages"]:
        package["decision_status"] = "approved"
        package["approved_package_name"] = package["current_name"]
        package["registry_target"] = "internal-artifact-registry"
        package["package_name_ownership"] = "approved by release manager"
        package["version_policy"] = "0.1.0 internal preview; semver required before external release"
        package["changelog_policy"] = "release notes include auth headers, documents, SSE, approvals, and redaction"
        package["registry_consumer_smoke"] = "required after upload to approved registry"
    return payload


def test_template_requires_explicit_allow_template():
    payload = _template()

    assert validate(payload, allow_template=True) == []
    errors = validate(payload)

    assert any("not_run evidence" in error for error in errors)


def test_approved_release_evidence_validates():
    assert validate(_approved()) == []


def test_approved_release_rejects_pending_registry_target():
    payload = _approved()
    payload["packages"][0]["registry_target"] = "pending"

    errors = validate(payload)

    assert any("registry_target must be filled" in error for error in errors)


def test_approved_release_requires_security_review():
    payload = _approved()
    payload["security_review"]["redaction_behavior_documented"] = False

    errors = validate(payload)

    assert any("redaction_behavior_documented=true" in error for error in errors)


def test_local_evidence_paths_are_checked():
    payload = _approved()
    payload["local_evidence"]["external_consumer_smoke"] = "production/qa/evidence/sdk/missing.json"

    errors = validate(payload)

    assert any("local evidence not found" in error for error in errors)


def test_secret_like_values_are_rejected():
    payload = _approved()
    payload["packages"][0]["notes"] = "temporary token: should-not-appear"

    errors = validate(payload)

    assert any("appears to contain" in error for error in errors)


def test_cli_allows_template_only_with_flag():
    script = ROOT / "scripts" / "validate_sdk_release_approval_evidence.py"
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
