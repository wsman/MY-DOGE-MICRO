import json
import os
from pathlib import Path
import subprocess
import sys

from scripts.validate_plan_closure_gate import EvidenceGate, _gate_result, _resolve_evidence_path, _validate_gate, validate_all


ROOT = Path(__file__).resolve().parents[3]


def test_plan_closure_gate_reports_controlled_open_items():
    result = validate_all(allow_open=True)

    assert result["schema"] == "doge.plan_closure_gate.v1"
    assert result["result"] == "open"
    assert result["acceptable"] is True
    assert result["summary"] == {
        "total": 6,
        "passed": 2,
        "open": 4,
        "failed": 0,
        "invalid": 0,
    }
    assert {item["id"] for item in result["gates"]} == {
        "S017-002",
        "S017-003",
        "W3-live",
        "AUTH-prod",
        "S017-006",
        "S017-007",
    }
    for gate in result["gates"]:
        assert gate["next_action"]
        assert gate["strict_command"].startswith(".\\.venv\\Scripts\\python.exe scripts\\validate_")
        assert gate["evidence"] in gate["strict_command"]
        if gate["id"] in {"S017-002", "S017-006"}:
            assert gate["status"] == "passed"
            assert gate["strict_errors"] == []
            if gate["id"] == "S017-002":
                assert gate["evidence"].endswith("kimi-live-smoke-2026-06-29.json")
            else:
                assert gate["evidence"].endswith("research-agent-screen-reader-manual-2026-06-22.json")
        else:
            assert gate["status"] == "open"
            assert gate["strict_errors"]
        assert gate["fallback_evidence"]
        assert gate["passing_results"] in (["approved"], ["passed"])
    assert result["posture"]["production_ready_false"] is True
    assert result["posture"]["stable_declaration_forbidden"] is True
    assert result["posture"]["errors"] == []


def test_plan_closure_gate_strict_mode_does_not_accept_open_items():
    result = validate_all()

    assert result["result"] == "open"
    assert result["acceptable"] is False
    assert result["summary"]["open"] == 4
    assert result["summary"]["passed"] == 2
    assert [item["status"] for item in result["gates"]].count("open") == 4
    assert [item["status"] for item in result["gates"]].count("passed") == 2
    assert all(item["strict_errors"] for item in result["gates"] if item["status"] == "open")
    assert all(item["strict_errors"] == [] for item in result["gates"] if item["status"] == "passed")
    assert all(item["next_action"] for item in result["gates"])


def test_plan_closure_gate_cli_requires_allow_open_for_zero_exit():
    script = ROOT / "scripts" / "validate_plan_closure_gate.py"
    strict = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    allowed = subprocess.run(
        [sys.executable, str(script), "--allow-open"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert strict.returncode == 1
    strict_payload = json.loads(strict.stdout)
    assert strict_payload["acceptable"] is False
    assert strict_payload["summary"]["open"] == 4
    assert strict_payload["summary"]["passed"] == 2

    assert allowed.returncode == 0
    allowed_payload = json.loads(allowed.stdout)
    assert allowed_payload["acceptable"] is True
    assert allowed_payload["summary"]["open"] == 4
    assert allowed_payload["summary"]["passed"] == 2


def test_plan_closure_gate_prefers_completed_evidence_over_template(tmp_path):
    fallback = tmp_path / "research-agent-screen-reader-manual-template-2026-06-22.json"
    older = tmp_path / "research-agent-screen-reader-manual-2026-06-22.json"
    newer = tmp_path / "research-agent-screen-reader-manual-2026-06-23.json"
    for path in [fallback, older, newer]:
        path.write_text("{}", encoding="utf-8")
    os.utime(older, (100, 100))
    os.utime(newer, (200, 200))
    gate = EvidenceGate(
        gate_id="test",
        title="test",
        path=fallback,
        validator=lambda payload, **kwargs: [],
        allow_kwarg="allow_template",
        open_results=frozenset({"not_run"}),
        passing_results=frozenset({"passed"}),
        next_action="complete evidence",
        strict_command="validate fallback",
        completed_glob="research-agent-screen-reader-manual-*.json",
    )

    assert _resolve_evidence_path(gate) == newer


def test_plan_closure_gate_ignores_template_when_glob_matches(tmp_path):
    fallback = tmp_path / "sdk-release-approval-template-2026-06-22.json"
    matching_template = tmp_path / "sdk-release-approval-template-2026-06-23.json"
    completed = tmp_path / "sdk-release-approval-2026-06-22.json"
    for path in [fallback, matching_template, completed]:
        path.write_text("{}", encoding="utf-8")
    os.utime(completed, (100, 100))
    os.utime(matching_template, (200, 200))
    gate = EvidenceGate(
        gate_id="test",
        title="test",
        path=fallback,
        validator=lambda payload, **kwargs: [],
        allow_kwarg="allow_template",
        open_results=frozenset({"not_run"}),
        passing_results=frozenset({"approved"}),
        next_action="complete evidence",
        strict_command="validate fallback",
        completed_glob="sdk-release-approval-*.json",
    )

    assert _resolve_evidence_path(gate) == completed


def test_plan_closure_gate_falls_back_when_only_matching_file_is_template(tmp_path):
    fallback = tmp_path / "financial-provider-approval-template-2026-06-22.json"
    matching_template = tmp_path / "financial-provider-approval-template-2026-06-23.json"
    for path in [fallback, matching_template]:
        path.write_text("{}", encoding="utf-8")
    os.utime(matching_template, (200, 200))
    gate = EvidenceGate(
        gate_id="test",
        title="test",
        path=fallback,
        validator=lambda payload, **kwargs: [],
        allow_kwarg="allow_template",
        open_results=frozenset({"not_run"}),
        passing_results=frozenset({"approved"}),
        next_action="complete evidence",
        strict_command="validate fallback",
        completed_glob="financial-provider-approval-*.json",
    )

    assert _resolve_evidence_path(gate) == fallback


def test_plan_closure_gate_result_reports_explicit_passing_results():
    gate = EvidenceGate(
        gate_id="test",
        title="test",
        path=ROOT / "example.json",
        validator=lambda payload, **kwargs: [],
        allow_kwarg="allow_template",
        open_results=frozenset({"not_run"}),
        passing_results=frozenset({"approved"}),
        next_action="complete evidence",
        strict_command="validate example.json",
    )

    result = _gate_result(
        gate,
        status="failed",
        result="needs_revision",
        strict_errors=[],
        evidence_path="example.json",
    )

    assert result["evidence_result"] == "needs_revision"
    assert result["passing_results"] == ["approved"]
    assert result["status"] == "failed"


def test_plan_closure_gate_rejects_structurally_valid_non_passing_result(tmp_path):
    evidence = tmp_path / "provider-approval.json"
    evidence.write_text('{"result": "needs_revision"}', encoding="utf-8")
    gate = EvidenceGate(
        gate_id="test",
        title="test",
        path=evidence,
        validator=lambda payload, **kwargs: [],
        allow_kwarg="allow_template",
        open_results=frozenset({"not_run"}),
        passing_results=frozenset({"approved"}),
        next_action="complete evidence",
        strict_command="validate provider-approval.json",
    )

    result = _validate_gate(gate, allow_open=True)

    assert result["status"] == "failed"
    assert result["evidence_result"] == "needs_revision"
    assert result["strict_errors"] == []
    assert result["passing_results"] == ["approved"]
