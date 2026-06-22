from pathlib import Path
import subprocess
import sys

from scripts.validate_plan_closure_runbook import RUNBOOK, validate


ROOT = Path(__file__).resolve().parents[3]


def test_plan_closure_runbook_matches_gate_manifest():
    errors = validate(RUNBOOK.read_text(encoding="utf-8"))

    assert errors == []


def test_plan_closure_runbook_rejects_missing_gate_details():
    text = RUNBOOK.read_text(encoding="utf-8")
    missing_gate = text.replace("S017-003", "")
    incomplete_gate = text.replace("production/qa/evidence/provider/financial-provider-approval-*.json", "")
    incomplete_gate = incomplete_gate.replace("`approved`", "", 1)
    missing_manifest_validator = text.replace("validate_plan_closure_manifest.py", "")

    missing_gate_errors = validate(missing_gate)
    incomplete_gate_errors = validate(incomplete_gate)
    missing_manifest_validator_errors = validate(missing_manifest_validator)

    assert any("missing gate id: S017-003" in error for error in missing_gate_errors)
    assert any("S017-003: runbook missing completed pattern" in error for error in incomplete_gate_errors)
    assert any("S017-003: runbook missing required result approved" in error for error in incomplete_gate_errors)
    assert any(
        "runbook missing global snippet: validate_plan_closure_manifest.py" in error
        for error in missing_manifest_validator_errors
    )


def test_plan_closure_runbook_cli():
    script = ROOT / "scripts" / "validate_plan_closure_runbook.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "OK" in result.stdout
