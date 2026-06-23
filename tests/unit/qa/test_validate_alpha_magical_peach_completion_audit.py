import json
from pathlib import Path
import subprocess
import sys

from scripts.validate_alpha_magical_peach_completion_audit import (
    AUDIT,
    FALLBACK_PLAN_TEXT,
    MANIFEST,
    MATURITY,
    validate,
)


ROOT = Path(__file__).resolve().parents[3]


def test_alpha_magical_peach_completion_audit_matches_current_gate():
    errors = validate(AUDIT.read_text(encoding="utf-8"))

    assert errors == []


def test_alpha_magical_peach_completion_audit_rejects_remote_ci_as_proved():
    text = AUDIT.read_text(encoding="utf-8").replace("pending_remote_ci", "proved")

    errors = validate(text)

    assert any(
        "Remote CI success is linked for target HEAD: row must have status pending_remote_ci" in error
        for error in errors
    )


def test_alpha_magical_peach_completion_audit_rejects_production_posture_claim():
    text = AUDIT.read_text(encoding="utf-8").replace(
        "`production_ready: false`",
        "`production_ready: true`",
    )

    errors = validate(text)

    assert any("audit missing global snippet: `production_ready: false`" in error for error in errors)


def test_alpha_magical_peach_completion_audit_rejects_missing_open_gate_id():
    text = AUDIT.read_text(encoding="utf-8").replace("S017-007", "S017-XXX")

    errors = validate(text)

    assert any("audit missing open external gate id: S017-007" in error for error in errors)


def test_alpha_magical_peach_completion_audit_rejects_checked_remote_ci_plan_item():
    plan_text = FALLBACK_PLAN_TEXT.replace(
        "- [ ] Remote CI success is linked for the target HEAD",
        "- [x] Remote CI success is linked for the target HEAD",
    )

    errors = validate(
        AUDIT.read_text(encoding="utf-8"),
        plan_text=plan_text,
        maturity_text=MATURITY.read_text(encoding="utf-8"),
        manifest=json.loads(MANIFEST.read_text(encoding="utf-8")),
    )

    assert any(
        "source plan missing required Alpha/remote-CI snippet: "
        "- [ ] Remote CI success is linked for the target HEAD" in error
        for error in errors
    )
    assert any(
        "source plan must not mark remote CI complete: "
        "- [x] Remote CI success is linked for the target HEAD" in error
        for error in errors
    )


def test_alpha_magical_peach_completion_audit_cli():
    script = ROOT / "scripts" / "validate_alpha_magical_peach_completion_audit.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"passed": true' in result.stdout
