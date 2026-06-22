from pathlib import Path
import subprocess
import sys

from scripts.validate_kimi_plan_completion_audit import AUDIT, validate


ROOT = Path(__file__).resolve().parents[3]


def test_kimi_plan_completion_audit_matches_closure_gate():
    errors = validate(AUDIT.read_text(encoding="utf-8"))

    assert errors == []


def test_kimi_plan_completion_audit_rejects_missing_gate_row():
    text = AUDIT.read_text(encoding="utf-8").replace("S017-007", "S017-XXX")

    errors = validate(text)

    assert any("audit missing remaining external item row: S017-007" in error for error in errors)
    assert any("audit has unexpected remaining external item row: S017-XXX" in error for error in errors)


def test_kimi_plan_completion_audit_rejects_missing_required_result():
    text = AUDIT.read_text(encoding="utf-8").replace("S017-003 | Financial provider fixture approval | `approved`", "S017-003 | Financial provider fixture approval | `needs_revision`")

    errors = validate(text)

    assert any("S017-003: audit row missing required result approved" in error for error in errors)


def test_kimi_plan_completion_audit_cli():
    script = ROOT / "scripts" / "validate_kimi_plan_completion_audit.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"passed": true' in result.stdout
