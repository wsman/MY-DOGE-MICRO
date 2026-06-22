from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_plan_closure_manifest import DEFAULT_OUTPUT


DEFAULT_OUTPUT_ROOT = (
    ROOT
    / "production"
    / "qa"
    / "evidence"
    / "plan-closure"
    / "handoffs"
)
SCHEMA = "doge.plan_closure_handoff_workspace.v1"


def prepare_handoff_workspace(
    *,
    manifest_path: Path = DEFAULT_OUTPUT,
    date: str,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    _validate_date(date)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "doge.plan_closure_execution_manifest.v1":
        raise ValueError("manifest must use doge.plan_closure_execution_manifest.v1")

    workspace = output_dir or (DEFAULT_OUTPUT_ROOT / f"9b77f9c-{date}")
    workspace.mkdir(parents=True, exist_ok=True)

    tasks = [_prepare_task(task, workspace=workspace, date=date) for task in manifest["tasks"]]
    payload = {
        "schema": SCHEMA,
        "source_manifest": _display_path(manifest_path),
        "source_plan": manifest.get("source_plan"),
        "source_plan_check": manifest.get("source_plan_check"),
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": _display_path(workspace),
        "date": date,
        "does_not_close_gates": True,
        "closure_gate": manifest.get("closure_gate"),
        "tasks": tasks,
    }

    readme_path = workspace / "README.md"
    operator_checklist_path = workspace / "operator-checklist.md"
    operator_commands_path = workspace / "operator-commands.ps1"
    handoff_path = workspace / "handoff.json"
    payload["handoff_json"] = _display_path(handoff_path)
    payload["readme"] = _display_path(readme_path)
    payload["operator_checklist"] = _display_path(operator_checklist_path)
    payload["operator_commands"] = _display_path(operator_commands_path)
    handoff_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    readme_path.write_text(_render_readme(payload), encoding="utf-8")
    operator_checklist_path.write_text(_render_operator_checklist(payload), encoding="utf-8")
    operator_commands_path.write_text(_render_operator_commands(payload), encoding="utf-8")
    return payload


def _prepare_task(task: dict[str, Any], *, workspace: Path, date: str) -> dict[str, Any]:
    task_id = str(task["id"])
    handoff = task.get("handoff", {})
    input_dir = workspace / "inputs" / _safe_name(task_id)
    prepared_inputs = []
    for template in handoff.get("input_templates", []):
        source = _repo_path(template)
        if not source.exists():
            raise ValueError(f"missing input template: {template}")
        destination = input_dir / _draft_name(source.name, date)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        prepared_inputs.append(
            {
                "source_template": template,
                "prepared_input": _display_path(destination),
                "action": "copied_template_for_operator_edit",
            }
        )

    command_plan = _workspace_command_plan(
        handoff=handoff,
        prepared_inputs=prepared_inputs,
        date=date,
    )
    return {
        "id": task_id,
        "title": task["title"],
        "current_status": task["current_status"],
        "current_result": task["current_result"],
        "required_results": task["required_results"],
        "current_evidence": task["current_evidence"],
        "current_blockers": task["current_blockers"],
        "validator_command": task["validator_command"],
        "next_action": task["next_action"],
        "handoff_kind": handoff.get("kind"),
        "input_refs": handoff.get("input_refs", []),
        "input_templates": handoff.get("input_templates", []),
        "prepared_inputs": prepared_inputs,
        "build_or_run_command": handoff.get("build_or_run_command"),
        "workspace_command_plan": command_plan,
        "output_ref": handoff.get("output_ref"),
        "close_condition": handoff.get("close_condition"),
    }


def _workspace_command_plan(
    *,
    handoff: dict[str, Any],
    prepared_inputs: list[dict[str, str]],
    date: str,
) -> dict[str, Any]:
    original = handoff.get("build_or_run_command") or ""
    command = original
    bindings = _prepared_input_bindings(
        input_refs=handoff.get("input_refs", []),
        prepared_inputs=prepared_inputs,
    )
    for binding in bindings:
        command = _replace_path_token(command, binding["input_ref"], binding["prepared_input"])

    output_ref = handoff.get("output_ref")
    resolved_output_ref = _resolve_date_token(output_ref, date)
    if output_ref and resolved_output_ref:
        command = _replace_path_token(command, output_ref, resolved_output_ref)

    command = command.replace("YYYY-MM-DDTHH:MM:SSZ", "$createdAt")
    command = command.replace("YYYY-MM-DD", date)
    placeholders = sorted(set(re.findall(r"<[^>]+>|\$createdAt", command)))
    return {
        "command_template": original,
        "command_with_draft_inputs": command,
        "prepared_input_bindings": bindings,
        "resolved_output_ref": resolved_output_ref,
        "requires_operator_values": placeholders,
        "timestamp_preamble": (
            '$createdAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")'
            if "$createdAt" in placeholders
            else None
        ),
        "writes_completed_evidence_to_workspace": False,
    }


def _prepared_input_bindings(
    *,
    input_refs: list[str],
    prepared_inputs: list[dict[str, str]],
) -> list[dict[str, str]]:
    bindings: list[dict[str, str]] = []
    unmatched_refs = list(input_refs)
    for prepared in prepared_inputs:
        source_template = prepared["source_template"]
        source_base = _template_base(source_template)
        match = next(
            (
                ref
                for ref in unmatched_refs
                if not ref.startswith("env:")
                and not ref.startswith("optional:env:")
                and _input_ref_matches_template(ref, source_base)
            ),
            None,
        )
        if match is None:
            continue
        unmatched_refs.remove(match)
        bindings.append(
            {
                "input_ref": match,
                "source_template": source_template,
                "prepared_input": prepared["prepared_input"],
            }
        )
    return bindings


def _input_ref_matches_template(input_ref: str, template_base: str) -> bool:
    input_base = _input_base(input_ref)
    return input_base == template_base or input_base.startswith(f"{template_base}-")


def _template_base(value: str) -> str:
    stem = Path(value.replace("\\", "/")).stem
    return re.sub(r"-template-\d{4}-\d{2}-\d{2}$", "", stem)


def _input_base(value: str) -> str:
    stem = Path(value.replace("\\", "/")).stem
    stem = stem.replace("YYYY-MM-DD", "").strip("-")
    return stem


def _resolve_date_token(value: str | None, date: str) -> str | None:
    if value is None:
        return None
    return value.replace("YYYY-MM-DD", date)


def _replace_path_token(command: str, original: str, replacement: str) -> str:
    values = {
        original,
        original.replace("\\", "/"),
        original.replace("/", "\\"),
    }
    result = command
    for value in values:
        result = result.replace(value, replacement)
    return result


def _render_readme(payload: dict[str, Any]) -> str:
    lines = [
        "# 9b77f9c External Closure Handoff Workspace",
        "",
        f"Prepared: {payload['prepared_at']}",
        f"Date token: {payload['date']}",
        f"Source manifest: `{payload['source_manifest']}`",
        f"Source plan SHA-256: `{_source_plan_sha(payload)}`",
        f"Operator command list: `{payload['operator_commands']}`",
        "",
        "This workspace does not close any gate. It only copies operator input",
        "templates into draft files and records the commands needed after real",
        "external evidence is collected.",
        "",
        "Do not place secrets, API keys, raw sensitive documents, or completed",
        "evidence outputs in this workspace. Completed evidence must be written to",
        "the output paths listed by each task and then validated with the strict",
        "validator command.",
        "",
        "## Tasks",
        "",
    ]
    for task in payload["tasks"]:
        lines.extend(
            [
                f"### {task['id']} - {task['title']}",
                "",
                f"- Required result: `{', '.join(task['required_results'])}`",
                f"- Current status: `{task['current_status']}` / `{task['current_result']}`",
                f"- Handoff kind: `{task['handoff_kind']}`",
                f"- Close condition: {task['close_condition']}",
                f"- Output ref: `{task['output_ref']}`",
                f"- Validator: `{task['validator_command']}`",
                f"- Builder/runner: `{task['build_or_run_command']}`",
            ]
        )
        if task["prepared_inputs"]:
            lines.append("- Prepared draft inputs:")
            for prepared in task["prepared_inputs"]:
                lines.append(
                    f"  - `{prepared['prepared_input']}` from `{prepared['source_template']}`"
                )
        else:
            lines.append("- Prepared draft inputs: none; use the listed env/input refs.")
        lines.append("- Input refs:")
        for input_ref in task["input_refs"]:
            lines.append(f"  - `{input_ref}`")
        command_plan = task["workspace_command_plan"]
        if command_plan["prepared_input_bindings"]:
            lines.append("- Draft input bindings:")
            for binding in command_plan["prepared_input_bindings"]:
                lines.append(f"  - `{binding['input_ref']}` -> `{binding['prepared_input']}`")
        if command_plan["timestamp_preamble"]:
            lines.append(f"- Timestamp preamble: `{command_plan['timestamp_preamble']}`")
        if command_plan["requires_operator_values"]:
            lines.append(
                "- Operator placeholders: "
                + ", ".join(f"`{value}`" for value in command_plan["requires_operator_values"])
            )
        lines.append(f"- Workspace command: `{command_plan['command_with_draft_inputs']}`")
        lines.extend(["", f"Next action: {task['next_action']}", ""])
    return "\n".join(lines).rstrip() + "\n"


def _render_operator_checklist(payload: dict[str, Any]) -> str:
    workspace = payload["workspace_root"]
    command_file = payload["operator_commands"]
    lines = [
        "# 9b77f9c External Closure Operator Checklist",
        "",
        f"Workspace: `{workspace}`",
        f"Command file: `{command_file}`",
        f"Source plan SHA-256: `{_source_plan_sha(payload)}`",
        "",
        "This checklist does not close gates. It is a short execution index for",
        "real operator evidence. Do not place secrets, API keys, raw sensitive",
        "documents, or completed evidence outputs in the handoff workspace.",
        "",
        "## Quick Start",
        "",
        "1. Fill only the draft inputs for the gate you are executing.",
        "2. Run preflight for that gate through the generated command file.",
        "3. Run the generated builder or live runner.",
        "4. Run the strict validator for the produced evidence.",
        "5. Run the final strict closure gate only after all six gates have real evidence.",
        "",
        "Example single-gate command:",
        "",
        "```powershell",
        f"powershell -ExecutionPolicy Bypass -File {command_file} -TaskId S017-003",
        "```",
        "",
        "Example final gate command after all evidence is complete:",
        "",
        "```powershell",
        f"powershell -ExecutionPolicy Bypass -File {command_file} -RunFinalGate",
        "```",
        "",
        "## Task Checklist",
        "",
        "| ID | Required result | Fill before running | Output evidence | Strict validator |",
        "|----|----|----|----|----|",
    ]
    for task in payload["tasks"]:
        fill_items = _checklist_fill_items(task)
        validator = _validator_for_task(task)
        lines.append(
            "| "
            + " | ".join(
                [
                    task["id"],
                    ", ".join(task["required_results"]),
                    "<br>".join(f"`{item}`" for item in fill_items) if fill_items else "No draft; set env/input refs",
                    f"`{task['workspace_command_plan']['resolved_output_ref'] or task['output_ref']}`",
                    f"`{validator}`",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Templates and copied drafts are not evidence.",
            "- `needs_revision`, `rejected`, `failed`, `blocked`, and `not_run` do not close gates.",
            "- Redaction and security-review flags must be explicit `false`; missing flags do not pass preflight or strict validation.",
            "- Completed evidence belongs in the production evidence folders listed above, not inside this workspace.",
            "- The final gate must keep `production_ready: false` and `stable_declaration: forbidden` until a separate promotion review changes them.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _source_plan_sha(payload: dict[str, Any]) -> str:
    check = payload.get("source_plan_check")
    if not isinstance(check, dict):
        return "unavailable"
    value = check.get("sha256")
    return value if isinstance(value, str) and value else "unavailable"


def _checklist_fill_items(task: dict[str, Any]) -> list[str]:
    prepared = [
        item["prepared_input"]
        for item in task.get("prepared_inputs", [])
        if isinstance(item, dict) and isinstance(item.get("prepared_input"), str)
    ]
    if prepared:
        return prepared
    return [
        ref
        for ref in task.get("input_refs", [])
        if isinstance(ref, str) and (ref.startswith("env:") or ref.startswith("optional:env:"))
    ]


def _render_operator_commands(payload: dict[str, Any]) -> str:
    workspace = payload["workspace_root"]
    task_ids = [task["id"] for task in payload["tasks"]]
    validate_set = ", ".join(_powershell_single_quoted(value) for value in ["all", *task_ids])
    commands = [
        "# 9b77f9c External Closure Operator Commands",
        "# Generated from the handoff manifest. Review before running.",
        "# This script does not prove closure by itself.",
        "# The script switches to the repository root before running commands.",
        "# Fill and review draft inputs before running builder commands.",
        "# Do not put secrets, API keys, or sensitive raw documents in this file or workspace.",
        "",
        "param(",
        f"    [ValidateSet({validate_set})]",
        "    [string]$TaskId = 'all',",
        "    [switch]$RunFinalGate",
        ")",
        "",
        '$ErrorActionPreference = "Stop"',
        f"$repoRoot = {_powershell_single_quoted(str(ROOT.resolve()))}",
        "Set-Location -LiteralPath $repoRoot",
        "$python = Join-Path $repoRoot '.venv\\Scripts\\python.exe'",
        "if (-not (Test-Path -LiteralPath $python)) {",
        "    throw 'Missing Python interpreter: .venv\\Scripts\\python.exe'",
        "}",
        '$createdAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")',
    ]
    if _requires_placeholder(payload, "<initials>"):
        commands.extend(
            [
                '$analystInitials = "<initials>"',
                'if ($TaskId -in @(\'all\', \'W3-live\') -and $analystInitials -eq "<initials>") {',
                "    throw 'Set $analystInitials before running analyst benchmark commands.'",
                "}",
            ]
        )
    commands.extend(
        [
            "",
            "# Preflight: fails until external env vars and edited draft inputs are ready.",
            "$preflightArgs = @(",
            "    'scripts\\preflight_plan_closure_external.py',",
            "    '--handoff-workspace',",
            f"    {_powershell_single_quoted(workspace)},",
            "    '--require-external-inputs'",
            ")",
            "if ($TaskId -ne 'all') {",
            "    $preflightArgs += @('--task-id', $TaskId)",
            "}",
            "& $python @preflightArgs",
            "",
        ]
    )

    for task in payload["tasks"]:
        plan = task["workspace_command_plan"]
        known_paths = _operator_known_paths(task)
        command = _command_for_powershell(
            _quote_powershell_paths(plan["command_with_draft_inputs"], known_paths)
        )
        validator = _command_for_powershell(
            _quote_powershell_paths(_validator_for_task(task), known_paths)
        )
        commands.extend(
            [
                f"# {task['id']} - {task['title']}",
                f"# Required result: {', '.join(task['required_results'])}",
                f"# Close condition: {task['close_condition']}",
            ]
        )
        if plan["requires_operator_values"]:
            commands.append(
                "# Operator values: "
                + ", ".join(str(value) for value in plan["requires_operator_values"])
            )
        condition = _task_condition(task["id"])
        commands.extend(
            [
                f"if ({condition}) {{",
                f"    {command}",
                f"    {_command_for_powershell(validator)}",
                "}",
                "",
            ]
        )

    commands.extend(
        [
            "# Refresh and validate closure metadata after completed evidence is present.",
            "if ($TaskId -eq 'all' -or $RunFinalGate) {",
            "    & $python scripts\\export_plan_closure_manifest.py",
            "    & $python scripts\\validate_plan_closure_manifest.py",
            "    & $python scripts\\validate_plan_closure_runbook.py",
            "    & $python scripts\\validate_kimi_plan_completion_audit.py",
            "    # Final strict gate: succeeds only when every external gate has real completed evidence.",
            "    & $python scripts\\validate_plan_closure_gate.py",
            "} else {",
            "    Write-Host 'Skipping final strict gate for single-task run; use -RunFinalGate or -TaskId all when ready.'",
            "}",
            "",
        ]
    )
    return "\n".join(commands)


def _requires_placeholder(payload: dict[str, Any], placeholder: str) -> bool:
    return any(
        placeholder in task["workspace_command_plan"]["requires_operator_values"]
        for task in payload["tasks"]
    )


def _command_for_powershell(command: str) -> str:
    return command.replace(".\\.venv\\Scripts\\python.exe", "& $python").replace(
        "<initials>",
        "$analystInitials",
    )


def _task_condition(task_id: str) -> str:
    return f"$TaskId -in @('all', {_powershell_single_quoted(task_id)})"


def _operator_known_paths(task: dict[str, Any]) -> list[str]:
    plan = task["workspace_command_plan"]
    paths = [
        binding["prepared_input"]
        for binding in plan.get("prepared_input_bindings", [])
        if isinstance(binding, dict) and isinstance(binding.get("prepared_input"), str)
    ]
    for value in [plan.get("resolved_output_ref"), task.get("current_evidence"), task.get("output_ref")]:
        if isinstance(value, str) and value:
            paths.append(value)
    return paths


def _quote_powershell_paths(command: str, paths: list[str]) -> str:
    result = command
    for path in sorted(set(paths), key=len, reverse=True):
        replacement = _powershell_single_quoted(path)
        for variant in {path, path.replace("\\", "/"), path.replace("/", "\\")}:
            result = result.replace(variant, replacement)
    return result


def _powershell_single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _validator_for_task(task: dict[str, Any]) -> str:
    validator = task["validator_command"]
    resolved_output = task["workspace_command_plan"].get("resolved_output_ref")
    if not resolved_output:
        return validator
    current_evidence = task.get("current_evidence")
    if current_evidence:
        validator = _replace_path_token(validator, current_evidence, resolved_output)
    output_ref = task.get("output_ref")
    if output_ref:
        validator = _replace_path_token(validator, output_ref, resolved_output)
    return validator


def _repo_path(value: str) -> Path:
    return ROOT / Path(value.replace("\\", "/"))


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def _draft_name(filename: str, date: str) -> str:
    path = Path(filename)
    stem = path.stem
    suffix = path.suffix
    stem = re.sub(r"-template-\d{4}-\d{2}-\d{2}$", "", stem)
    if "-template" in stem:
        stem = stem.replace("-template", "")
    return f"{stem}-draft-{date}{suffix}"


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-").lower()


def _validate_date(value: str) -> None:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("date must use YYYY-MM-DD") from exc
    if parsed.strftime("%Y-%m-%d") != value:
        raise ValueError("date must use YYYY-MM-DD")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare draft inputs for the 9b77f9c external closure handoff.")
    parser.add_argument("--manifest", default=str(DEFAULT_OUTPUT), help="Execution manifest JSON path.")
    parser.add_argument("--date", required=True, help="Date token for copied draft input files, YYYY-MM-DD.")
    parser.add_argument("--output-dir", help="Workspace directory. Defaults under production/qa/evidence/plan-closure/handoffs/.")
    args = parser.parse_args(argv)

    payload = prepare_handoff_workspace(
        manifest_path=Path(args.manifest),
        date=args.date,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    result = {
        "workspace_root": payload["workspace_root"],
        "handoff_json": payload["handoff_json"],
        "readme": payload["readme"],
        "operator_commands": payload["operator_commands"],
        "operator_checklist": payload["operator_checklist"],
        "tasks": len(payload["tasks"]),
        "prepared_inputs": sum(len(task["prepared_inputs"]) for task in payload["tasks"]),
        "does_not_close_gates": payload["does_not_close_gates"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
