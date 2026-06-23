from pathlib import Path
import subprocess
import sys

from scripts.validate_alpha_pre_remote_ci_package import PACKAGE, REQUIRED_PAYLOAD_PATHS, validate


ROOT = Path(__file__).resolve().parents[3]


def test_alpha_pre_remote_ci_package_matches_current_boundary():
    errors = validate(PACKAGE.read_text(encoding="utf-8"))

    assert errors == []


def test_alpha_pre_remote_ci_package_rejects_completed_remote_ci_claim():
    text = PACKAGE.read_text(encoding="utf-8").replace("pending_remote_ci", "passed")

    errors = validate(text)

    assert any("package missing required snippet: pending_remote_ci" in error for error in errors)


def test_alpha_pre_remote_ci_package_rejects_missing_required_payload_file():
    text = PACKAGE.read_text(encoding="utf-8").replace(
        "scripts/verify_remote_ci_evidence.py",
        "scripts/missing_remote_ci_evidence.py",
    )

    errors = validate(text)

    assert any(
        "package missing required snippet: scripts/verify_remote_ci_evidence.py" in error
        for error in errors
    )


def test_alpha_pre_remote_ci_package_rejects_missing_workspace_payload_file():
    existing_paths = set(REQUIRED_PAYLOAD_PATHS)
    existing_paths.remove("scripts/verify_remote_ci_evidence.py")

    errors = validate(
        PACKAGE.read_text(encoding="utf-8"),
        existing_payload_paths=existing_paths,
    )

    assert "required payload path missing from workspace: scripts/verify_remote_ci_evidence.py" in errors


def test_alpha_pre_remote_ci_package_rejects_production_posture_claim():
    text = PACKAGE.read_text(encoding="utf-8").replace("production_ready: false", "production_ready: true")

    errors = validate(text)

    assert any("package missing required snippet: production_ready: false" in error for error in errors)


def test_alpha_pre_remote_ci_package_cli():
    script = ROOT / "scripts" / "validate_alpha_pre_remote_ci_package.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"passed": true' in result.stdout
