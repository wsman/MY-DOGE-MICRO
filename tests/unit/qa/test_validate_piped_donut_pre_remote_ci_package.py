from pathlib import Path
import subprocess
import sys

import scripts.validate_piped_donut_pre_remote_ci_package as validator
from scripts.validate_piped_donut_pre_remote_ci_package import (
    PACKAGE,
    REQUIRED_PAYLOAD_PATHS,
    _read_plan_text,
    validate,
)


ROOT = Path(__file__).resolve().parents[3]


def test_piped_donut_pre_remote_ci_package_matches_current_boundary():
    errors = validate(PACKAGE.read_text(encoding="utf-8"))

    assert errors == []


def test_piped_donut_pre_remote_ci_package_rejects_completed_remote_ci_claim():
    text = PACKAGE.read_text(encoding="utf-8").replace("pending_remote_ci", "passed")

    errors = validate(text)

    assert any("package missing required snippet: pending_remote_ci" in error for error in errors)


def test_piped_donut_pre_remote_ci_package_rejects_missing_remote_ci_tool():
    text = PACKAGE.read_text(encoding="utf-8").replace(
        "scripts/verify_remote_ci_evidence.py",
        "scripts/missing_remote_ci_evidence.py",
    )

    errors = validate(text)

    assert any(
        "package missing required snippet: scripts/verify_remote_ci_evidence.py" in error
        for error in errors
    )


def test_piped_donut_pre_remote_ci_package_rejects_missing_workspace_payload_file():
    existing_paths = set(REQUIRED_PAYLOAD_PATHS)
    existing_paths.remove("tools/ci/sdk-contract-check.py")

    errors = validate(
        PACKAGE.read_text(encoding="utf-8"),
        existing_payload_paths=existing_paths,
    )

    assert "required payload path missing from workspace: tools/ci/sdk-contract-check.py" in errors


def test_piped_donut_pre_remote_ci_package_rejects_production_posture_claim():
    text = PACKAGE.read_text(encoding="utf-8").replace("production_ready: false", "production_ready: true")

    errors = validate(text)

    assert any("package missing required snippet: production_ready: false" in error for error in errors)


def test_piped_donut_pre_remote_ci_package_uses_fallback_plan_when_external_plan_missing(monkeypatch, tmp_path):
    missing_plan = tmp_path / "missing-piped-donut-plan.md"
    monkeypatch.setattr(validator, "PLAN", missing_plan)

    text = _read_plan_text(missing_plan)

    assert "docs/progress/my-doge-micro-main-2ffdb66-piped-donut-completion-audit.md" in text
    assert "scripts/validate_alpha_remote_ci_success.py" in text


def test_piped_donut_pre_remote_ci_package_cli():
    script = ROOT / "scripts" / "validate_piped_donut_pre_remote_ci_package.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"passed": true' in result.stdout
