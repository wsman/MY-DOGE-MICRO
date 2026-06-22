from copy import deepcopy
from pathlib import Path
import subprocess
import sys

import scripts.validate_plan_closure_runbook as runbook_validator
from scripts.validate_plan_closure_gate import validate_all
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


def test_plan_closure_runbook_accepts_completed_gate_outside_remaining_gates(monkeypatch):
    monkeypatch.setattr(
        runbook_validator,
        "validate_all",
        lambda allow_open=True: _gate_output_with_s017006_passed(),
    )
    text = _runbook_text_with_s017006_completed()

    errors = runbook_validator.validate(text)

    assert errors == []


def test_plan_closure_runbook_rejects_missing_completed_gate_evidence(monkeypatch):
    monkeypatch.setattr(
        runbook_validator,
        "validate_all",
        lambda allow_open=True: _gate_output_with_s017006_passed(),
    )
    text = _runbook_text_with_s017006_completed().replace(
        "production/qa/evidence/manual/research-agent-screen-reader-manual-2026-06-22.json",
        "production/qa/evidence/manual/missing-screen-reader-evidence.json",
    )

    errors = runbook_validator.validate(text)

    assert any(
        "S017-006: runbook missing completed evidence "
        "production/qa/evidence/manual/research-agent-screen-reader-manual-2026-06-22.json" in error
        for error in errors
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


def _gate_output_with_s017006_passed():
    payload = deepcopy(validate_all(allow_open=True))
    payload["summary"]["open"] = 5
    payload["summary"]["passed"] = 1
    for gate in payload["gates"]:
        if gate["id"] == "S017-006":
            gate["status"] = "passed"
            gate["evidence"] = (
                "production\\qa\\evidence\\manual\\research-agent-screen-reader-manual-2026-06-22.json"
            )
            gate["evidence_result"] = "passed"
            gate["strict_errors"] = []
            gate["allowed_errors"] = []
    return payload


def _runbook_text_with_s017006_completed() -> str:
    text = RUNBOOK.read_text(encoding="utf-8")
    lines = [
        line
        for line in text.splitlines()
        if not line.startswith("| S017-006 | `passed` |")
    ]
    text = "\n".join(lines)
    text += (
        "\n\n## Completed Gates\n\n"
        "- S017-006 passed evidence: "
        "`production/qa/evidence/manual/research-agent-screen-reader-manual-2026-06-22.json`.\n"
    )
    return text
