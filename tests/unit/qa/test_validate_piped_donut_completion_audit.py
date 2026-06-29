from copy import deepcopy
from pathlib import Path
import subprocess
import sys

import scripts.validate_piped_donut_completion_audit as audit_validator
from scripts.validate_piped_donut_completion_audit import AUDIT, validate
from scripts.validate_plan_closure_gate import validate_all


ROOT = Path(__file__).resolve().parents[3]


def test_piped_donut_completion_audit_matches_current_gate():
    errors = validate(AUDIT.read_text(encoding="utf-8"))

    assert errors == []


def test_piped_donut_completion_audit_rejects_missing_workstream_row():
    text = AUDIT.read_text(encoding="utf-8").replace("C-04 SDK contract drift gate", "C-04 missing row")

    errors = validate(text)

    assert any("audit missing requirement matrix row: C-04 SDK contract drift gate" in error for error in errors)


def test_piped_donut_completion_audit_rejects_external_gate_completion_claim():
    text = AUDIT.read_text(encoding="utf-8").replace(
        "Open pending real operator evidence.",
        "Locally complete.",
    )

    errors = validate(text)

    assert "D-02 row must remain open pending real operator evidence" in errors


def test_piped_donut_completion_audit_rejects_missing_external_gate():
    text = AUDIT.read_text(encoding="utf-8").replace("S017-007", "S017-XXX")

    errors = validate(text)

    assert any("audit missing remaining external gate row: S017-007" in error for error in errors)
    assert any("audit has unexpected remaining external gate row: S017-XXX" in error for error in errors)


def test_piped_donut_completion_audit_accepts_completed_gate_outside_remaining_table(monkeypatch):
    monkeypatch.setattr(
        audit_validator,
        "validate_all",
        lambda allow_open=True: _gate_output_with_s017007_passed(),
    )
    text = _audit_text_with_s017007_completed()

    errors = audit_validator.validate(text)

    assert errors == []


def test_piped_donut_completion_audit_cli():
    script = ROOT / "scripts" / "validate_piped_donut_completion_audit.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"passed": true' in result.stdout


def _gate_output_with_s017007_passed():
    payload = deepcopy(validate_all(allow_open=True))
    payload["summary"]["open"] = 3
    payload["summary"]["passed"] = 3
    for gate in payload["gates"]:
        if gate["id"] == "S017-007":
            gate["status"] = "passed"
            gate["evidence"] = "production\\qa\\evidence\\sdk\\sdk-release-approval-2026-06-24.json"
            gate["evidence_result"] = "approved"
            gate["strict_errors"] = []
            gate["allowed_errors"] = []
    return payload


def _audit_text_with_s017007_completed() -> str:
    text = AUDIT.read_text(encoding="utf-8")
    lines = [
        line
        for line in text.splitlines()
        if not line.startswith("| S017-007 |")
    ]
    text = "\n".join(lines)
    text = text.replace("4 open / 2 passed", "3 open / 3 passed")
    text += (
        "\n\nS017-007 is already passed with "
        "`production\\qa\\evidence\\sdk\\sdk-release-approval-2026-06-24.json`.\n"
    )
    return text
