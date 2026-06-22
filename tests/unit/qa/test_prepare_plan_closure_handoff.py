import json
from pathlib import Path
import subprocess
import sys

from scripts.prepare_plan_closure_handoff import prepare_handoff_workspace


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json"


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
    assert payload["closure_gate"]["summary"]["open"] == 6
    assert Path(tmp_path / "handoff" / "handoff.json").exists()
    assert Path(tmp_path / "handoff" / "README.md").exists()
    assert Path(tmp_path / "handoff" / "operator-checklist.md").exists()
    assert Path(tmp_path / "handoff" / "operator-commands.ps1").exists()

    tasks = {task["id"]: task for task in payload["tasks"]}
    assert tasks["S017-002"]["prepared_inputs"] == []
    assert tasks["S017-002"]["workspace_command_plan"]["prepared_input_bindings"] == []
    assert len(tasks["W3-live"]["prepared_inputs"]) == 5
    assert len(tasks["W3-live"]["workspace_command_plan"]["prepared_input_bindings"]) == 5
    assert sum(len(task["prepared_inputs"]) for task in payload["tasks"]) == 9
    assert tasks["S017-003"]["workspace_command_plan"]["resolved_output_ref"] == (
        "production\\qa\\evidence\\provider\\financial-provider-approval-2030-01-02.json"
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
        Path(prepared["prepared_input"])
        for task in payload["tasks"]
        for prepared in task["prepared_inputs"]
    ]
    assert prepared_paths
    assert all("draft-2030-01-02" in path.name for path in prepared_paths)
    assert all((ROOT / path).exists() for path in prepared_paths)
    assert not any(_looks_like_completed_evidence(path.name) for path in prepared_paths)

    readme = (tmp_path / "handoff" / "README.md").read_text(encoding="utf-8")
    assert "does not close any gate" in readme
    assert payload["source_plan_check"]["sha256"] in readme
    assert "operator-commands.ps1" in readme
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
    assert (
        "validate_financial_provider_approval_evidence.py "
        "'production\\qa\\evidence\\provider\\financial-provider-approval-2030-01-02.json'"
    ) in operator_commands
    assert '$analystInitials = "<initials>"' in operator_commands
    assert "$TaskId -in @('all', 'W3-live')" in operator_commands
    assert '--analyst-initials "$analystInitials"' in operator_commands
    assert "if ($TaskId -in @('all', 'S017-003'))" in operator_commands
    assert "Skipping final strict gate for single-task run" in operator_commands
    assert "validate_kimi_plan_completion_audit.py" in operator_commands
    assert "validate_plan_closure_gate.py" in operator_commands


def test_prepare_plan_closure_handoff_quotes_operator_paths_with_spaces(tmp_path):
    output_dir = tmp_path / "operator window with spaces" / "handoff"

    prepare_handoff_workspace(
        manifest_path=MANIFEST,
        date="2030-01-02",
        output_dir=output_dir,
    )

    operator_commands = (output_dir / "operator-commands.ps1").read_text(encoding="utf-8")

    assert "operator window with spaces" in operator_commands
    assert "Set-Location -LiteralPath $repoRoot" in operator_commands
    assert "& $python scripts\\build_financial_provider_approval_evidence.py" in operator_commands
    assert "'--handoff-workspace'" in operator_commands
    assert "'production\\qa\\evidence\\provider\\financial-provider-approval-2030-01-02.json'" in operator_commands
    assert "'production\\qa\\evidence\\eval\\analyst-benchmark-2030-01-02.json'" in operator_commands
    assert "'production\\qa\\evidence\\manual\\research-agent-screen-reader-manual-2030-01-02.json'" in operator_commands
    assert "'production\\qa\\evidence\\sdk\\sdk-release-approval-2030-01-02.json'" in operator_commands
    assert "'production\\qa\\evidence\\enterprise\\enterprise-production-validation-2030-01-02.json'" in operator_commands
    assert "'production\\qa\\evidence\\live\\kimi-live-smoke-2026-06-22.json'" in operator_commands
    assert "\\operator window with spaces\\handoff\\inputs\\s017-003\\provider-decisions-draft-2030-01-02.json'" in operator_commands
    assert "--created-at \"$createdAt\"" in operator_commands


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
