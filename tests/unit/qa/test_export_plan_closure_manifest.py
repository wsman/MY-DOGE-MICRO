import json
from pathlib import Path
import subprocess
import sys

from scripts.export_plan_closure_manifest import build_manifest


ROOT = Path(__file__).resolve().parents[3]


def test_build_plan_closure_manifest_from_gate_output():
    manifest = build_manifest(generated_at="2026-06-22T00:00:00+00:00")

    assert manifest["schema"] == "doge.plan_closure_execution_manifest.v1"
    assert manifest["generated_at"] == "2026-06-22T00:00:00+00:00"
    assert manifest["source_plan_check"]["path"] == manifest["source_plan"]
    assert manifest["source_plan_check"]["exists"] is True
    assert len(manifest["source_plan_check"]["sha256"]) == 64
    assert manifest["source_plan_check"]["bytes"] > 0
    assert manifest["closure_gate"]["result"] == "open"
    assert manifest["closure_gate"]["acceptable_with_open_items"] is True
    assert manifest["closure_gate"]["summary"] == {
        "total": 6,
        "passed": 0,
        "open": 6,
        "failed": 0,
        "invalid": 0,
    }
    assert manifest["closure_gate"]["posture"]["production_ready_false"] is True
    assert manifest["closure_gate"]["posture"]["stable_declaration_forbidden"] is True
    assert {item["id"] for item in manifest["tasks"]} == {
        "S017-002",
        "S017-003",
        "W3-live",
        "AUTH-prod",
        "S017-006",
        "S017-007",
    }
    assert all(item["current_status"] == "open" for item in manifest["tasks"])
    assert all(item["can_close_now"] is False for item in manifest["tasks"])
    assert all(item["validator_command"].startswith(".\\.venv\\Scripts\\python.exe scripts\\validate_") for item in manifest["tasks"])
    assert all(item["current_evidence"] in item["validator_command"] for item in manifest["tasks"])
    assert all(item["handoff"]["input_refs"] for item in manifest["tasks"])
    assert all(item["handoff"]["build_or_run_command"].startswith(".\\.venv\\Scripts\\python.exe scripts\\") for item in manifest["tasks"])
    assert all("YYYY-MM-DD" in item["handoff"]["output_ref"] or item["id"] == "S017-002" for item in manifest["tasks"])
    assert all("input_templates" in item["handoff"] for item in manifest["tasks"])

    required = {item["id"]: item["required_results"] for item in manifest["tasks"]}
    assert required["S017-002"] == ["passed"]
    assert required["S017-003"] == ["approved"]
    assert required["W3-live"] == ["passed"]
    assert required["AUTH-prod"] == ["passed"]
    assert required["S017-006"] == ["passed"]
    assert required["S017-007"] == ["approved"]

    handoff = {item["id"]: item["handoff"] for item in manifest["tasks"]}
    assert handoff["S017-002"]["kind"] == "live_runner"
    assert "env:DOGE_LIVE_KIMI=1" in handoff["S017-002"]["input_refs"]
    assert "run_kimi_live_smoke.py" in handoff["S017-002"]["build_or_run_command"]
    assert handoff["S017-003"]["kind"] == "evidence_builder"
    assert handoff["S017-003"]["input_templates"] == [
        "production\\qa\\evidence\\provider\\provider-decisions-template-2026-06-22.json"
    ]
    assert "build_financial_provider_approval_evidence.py" in handoff["S017-003"]["build_or_run_command"]
    assert len(handoff["W3-live"]["input_templates"]) == 5
    assert "build_analyst_benchmark_evidence.py" in handoff["W3-live"]["build_or_run_command"]
    assert handoff["AUTH-prod"]["input_templates"] == [
        "production\\qa\\evidence\\enterprise\\enterprise-production-observations-template-2026-06-22.json"
    ]
    assert "build_enterprise_production_validation_evidence.py" in handoff["AUTH-prod"]["build_or_run_command"]
    assert handoff["S017-006"]["input_templates"] == [
        "production\\qa\\evidence\\manual\\screen-reader-observations-template-2026-06-22.json"
    ]
    assert "build_screen_reader_evidence.py" in handoff["S017-006"]["build_or_run_command"]
    assert handoff["S017-007"]["input_templates"] == [
        "production\\qa\\evidence\\sdk\\sdk-release-decisions-template-2026-06-22.json"
    ]
    assert "build_sdk_release_approval_evidence.py" in handoff["S017-007"]["build_or_run_command"]


def test_export_plan_closure_manifest_cli_writes_json(tmp_path):
    script = ROOT / "scripts" / "export_plan_closure_manifest.py"
    output = tmp_path / "manifest.json"

    result = subprocess.run(
        [sys.executable, str(script), "--output", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "doge.plan_closure_execution_manifest.v1"
    assert len(payload["tasks"]) == 6
    stdout = json.loads(result.stdout)
    assert stdout["tasks"] == 6
