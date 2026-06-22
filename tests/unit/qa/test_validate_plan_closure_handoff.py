import json
from pathlib import Path
import subprocess
import sys

from scripts.prepare_plan_closure_handoff import prepare_handoff_workspace
from scripts.validate_plan_closure_handoff import validate_workspace


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json"


def test_validate_plan_closure_handoff_accepts_fresh_workspace(tmp_path):
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)

    assert validate_workspace(workspace) == []


def test_validate_plan_closure_handoff_rejects_stale_task_metadata(tmp_path):
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    handoff = json.loads((workspace / "handoff.json").read_text(encoding="utf-8"))
    handoff["tasks"][0]["build_or_run_command"] = "stale command"
    (workspace / "handoff.json").write_text(json.dumps(handoff, indent=2), encoding="utf-8")

    errors = validate_workspace(workspace)

    assert any("S017-002: build_or_run_command does not match manifest" in error for error in errors)


def test_validate_plan_closure_handoff_rejects_stale_source_plan_check(tmp_path):
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    handoff = json.loads((workspace / "handoff.json").read_text(encoding="utf-8"))
    handoff["source_plan_check"]["sha256"] = "0" * 64
    (workspace / "handoff.json").write_text(json.dumps(handoff, indent=2), encoding="utf-8")

    errors = validate_workspace(workspace)

    assert any("source_plan_check does not match manifest" in error for error in errors)


def test_validate_plan_closure_handoff_rejects_completed_evidence_in_workspace(tmp_path):
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    (workspace / "inputs" / "s017-003" / "financial-provider-approval-2030-01-02.json").write_text(
        "{}",
        encoding="utf-8",
    )

    errors = validate_workspace(workspace)

    assert any("completed-evidence-looking file" in error for error in errors)


def test_validate_plan_closure_handoff_rejects_command_plan_output_inside_workspace(tmp_path):
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    handoff = json.loads((workspace / "handoff.json").read_text(encoding="utf-8"))
    handoff["tasks"][1]["workspace_command_plan"]["resolved_output_ref"] = str(
        workspace / "financial-provider-approval-2030-01-02.json"
    )
    (workspace / "handoff.json").write_text(json.dumps(handoff, indent=2), encoding="utf-8")

    errors = validate_workspace(workspace)

    assert any("resolved_output_ref must not be inside handoff workspace" in error for error in errors)


def test_validate_plan_closure_handoff_rejects_missing_operator_commands(tmp_path):
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    (workspace / "operator-commands.ps1").unlink()

    errors = validate_workspace(workspace)

    assert any("missing operator commands file" in error for error in errors)


def test_validate_plan_closure_handoff_rejects_missing_operator_checklist(tmp_path):
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    (workspace / "operator-checklist.md").unlink()

    errors = validate_workspace(workspace)

    assert any("missing operator checklist file" in error for error in errors)


def test_validate_plan_closure_handoff_rejects_weak_operator_checklist(tmp_path):
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    (workspace / "operator-checklist.md").write_text("tasks maybe done\n", encoding="utf-8")

    errors = validate_workspace(workspace)

    assert any("does not close gates" in error for error in errors)
    assert any("quick start" in error for error in errors)
    assert any("template-as-evidence" in error for error in errors)
    assert any("explicit false redaction/security-review flags" in error for error in errors)
    assert any("operator checklist missing task id" in error for error in errors)


def test_validate_plan_closure_handoff_rejects_weak_operator_commands(tmp_path):
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    (workspace / "operator-commands.ps1").write_text("no strict command list\n", encoding="utf-8")

    errors = validate_workspace(workspace)

    assert any("do not prove closure" in error for error in errors)
    assert any("external preflight" in error for error in errors)
    assert any("strict closure gate" in error for error in errors)
    assert any("operator commands missing workspace command" in error for error in errors)


def test_validate_plan_closure_handoff_rejects_operator_commands_without_repo_root(tmp_path):
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    commands = (workspace / "operator-commands.ps1").read_text(encoding="utf-8")
    commands = commands.replace("$repoRoot", "$removedRepoRoot")
    commands = commands.replace("Set-Location -LiteralPath $removedRepoRoot", "# missing repo root switch")
    (workspace / "operator-commands.ps1").write_text(commands, encoding="utf-8")

    errors = validate_workspace(workspace)

    assert any("must define the repository root" in error for error in errors)
    assert any("must switch to the repository root" in error for error in errors)


def test_validate_plan_closure_handoff_rejects_operator_commands_without_python_guard(tmp_path):
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    commands = (workspace / "operator-commands.ps1").read_text(encoding="utf-8")
    commands = commands.replace("$python = Join-Path $repoRoot '.venv\\Scripts\\python.exe'", "# missing python path")
    commands = commands.replace("Test-Path -LiteralPath $python", "Test-Path -LiteralPath $missingPython")
    commands = commands.replace("& $python", "& $missingPython")
    (workspace / "operator-commands.ps1").write_text(commands, encoding="utf-8")

    errors = validate_workspace(workspace)

    assert any("must define the Python interpreter path" in error for error in errors)
    assert any("must check the Python interpreter path" in error for error in errors)
    assert any("must invoke Python through the checked interpreter" in error for error in errors)


def test_validate_plan_closure_handoff_rejects_operator_commands_without_task_selection(tmp_path):
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    commands = (workspace / "operator-commands.ps1").read_text(encoding="utf-8")
    commands = commands.replace("param(", "# missing param")
    commands = commands.replace("[ValidateSet(", "# missing validate set")
    commands = commands.replace("$preflightArgs += @('--task-id', $TaskId)", "# missing task scoped preflight")
    commands = commands.replace("if ($TaskId -in @('all', 'S017-003'))", "if ($true)")
    (workspace / "operator-commands.ps1").write_text(commands, encoding="utf-8")

    errors = validate_workspace(workspace)

    assert any("must expose task-selection parameters" in error for error in errors)
    assert any("must constrain task selection values" in error for error in errors)
    assert any("must pass task scope to preflight" in error for error in errors)
    assert any("S017-003: operator commands missing task selection condition" in error for error in errors)


def test_validate_plan_closure_handoff_rejects_completion_audit_after_strict_gate(tmp_path):
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    commands_path = workspace / "operator-commands.ps1"
    commands = commands_path.read_text(encoding="utf-8")
    audit_line = "    & $python scripts\\validate_kimi_plan_completion_audit.py"
    strict_line = "    & $python scripts\\validate_plan_closure_gate.py"
    commands = commands.replace(audit_line, "")
    commands = commands.replace(strict_line, strict_line + "\n" + audit_line)
    commands_path.write_text(commands, encoding="utf-8")

    errors = validate_workspace(workspace)

    assert any("completion audit before the strict closure gate" in error for error in errors)


def test_validate_plan_closure_handoff_cli_reports_errors(tmp_path):
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    (workspace / "README.md").write_text("missing required warnings\n", encoding="utf-8")

    script = ROOT / "scripts" / "validate_plan_closure_handoff.py"
    result = subprocess.run(
        [sys.executable, str(script), str(workspace)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["passed"] is False
    assert any("README.md must state" in error for error in payload["errors"])
