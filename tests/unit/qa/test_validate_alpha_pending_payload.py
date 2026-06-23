from pathlib import Path
import subprocess
import sys

from scripts.validate_alpha_pending_payload import (
    REQUIRED_PENDING_PATHS,
    REQUIRED_PENDING_PREFIXES,
    validate,
)


ROOT = Path(__file__).resolve().parents[3]


def test_alpha_pending_payload_accepts_required_status_lines():
    status_lines = [f" M {path}" for path in REQUIRED_PENDING_PATHS]
    status_lines += [f" M {prefix}README.md" for prefix in REQUIRED_PENDING_PREFIXES]

    errors = validate(status_lines)

    assert errors == []


def test_alpha_pending_payload_rejects_missing_required_path():
    status_lines = [
        f" M {path}"
        for path in REQUIRED_PENDING_PATHS
        if path != "scripts/verify_remote_ci_evidence.py"
    ]
    status_lines += [f" M {prefix}README.md" for prefix in REQUIRED_PENDING_PREFIXES]

    errors = validate(status_lines)

    assert (
        "required path missing from pending commit payload: scripts/verify_remote_ci_evidence.py"
        in errors
    )


def test_alpha_pending_payload_parses_renamed_status_lines():
    status_lines = [f" M {path}" for path in REQUIRED_PENDING_PATHS]
    status_lines += [f" M {prefix}README.md" for prefix in REQUIRED_PENDING_PREFIXES]
    status_lines.append("R  old/path.py -> scripts/verify_remote_ci_evidence.py")

    errors = validate(status_lines)

    assert errors == []


def test_alpha_pending_payload_rejects_missing_required_directory_prefix():
    status_lines = [f" M {path}" for path in REQUIRED_PENDING_PATHS]

    errors = validate(status_lines)

    assert (
        "required directory missing from pending commit payload: "
        "production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/" in errors
    )


def test_alpha_pending_payload_cli_status_file(tmp_path):
    status_file = tmp_path / "status.txt"
    lines = [f"?? {path}" for path in REQUIRED_PENDING_PATHS]
    lines += [f"?? {prefix}README.md" for prefix in REQUIRED_PENDING_PREFIXES]
    status_file.write_text("\n".join(lines), encoding="utf-8")
    script = ROOT / "scripts" / "validate_alpha_pending_payload.py"

    result = subprocess.run(
        [sys.executable, str(script), "--status-file", str(status_file)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"passed": true' in result.stdout
