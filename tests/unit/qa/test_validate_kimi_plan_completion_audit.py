from copy import deepcopy
from pathlib import Path
import subprocess
import sys

import scripts.validate_kimi_plan_completion_audit as audit_validator
from scripts.validate_kimi_plan_completion_audit import AUDIT, validate
from scripts.validate_plan_closure_gate import validate_all


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


def test_kimi_plan_completion_audit_accepts_completed_gate_outside_remaining_items(monkeypatch):
    monkeypatch.setattr(
        audit_validator,
        "validate_all",
        lambda allow_open=True: _gate_output_with_s017006_passed(),
    )
    text = _audit_text_with_s017006_completed()

    errors = audit_validator.validate(text)

    assert errors == []


def test_kimi_plan_completion_audit_rejects_missing_completed_gate_evidence(monkeypatch):
    monkeypatch.setattr(
        audit_validator,
        "validate_all",
        lambda allow_open=True: _gate_output_with_s017006_passed(),
    )
    text = _audit_text_with_s017006_completed().replace(
        "production/qa/evidence/manual/research-agent-screen-reader-manual-2026-06-22.json",
        "production/qa/evidence/manual/missing-screen-reader-evidence.json",
    )

    errors = audit_validator.validate(text)

    assert any(
        "S017-006: audit missing completed evidence "
        "production/qa/evidence/manual/research-agent-screen-reader-manual-2026-06-22.json" in error
        for error in errors
    )


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


def _audit_text_with_s017006_completed() -> str:
    text = AUDIT.read_text(encoding="utf-8")
    lines = [
        line
        for line in text.splitlines()
        if not line.startswith("| S017-006 | Research Agent screen-reader manual pass |")
    ]
    text = "\n".join(lines)
    text = text.replace("S017-006 screen-reader manual pass, and ", "")
    text += (
        "\n\n## Completed External Items\n\n"
        "- S017-006 passed evidence: "
        "`production/qa/evidence/manual/research-agent-screen-reader-manual-2026-06-22.json`.\n"
    )
    return text
