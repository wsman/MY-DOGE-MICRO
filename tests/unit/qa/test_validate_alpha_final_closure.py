from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from scripts.validate_alpha_final_closure import validate
from scripts.verify_remote_ci_evidence import SCHEMA


ROOT = Path(__file__).resolve().parents[3]
SHA = "e6398dab7975f130770608f411604d51ec300e43"
SHORT_SHA = "e6398da"
EVIDENCE_REF = f"production/qa/evidence/ci/remote-ci-{SHORT_SHA}.json"
RUN_URL = "https://github.com/wsman/MY-DOGE-MICRO/actions/runs/27967339069"


def test_alpha_final_closure_accepts_finalized_plan_and_maturity():
    root = Path("D:/test-root")
    errors = validate(
        _payload(),
        evidence_path=root / EVIDENCE_REF,
        expected_head_sha=SHA,
        plan_text=_plan_text(),
        maturity_text=_maturity_text(),
        gate_output=_controlled_open_gate(),
        root=root,
    )

    assert errors == []


def test_alpha_final_closure_rejects_unchecked_remote_ci_plan_item():
    plan_text = _plan_text().replace(
        "- [x] Remote CI success is linked for the target HEAD",
        "- [ ] Remote CI success is linked for the target HEAD",
    )

    errors = validate(
        _payload(),
        evidence_path=ROOT / EVIDENCE_REF,
        expected_head_sha=SHA,
        plan_text=plan_text,
        maturity_text=_maturity_text(),
        gate_output=_controlled_open_gate(),
    )

    assert any("final plan must not leave remote CI unchecked" in error for error in errors)


def test_alpha_final_closure_rejects_missing_run_url_in_maturity():
    maturity_text = _maturity_text().replace(RUN_URL, "https://example.invalid/run")

    errors = validate(
        _payload(),
        evidence_path=ROOT / EVIDENCE_REF,
        expected_head_sha=SHA,
        plan_text=_plan_text(),
        maturity_text=maturity_text,
        gate_output=_controlled_open_gate(),
    )

    assert f"runtime maturity missing remote CI success run URL: {RUN_URL}" in errors


def test_alpha_final_closure_rejects_bad_remote_ci_evidence_path():
    errors = validate(
        _payload(),
        evidence_path="production/qa/evidence/ci/remote-ci-wrong.json",
        expected_head_sha=SHA,
        plan_text=_plan_text(),
        maturity_text=_maturity_text(),
        gate_output=_controlled_open_gate(),
    )

    assert any("canonical target-SHA path" in error for error in errors)


def test_alpha_final_closure_rejects_hollow_gate_summary():
    errors = validate(
        _payload(),
        evidence_path=ROOT / EVIDENCE_REF,
        expected_head_sha=SHA,
        plan_text=_plan_text(),
        maturity_text=_maturity_text(),
        gate_output={
            "acceptable": True,
            "result": "open",
            "summary": {"total": 6, "open": 5, "passed": 1, "failed": 0, "invalid": 0},
        },
    )

    assert "closure gate output schema must be doge.plan_closure_gate.v1" in errors
    assert "closure gate output must include gates list" in errors


def test_alpha_final_closure_cli(tmp_path):
    evidence = tmp_path / EVIDENCE_REF
    evidence.parent.mkdir(parents=True)
    evidence.write_text(json.dumps(_payload()), encoding="utf-8")
    plan = tmp_path / "plan.md"
    maturity = tmp_path / "runtime-maturity.yaml"
    plan.write_text(_plan_text(), encoding="utf-8")
    maturity.write_text(_maturity_text(), encoding="utf-8")
    script = ROOT / "scripts" / "validate_alpha_final_closure.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--remote-ci-evidence",
            str(evidence),
            "--expected-head",
            SHA,
            "--plan",
            str(plan),
            "--maturity",
            str(maturity),
            "--root",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"passed": true' in result.stdout


def _payload() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "generated_at": "2026-06-23T00:00:00Z",
        "repo": "wsman/MY-DOGE-MICRO",
        "head_sha": SHA,
        "required_workflow_name": "CI",
        "query_url": (
            "https://api.github.com/repos/wsman/MY-DOGE-MICRO/actions/runs"
            f"?head_sha={SHA}&per_page=20"
        ),
        "total_count": 1,
        "runs": [
            {
                "id": 27967339069,
                "name": "CI",
                "event": "push",
                "status": "completed",
                "conclusion": "success",
                "head_sha": SHA,
                "html_url": RUN_URL,
                "created_at": "2026-06-22T16:19:12Z",
                "updated_at": "2026-06-22T16:21:47Z",
            }
        ],
        "result": "passed",
        "wait": {
            "enabled": True,
            "attempts": 3,
            "status": "success",
            "timeout_seconds": 1800,
            "poll_interval_seconds": 15,
        },
    }


def _plan_text() -> str:
    return f"""
## Current DoD Snapshot

- [x] Target HEAD is recorded: `{SHORT_SHA}` / `{SHA}`.
- [x] Remote CI success is linked for the repaired target SHA: `{RUN_URL}` with `{EVIDENCE_REF}`.
- [x] Strict closure gate does not pass yet; the plan explicitly remains Alpha with controlled open gates.
- [x] Five external gates still need real evidence and current blocker cards in `docs/archive/audits/external-gate-next-actions-2026-06-23.md`.

## Definition of Done

- [x] Target HEAD is recorded.
- [x] Remote CI success is linked for the target HEAD: `{RUN_URL}` and `{EVIDENCE_REF}`.
- [x] `production_ready: false`, `stable_declaration: forbidden`, and Level 3 `experimental` remain unchanged.

```yaml
stable_declaration: forbidden
level_3: experimental
production_ready: false
```
"""


def _maturity_text() -> str:
    return f"""
stable_declaration: forbidden
maturity_labels:
  level_3_sdk_platform: experimental
  production_ready: false
local_verification:
  remote_ci_final:
    head_sha: {SHA}
    evidence: {EVIDENCE_REF}
    run_url: {RUN_URL}
"""


def _controlled_open_gate() -> dict[str, object]:
    return {
        "schema": "doge.plan_closure_gate.v1",
        "acceptable": True,
        "result": "open",
        "summary": {"total": 6, "open": 5, "passed": 1, "failed": 0, "invalid": 0},
        "gates": [
            _gate("S017-002", "open", "blocked"),
            _gate("S017-003", "open", "not_run"),
            _gate("W3-live", "open", "not_run"),
            _gate("AUTH-prod", "open", "not_run"),
            _gate("S017-006", "passed", "passed"),
            _gate("S017-007", "open", "not_run"),
        ],
    }


def _gate(gate_id: str, status: str, evidence_result: str) -> dict[str, object]:
    return {
        "id": gate_id,
        "title": gate_id,
        "status": status,
        "evidence": f"production/qa/evidence/{gate_id}.json",
        "evidence_result": evidence_result,
        "next_action": "complete operator evidence",
        "passing_results": ["passed"],
        "strict_command": f"validate {gate_id}",
        "strict_errors": [] if status == "passed" else ["not complete"],
    }
