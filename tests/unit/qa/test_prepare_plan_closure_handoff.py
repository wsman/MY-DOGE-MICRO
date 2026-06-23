import json
from pathlib import Path
import subprocess
import sys

from scripts.prepare_plan_closure_handoff import prepare_handoff_workspace


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json"
GATE_SLUGS = {
    "S017-002": "s017-002",
    "S017-003": "s017-003",
    "W3-live": "w3-live",
    "AUTH-prod": "auth-prod",
    "S017-006": "s017-006",
    "S017-007": "s017-007",
}


def test_prepare_plan_closure_handoff_copies_draft_inputs_without_closing_gates(tmp_path):
    payload = prepare_handoff_workspace(
        manifest_path=MANIFEST,
        date="2030-01-02",
        output_dir=tmp_path / "handoff",
    )

    assert payload["schema"] == "doge.plan_closure_handoff_workspace.v1"
    assert payload["does_not_close_gates"] is True
    assert payload["source_plan_check"]["exists"] is True
    assert len(payload["source_plan_check"]["sha256"]) == 64
    assert len(payload["tasks"]) == 6
    assert payload["closure_gate"]["summary"]["open"] == 5
    assert payload["closure_gate"]["summary"]["passed"] == 1
    assert Path(tmp_path / "handoff" / "handoff.json").exists()
    assert Path(tmp_path / "handoff" / "README.md").exists()
    assert Path(tmp_path / "handoff" / "operator-checklist.md").exists()
    assert Path(tmp_path / "handoff" / "operator-commands.ps1").exists()
    for gate_id, slug in GATE_SLUGS.items():
        guide = tmp_path / "handoff" / "inputs" / slug / "operator-input-guide.md"
        assert guide.exists()
        guide_text = guide.read_text(encoding="utf-8")
        assert gate_id in guide_text
        assert "does not close gates" in guide_text
        assert "Do not place secrets" in guide_text
        assert "Completed evidence belongs in" in guide_text
        assert "Templates and copied drafts are not evidence" in guide_text
        assert "preflight_plan_closure_external.py --require-external-inputs" in guide_text
        assert "operator-commands.ps1" in guide_text

    tasks = {task["id"]: task for task in payload["tasks"]}
    assert tasks["S017-002"]["prepared_inputs"] == []
    assert _norm(tasks["S017-002"]["operator_input_guide"]).endswith(
        "inputs/s017-002/operator-input-guide.md"
    )
    assert tasks["S017-002"]["workspace_command_plan"]["prepared_input_bindings"] == []
    assert len(tasks["W3-live"]["prepared_inputs"]) == 5
    assert len(tasks["W3-live"]["workspace_command_plan"]["prepared_input_bindings"]) == 5
    assert sum(len(task["prepared_inputs"]) for task in payload["tasks"]) == 9
    assert _norm(tasks["S017-003"]["workspace_command_plan"]["resolved_output_ref"]) == (
        "production/qa/evidence/provider/financial-provider-approval-2030-01-02.json"
    )
    assert "provider-decisions-draft-2030-01-02.json" in tasks["S017-003"]["workspace_command_plan"]["command_with_draft_inputs"]
    assert "financial-provider-approval-2030-01-02.json" in tasks["S017-003"]["workspace_command_plan"]["command_with_draft_inputs"]
    assert "$createdAt" in tasks["S017-003"]["workspace_command_plan"]["requires_operator_values"]
    assert "<initials>" in tasks["W3-live"]["workspace_command_plan"]["requires_operator_values"]
    assert "$createdAt" in tasks["W3-live"]["workspace_command_plan"]["requires_operator_values"]
    assert all(
        task["workspace_command_plan"]["writes_completed_evidence_to_workspace"] is False
        for task in payload["tasks"]
    )

    prepared_paths = [
        Path(prepared["prepared_input"].replace("\\", "/"))
        for task in payload["tasks"]
        for prepared in task["prepared_inputs"]
    ]
    assert prepared_paths
    assert all("draft-2030-01-02" in path.name for path in prepared_paths)
    assert all((ROOT / path).exists() for path in prepared_paths)
    assert not any(_looks_like_completed_evidence(path.name) for path in prepared_paths)
    prepared_items = [
        prepared
        for task in payload["tasks"]
        for prepared in task["prepared_inputs"]
    ]
    assert all(prepared["action"] == "copied_template_for_operator_edit" for prepared in prepared_items)
    assert all(prepared["differs_from_source_template"] is False for prepared in prepared_items)
    assert all(len(prepared["source_template_sha256"]) == 64 for prepared in prepared_items)
    assert all(len(prepared["prepared_input_sha256"]) == 64 for prepared in prepared_items)

    readme = (tmp_path / "handoff" / "README.md").read_text(encoding="utf-8")
    assert "does not close any gate" in readme
    assert payload["source_plan_check"]["sha256"] in readme
    assert "operator-commands.ps1" in readme
    assert "operator-input-guide.md" in readme
    assert "Prepared draft inputs: none" in readme
    assert "Workspace command" in readme
    assert "Draft input bindings" in readme
    for gate_id in ["S017-002", "S017-003", "W3-live", "AUTH-prod", "S017-006", "S017-007"]:
        assert gate_id in readme

    checklist = (tmp_path / "handoff" / "operator-checklist.md").read_text(encoding="utf-8")
    assert "does not close gates" in checklist
    assert payload["source_plan_check"]["sha256"] in checklist
    assert "Do not place secrets" in checklist
    assert "## Quick Start" in checklist
    assert "operator-input-guide.md" in checklist
    assert "## Task Checklist" in checklist
    assert "operator-commands.ps1" in checklist
    assert "-TaskId S017-003" in checklist
    assert "-RunFinalGate" in checklist
    assert "Templates and copied drafts are not evidence" in checklist
    assert "Redaction and security-review flags must be explicit `false`" in checklist
    assert "production_ready: false" in checklist
    assert "stable_declaration: forbidden" in checklist
    assert "provider-decisions-draft-2030-01-02.json" in checklist
    assert "financial-provider-approval-2030-01-02.json" in checklist
    assert "validate_financial_provider_approval_evidence.py" in checklist
    for gate_id in ["S017-002", "S017-003", "W3-live", "AUTH-prod", "S017-006", "S017-007"]:
        assert gate_id in checklist

    operator_commands = (tmp_path / "handoff" / "operator-commands.ps1").read_text(encoding="utf-8")
    assert "does not prove closure" in operator_commands
    assert "Do not put secrets" in operator_commands
    assert "$repoRoot = " in operator_commands
    assert str(ROOT) in operator_commands
    assert "param(" in operator_commands
    assert "[ValidateSet('all', 'S017-002', 'S017-003', 'W3-live', 'AUTH-prod', 'S017-006', 'S017-007')]" in operator_commands
    assert "[string]$TaskId = 'all'" in operator_commands
    assert "[switch]$RunFinalGate" in operator_commands
    assert "Set-Location -LiteralPath $repoRoot" in operator_commands
    assert "$python = Join-Path $repoRoot '.venv\\Scripts\\python.exe'" in operator_commands
    assert "Test-Path -LiteralPath $python" in operator_commands
    assert "& $python @preflightArgs" in operator_commands
    assert ".\\.venv\\Scripts\\python.exe" not in operator_commands
    assert "preflight_plan_closure_external.py" in operator_commands
    assert "--require-external-inputs" in operator_commands
    assert "$preflightArgs += @('--task-id', $TaskId)" in operator_commands
    assert "provider-decisions-draft-2030-01-02.json" in operator_commands
    assert "financial-provider-approval-2030-01-02.json" in operator_commands
    normalized_operator_commands = _norm(operator_commands)
    assert (
        "validate_financial_provider_approval_evidence.py "
        "'production/qa/evidence/provider/financial-provider-approval-2030-01-02.json'"
    ) in normalized_operator_commands
    assert '$analystInitials = "<initials>"' in operator_commands
    assert "$TaskId -in @('all', 'W3-live')" in operator_commands
    assert '--analyst-initials "$analystInitials"' in operator_commands
    assert "if ($TaskId -in @('all', 'S017-003'))" in operator_commands
    assert "Skipping final strict gate for single-task run" in operator_commands
    assert "validate_kimi_plan_completion_audit.py" in operator_commands
    assert "validate_glowing_weaving_kettle_completion_audit.py" in operator_commands
    assert "validate_plan_closure_gate.py" in operator_commands


def test_prepare_plan_closure_handoff_quotes_operator_paths_with_spaces(tmp_path):
    output_dir = tmp_path / "operator window with spaces" / "handoff"

    prepare_handoff_workspace(
        manifest_path=MANIFEST,
        date="2030-01-02",
        output_dir=output_dir,
    )

    operator_commands = (output_dir / "operator-commands.ps1").read_text(encoding="utf-8")
    normalized_operator_commands = _norm(operator_commands)

    assert "operator window with spaces" in operator_commands
    assert "Set-Location -LiteralPath $repoRoot" in operator_commands
    assert "& $python scripts\\build_financial_provider_approval_evidence.py" in operator_commands
    assert "'--handoff-workspace'" in operator_commands
    assert "'production/qa/evidence/provider/financial-provider-approval-2030-01-02.json'" in normalized_operator_commands
    assert "'production/qa/evidence/eval/analyst-benchmark-2030-01-02.json'" in normalized_operator_commands
    assert "'production/qa/evidence/manual/research-agent-screen-reader-manual-2030-01-02.json'" in normalized_operator_commands
    assert "'production/qa/evidence/sdk/sdk-release-approval-2030-01-02.json'" in normalized_operator_commands
    assert "'production/qa/evidence/enterprise/enterprise-production-validation-2030-01-02.json'" in normalized_operator_commands
    assert "'production/qa/evidence/live/kimi-live-smoke-2026-06-22.json'" in normalized_operator_commands
    assert "/operator window with spaces/handoff/inputs/s017-003/provider-decisions-draft-2030-01-02.json'" in normalized_operator_commands
    assert "--created-at \"$createdAt\"" in operator_commands


def test_prepare_plan_closure_handoff_preserves_existing_operator_drafts(tmp_path):
    output_dir = tmp_path / "handoff"
    draft = output_dir / "inputs" / "s017-006" / "screen-reader-observations-draft-2030-01-02.json"
    draft.parent.mkdir(parents=True)
    draft.write_text('{"result": "passed", "operator": "already-filled"}\n', encoding="utf-8")
    template_draft = output_dir / "inputs" / "s017-003" / "provider-decisions-draft-2030-01-02.json"
    template_draft.parent.mkdir(parents=True)
    template_draft.write_bytes(
        (ROOT / "production/qa/evidence/provider/provider-decisions-template-2026-06-22.json").read_bytes()
    )

    payload = prepare_handoff_workspace(
        manifest_path=MANIFEST,
        date="2030-01-02",
        output_dir=output_dir,
    )

    assert draft.read_text(encoding="utf-8") == '{"result": "passed", "operator": "already-filled"}\n'
    manual_task = next(item for item in payload["tasks"] if item["id"] == "S017-006")
    manual_input = manual_task["prepared_inputs"][0]
    assert manual_input["action"] == "preserved_existing_operator_draft"
    assert manual_input["differs_from_source_template"] is True
    provider_task = next(item for item in payload["tasks"] if item["id"] == "S017-003")
    provider_input = provider_task["prepared_inputs"][0]
    assert provider_input["action"] == "preserved_existing_template_draft"
    assert provider_input["differs_from_source_template"] is False


def test_prepare_plan_closure_handoff_cli_writes_summary(tmp_path):
    script = ROOT / "scripts" / "prepare_plan_closure_handoff.py"
    output_dir = tmp_path / "operator-window"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--manifest",
            str(MANIFEST),
            "--date",
            "2030-01-02",
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["tasks"] == 6
    assert summary["prepared_inputs"] == 9
    assert summary["operator_input_guides"] == 6
    assert summary["does_not_close_gates"] is True
    assert summary["operator_commands"].endswith("operator-commands.ps1")
    assert summary["operator_checklist"].endswith("operator-checklist.md")
    assert (output_dir / "handoff.json").exists()
    assert (output_dir / "README.md").exists()
    assert (output_dir / "operator-checklist.md").exists()
    assert (output_dir / "operator-commands.ps1").exists()


def _looks_like_completed_evidence(filename: str) -> bool:
    completed_prefixes = [
        "financial-provider-approval-",
        "analyst-benchmark-",
        "enterprise-production-validation-",
        "research-agent-screen-reader-manual-",
        "sdk-release-approval-",
    ]
    return any(filename.startswith(prefix) and "draft" not in filename for prefix in completed_prefixes)


def _norm(value: str) -> str:
    return value.replace("\\", "/")
