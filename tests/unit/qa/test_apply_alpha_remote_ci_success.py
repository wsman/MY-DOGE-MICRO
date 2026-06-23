from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from scripts.apply_alpha_remote_ci_success import apply_updates
from scripts.validate_alpha_final_closure import validate as validate_final_closure
from scripts.verify_remote_ci_evidence import SCHEMA


ROOT = Path(__file__).resolve().parents[3]
SHA = "e6398dab7975f130770608f411604d51ec300e43"
SHORT_SHA = "e6398da"
EVIDENCE_REF = f"production/qa/evidence/ci/remote-ci-{SHORT_SHA}.json"
RUN_URL = "https://github.com/wsman/MY-DOGE-MICRO/actions/runs/27967339069"


def test_apply_alpha_remote_ci_success_updates_plan_and_maturity_for_final_closure():
    root = Path("D:/test-root")
    result = apply_updates(
        remote_ci_payload=_payload(),
        evidence_path=root / EVIDENCE_REF,
        expected_head_sha=SHA,
        plan_text=_pending_plan_text(),
        maturity_text=_maturity_text(),
        root=root,
    )

    assert result["passed"] is True
    assert result["errors"] == []
    assert "- [x] Target HEAD is recorded: `e6398da` /" in result["plan_text"]
    assert "- [x] Remote CI success is linked for the target HEAD" in result["plan_text"]
    assert "alpha_magical_peach_final_closure:" in result["maturity_text"]
    assert validate_final_closure(
        _payload(),
        evidence_path=root / EVIDENCE_REF,
        expected_head_sha=SHA,
        plan_text=result["plan_text"],
        maturity_text=result["maturity_text"],
        gate_output=_controlled_open_gate(),
        root=root,
    ) == []


def test_apply_alpha_remote_ci_success_rejects_failed_evidence():
    payload = _payload(conclusion="failure", result="pending_remote_ci", wait_status="terminal_failure")

    result = apply_updates(
        remote_ci_payload=payload,
        evidence_path=ROOT / EVIDENCE_REF,
        expected_head_sha=SHA,
        plan_text=_pending_plan_text(),
        maturity_text=_maturity_text(),
    )

    assert result["passed"] is False
    assert any("remote CI evidence result must be passed" in error for error in result["errors"])


def test_apply_alpha_remote_ci_success_rejects_missing_plan_checklist_line():
    plan_text = _pending_plan_text().replace(
        "- [ ] Remote CI success is linked for the target HEAD; current handoff is `docs/archive/audits/remote-ci-handoff-2026-06-23.md`.",
        "",
    )

    result = apply_updates(
        remote_ci_payload=_payload(),
        evidence_path=ROOT / EVIDENCE_REF,
        expected_head_sha=SHA,
        plan_text=plan_text,
        maturity_text=_maturity_text(),
    )

    assert "could not update target HEAD remote CI checklist item" in result["errors"]


def test_apply_alpha_remote_ci_success_cli_dry_run_does_not_write(tmp_path):
    evidence = tmp_path / EVIDENCE_REF
    evidence.parent.mkdir(parents=True)
    evidence.write_text(json.dumps(_payload()), encoding="utf-8")
    plan = tmp_path / "plan.md"
    maturity = tmp_path / "runtime-maturity.yaml"
    plan.write_text(_pending_plan_text(), encoding="utf-8")
    maturity.write_text(_maturity_text(), encoding="utf-8")
    script = ROOT / "scripts" / "apply_alpha_remote_ci_success.py"

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
    assert '"written": false' in result.stdout
    assert "- [ ] Remote CI success is linked for the target HEAD" in plan.read_text(encoding="utf-8")


def test_apply_alpha_remote_ci_success_cli_write(tmp_path):
    evidence = tmp_path / EVIDENCE_REF
    evidence.parent.mkdir(parents=True)
    evidence.write_text(json.dumps(_payload()), encoding="utf-8")
    plan = tmp_path / "plan.md"
    maturity = tmp_path / "runtime-maturity.yaml"
    plan.write_text(_pending_plan_text(), encoding="utf-8")
    maturity.write_text(_maturity_text(), encoding="utf-8")
    script = ROOT / "scripts" / "apply_alpha_remote_ci_success.py"

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
            "--write",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"written": true' in result.stdout
    assert "- [x] Remote CI success is linked for the target HEAD" in plan.read_text(encoding="utf-8")
    assert "alpha_magical_peach_final_closure:" in maturity.read_text(encoding="utf-8")


def _payload(
    *,
    conclusion: str = "success",
    result: str = "passed",
    wait_status: str = "success",
) -> dict[str, object]:
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
                "conclusion": conclusion,
                "head_sha": SHA,
                "html_url": RUN_URL,
                "created_at": "2026-06-22T16:19:12Z",
                "updated_at": "2026-06-22T16:21:47Z",
            }
        ],
        "result": result,
        "wait": {
            "enabled": True,
            "attempts": 3,
            "status": wait_status,
            "timeout_seconds": 1800,
            "poll_interval_seconds": 15,
        },
    }


def _pending_plan_text() -> str:
    return """
## Current DoD Snapshot

- [x] Target HEAD is recorded: `e6398da`.
- [ ] Remote CI success is linked for the repaired target SHA; current handoff is `docs/archive/audits/remote-ci-handoff-2026-06-23.md`.
- [x] Strict closure gate does not pass yet; the plan explicitly remains Alpha with controlled open gates.
- [x] Five external gates still need real evidence and current blocker cards in `docs/archive/audits/external-gate-next-actions-2026-06-23.md`.

## Definition of Done

- [x] Target HEAD is recorded.
- [ ] Remote CI success is linked for the target HEAD; current handoff is `docs/archive/audits/remote-ci-handoff-2026-06-23.md`.
- [x] `production_ready: false`, `stable_declaration: forbidden`, and Level 3 `experimental` remain unchanged.
"""


def _maturity_text() -> str:
    return """
stable_declaration: forbidden
maturity_labels:
  level_3_sdk_platform: experimental
  production_ready: false
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
