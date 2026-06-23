from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from scripts.close_alpha_remote_ci_gate import close_remote_ci_gate
from scripts.verify_remote_ci_evidence import SCHEMA


ROOT = Path(__file__).resolve().parents[3]
SHA = "abcdef1234567890abcdef1234567890abcdef12"
RUN_URL = "https://github.com/wsman/MY-DOGE-MICRO/actions/runs/42"


def test_close_remote_ci_gate_dry_run_writes_canonical_evidence_only(tmp_path):
    plan = tmp_path / "alpha.md"
    maturity = tmp_path / "maturity.yaml"
    plan.write_text(_plan_text(), encoding="utf-8")
    maturity.write_text(_maturity_text(), encoding="utf-8")

    result = close_remote_ci_gate(
        remote_ci_payload=_success_payload(),
        output_dir=tmp_path / "production" / "qa" / "evidence" / "ci",
        plan_path=plan,
        maturity_path=maturity,
        write=False,
        gate_output=_gate_output(),
        root=tmp_path,
    )

    assert result["passed"] is True
    assert result["written"] is False
    assert result["stage"] == "closed"
    assert result["remote_ci_evidence"].replace("\\", "/").endswith(
        "production/qa/evidence/ci/remote-ci-abcdef1.json"
    )
    assert Path(result["remote_ci_evidence"]).name == "remote-ci-abcdef1.json"
    assert json.loads(Path(result["remote_ci_evidence"]).read_text(encoding="utf-8"))["head_sha"] == SHA
    assert "- [ ] Remote CI success is linked for the target HEAD" in plan.read_text(encoding="utf-8")


def test_close_remote_ci_gate_write_updates_plan_and_maturity(tmp_path):
    plan = tmp_path / "alpha.md"
    maturity = tmp_path / "maturity.yaml"
    plan.write_text(_plan_text(), encoding="utf-8")
    maturity.write_text(_maturity_text(), encoding="utf-8")

    result = close_remote_ci_gate(
        remote_ci_payload=_success_payload(),
        output_dir=tmp_path / "production" / "qa" / "evidence" / "ci",
        plan_path=plan,
        maturity_path=maturity,
        write=True,
        gate_output=_gate_output(),
        root=tmp_path,
        require_commit_scope=False,
    )

    assert result["passed"] is True
    assert result["written"] is True
    assert result["evidence_ref"] == "production/qa/evidence/ci/remote-ci-abcdef1.json"
    assert "- [x] Remote CI success is linked for the target HEAD" in plan.read_text(encoding="utf-8")
    assert RUN_URL in plan.read_text(encoding="utf-8")
    assert "alpha_magical_peach_final_closure" in maturity.read_text(encoding="utf-8")
    assert SHA in maturity.read_text(encoding="utf-8")


def test_close_remote_ci_gate_rejects_failed_evidence_without_plan_write(tmp_path):
    plan = tmp_path / "alpha.md"
    maturity = tmp_path / "maturity.yaml"
    plan.write_text(_plan_text(), encoding="utf-8")
    maturity.write_text(_maturity_text(), encoding="utf-8")
    payload = _success_payload()
    payload["result"] = "pending_remote_ci"
    payload["runs"][0]["conclusion"] = "failure"
    payload["wait"]["status"] = "terminal_failure"

    result = close_remote_ci_gate(
        remote_ci_payload=payload,
        output_dir=tmp_path / "production" / "qa" / "evidence" / "ci",
        plan_path=plan,
        maturity_path=maturity,
        write=True,
        gate_output=_gate_output(),
        root=tmp_path,
        require_commit_scope=False,
    )

    assert result["passed"] is False
    assert result["stage"] == "remote_ci_success"
    assert result["written"] is False
    assert any("remote CI evidence result must be passed" in error for error in result["errors"])
    assert "- [ ] Remote CI success is linked for the target HEAD" in plan.read_text(encoding="utf-8")


def test_close_remote_ci_gate_fetches_evidence_when_payload_is_absent(tmp_path):
    plan = tmp_path / "alpha.md"
    maturity = tmp_path / "maturity.yaml"
    calls = []
    plan.write_text(_plan_text(), encoding="utf-8")
    maturity.write_text(_maturity_text(), encoding="utf-8")

    def fake_fetcher(**kwargs):
        calls.append(kwargs)
        return _success_payload()

    result = close_remote_ci_gate(
        head_sha=SHA,
        evidence_fetcher=fake_fetcher,
        output_dir=tmp_path / "production" / "qa" / "evidence" / "ci",
        plan_path=plan,
        maturity_path=maturity,
        owner="octo",
        repo="repo",
        workflow_name="CI",
        timeout_seconds=12,
        poll_interval_seconds=3,
        write=False,
        gate_output=_gate_output(),
        root=tmp_path,
    )

    assert result["passed"] is True
    assert calls == [
        {
            "owner": "octo",
            "repo": "repo",
            "head_sha": SHA,
            "workflow_name": "CI",
            "timeout_seconds": 12,
            "poll_interval_seconds": 3,
        }
    ]
    assert Path(result["remote_ci_evidence"]).name == "remote-ci-abcdef1.json"


def test_close_remote_ci_gate_rejects_explicit_head_mismatch(tmp_path):
    plan = tmp_path / "alpha.md"
    maturity = tmp_path / "maturity.yaml"
    mismatched = "1111111111111111111111111111111111111111"
    plan.write_text(_plan_text(), encoding="utf-8")
    maturity.write_text(_maturity_text(), encoding="utf-8")

    result = close_remote_ci_gate(
        head_sha=mismatched,
        remote_ci_payload=_success_payload(),
        output_dir=tmp_path / "production" / "qa" / "evidence" / "ci",
        plan_path=plan,
        maturity_path=maturity,
        write=True,
        gate_output=_gate_output(),
        root=tmp_path,
        require_commit_scope=False,
    )

    assert result["passed"] is False
    assert result["stage"] == "remote_ci_success"
    assert result["written"] is False
    assert any("head_sha must match expected target SHA" in error for error in result["errors"])
    assert "- [ ] Remote CI success is linked for the target HEAD" in plan.read_text(encoding="utf-8")


def test_close_remote_ci_gate_rejects_failed_post_commit_scope_before_write(tmp_path):
    plan = tmp_path / "alpha.md"
    maturity = tmp_path / "maturity.yaml"
    plan.write_text(_plan_text(), encoding="utf-8")
    maturity.write_text(_maturity_text(), encoding="utf-8")

    result = close_remote_ci_gate(
        remote_ci_payload=_success_payload(),
        output_dir=tmp_path / "production" / "qa" / "evidence" / "ci",
        plan_path=plan,
        maturity_path=maturity,
        write=True,
        gate_output=_gate_output(),
        root=tmp_path,
        commit_scope_checker=lambda _sha: ["unexpected material paths in target commit payload: src/unrelated.py"],
    )

    assert result["passed"] is False
    assert result["stage"] == "post_commit_scope"
    assert result["written"] is False
    assert not Path(result["remote_ci_evidence"]).exists()
    assert "- [ ] Remote CI success is linked for the target HEAD" in plan.read_text(encoding="utf-8")


def test_close_remote_ci_gate_cli_uses_existing_evidence_without_network(tmp_path):
    plan = tmp_path / "alpha.md"
    maturity = tmp_path / "maturity.yaml"
    evidence = tmp_path / "input.json"
    out = tmp_path / "production" / "qa" / "evidence" / "ci"
    plan.write_text(_plan_text(), encoding="utf-8")
    maturity.write_text(_maturity_text(), encoding="utf-8")
    evidence.write_text(json.dumps(_success_payload()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "close_alpha_remote_ci_gate.py"),
            "--remote-ci-evidence",
            str(evidence),
            "--output-dir",
            str(out),
            "--plan",
            str(plan),
            "--maturity",
            str(maturity),
            "--root",
            str(tmp_path),
            "--skip-commit-scope",
            "--write",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"passed": true' in result.stdout
    assert '"written": true' in result.stdout
    assert (out / "remote-ci-abcdef1.json").is_file()
    assert "- [x] Remote CI success is linked for the target HEAD" in plan.read_text(encoding="utf-8")


def _success_payload() -> dict:
    return {
        "schema": SCHEMA,
        "generated_at": "2026-06-23T00:00:00Z",
        "repo": "wsman/MY-DOGE-MICRO",
        "head_sha": SHA,
        "required_workflow_name": "CI",
        "query_url": "https://api.github.com/repos/wsman/MY-DOGE-MICRO/actions/runs?head_sha=" + SHA,
        "total_count": 1,
        "runs": [
            {
                "id": 42,
                "name": "CI",
                "event": "push",
                "status": "completed",
                "conclusion": "success",
                "head_sha": SHA,
                "html_url": RUN_URL,
                "created_at": "2026-06-23T00:00:00Z",
                "updated_at": "2026-06-23T00:01:00Z",
            }
        ],
        "result": "passed",
        "wait": {
            "enabled": True,
            "attempts": 1,
            "status": "success",
            "timeout_seconds": 1800,
            "poll_interval_seconds": 15,
        },
    }


def _plan_text() -> str:
    return """
Current DoD Snapshot

- [x] Target HEAD is recorded: `old`.
- [ ] Remote CI success is linked for the repaired target SHA; current handoff is `docs/progress/remote-ci-handoff-2026-06-23.md`.

Definition of Done

- [x] Target HEAD is recorded.
- [ ] Remote CI success is linked for the target HEAD; current handoff is `docs/progress/remote-ci-handoff-2026-06-23.md`.

The plan explicitly remains Alpha with controlled-open Alpha gates.
External gate blockers are tracked in `docs/progress/external-gate-next-actions-2026-06-23.md`.
`production_ready: false`
`stable_declaration: forbidden`
Level 3 `experimental`
"""


def _maturity_text() -> str:
    return """
stable_declaration: forbidden
maturity_labels:
  level_3_sdk_platform: experimental
production_ready: false
"""


def _gate_output() -> dict:
    return {
        "schema": "doge.plan_closure_gate.v1",
        "acceptable": True,
        "result": "open",
        "summary": {"failed": 0, "invalid": 0, "open": 5, "passed": 1, "total": 6},
        "gates": [
            _gate("S017-002", "open", "blocked"),
            _gate("S017-003", "open", "not_run"),
            _gate("W3-live", "open", "not_run"),
            _gate("AUTH-prod", "open", "not_run"),
            _gate("S017-006", "passed", "passed"),
            _gate("S017-007", "open", "not_run"),
        ],
    }


def _gate(gate_id: str, status: str, evidence_result: str) -> dict:
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
