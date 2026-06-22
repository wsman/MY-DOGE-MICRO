from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_plan_closure_manifest import DEFAULT_OUTPUT


SCHEMA = "doge.plan_closure_handoff_workspace.v1"
COMPLETED_EVIDENCE_PREFIXES = (
    "kimi-live-smoke-",
    "financial-provider-approval-",
    "analyst-benchmark-",
    "enterprise-production-validation-",
    "research-agent-screen-reader-manual-",
    "sdk-release-approval-",
)


def validate_workspace(workspace: Path, *, manifest_path: Path | None = None) -> list[str]:
    handoff_path = workspace if workspace.name == "handoff.json" else workspace / "handoff.json"
    workspace_dir = handoff_path.parent
    errors: list[str] = []
    if not handoff_path.exists():
        return [f"missing handoff.json: {handoff_path}"]

    try:
        payload = json.loads(handoff_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"handoff.json is not valid JSON: {exc}"]

    errors.extend(_validate_payload_basics(payload, workspace_dir))
    manifest_ref = manifest_path or _resolve_path(payload.get("source_manifest") or str(DEFAULT_OUTPUT))
    if not manifest_ref.exists():
        errors.append(f"missing source manifest: {manifest_ref}")
        manifest = None
    else:
        manifest = json.loads(manifest_ref.read_text(encoding="utf-8"))
        errors.extend(_validate_against_manifest(payload, manifest))

    errors.extend(_validate_readme(workspace_dir / "README.md"))
    errors.extend(_validate_operator_checklist(payload, workspace_dir))
    errors.extend(_validate_operator_commands(payload, workspace_dir))
    errors.extend(_validate_prepared_inputs(payload, manifest, workspace_dir))
    errors.extend(_validate_workspace_command_plans(payload, workspace_dir))
    errors.extend(_validate_workspace_files(workspace_dir))
    return errors


def _validate_payload_basics(payload: dict[str, Any], workspace_dir: Path) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if payload.get("does_not_close_gates") is not True:
        errors.append("does_not_close_gates must be true")
    if not isinstance(payload.get("tasks"), list) or not payload["tasks"]:
        errors.append("tasks must be a non-empty list")
    root = payload.get("workspace_root")
    if not isinstance(root, str) or not root.strip():
        errors.append("workspace_root is required")
    else:
        recorded = _resolve_path(root)
        if recorded.resolve() != workspace_dir.resolve():
            errors.append(f"workspace_root mismatch: expected {workspace_dir}, got {recorded}")
    return errors


def _validate_against_manifest(payload: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema") != "doge.plan_closure_execution_manifest.v1":
        errors.append("source manifest must use doge.plan_closure_execution_manifest.v1")
        return errors
    if payload.get("source_plan") != manifest.get("source_plan"):
        errors.append("source_plan does not match manifest")
    if payload.get("source_plan_check") != manifest.get("source_plan_check"):
        errors.append("source_plan_check does not match manifest")
    if payload.get("closure_gate") != manifest.get("closure_gate"):
        errors.append("closure_gate snapshot does not match manifest")

    payload_tasks = _tasks_by_id(payload.get("tasks", []))
    manifest_tasks = _tasks_by_id(manifest.get("tasks", []))
    if set(payload_tasks) != set(manifest_tasks):
        errors.append(
            "task id set mismatch: "
            f"expected {', '.join(sorted(manifest_tasks))}, got {', '.join(sorted(payload_tasks))}"
        )
    for task_id in sorted(set(payload_tasks) & set(manifest_tasks)):
        errors.extend(_validate_task_against_manifest(task_id, payload_tasks[task_id], manifest_tasks[task_id]))
    return errors


def _validate_task_against_manifest(task_id: str, payload_task: dict[str, Any], manifest_task: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    handoff = manifest_task.get("handoff", {})
    expected = {
        "title": manifest_task.get("title"),
        "current_status": manifest_task.get("current_status"),
        "current_result": manifest_task.get("current_result"),
        "required_results": manifest_task.get("required_results"),
        "current_evidence": manifest_task.get("current_evidence"),
        "current_blockers": manifest_task.get("current_blockers"),
        "validator_command": manifest_task.get("validator_command"),
        "next_action": manifest_task.get("next_action"),
        "handoff_kind": handoff.get("kind"),
        "input_refs": handoff.get("input_refs", []),
        "input_templates": handoff.get("input_templates", []),
        "build_or_run_command": handoff.get("build_or_run_command"),
        "output_ref": handoff.get("output_ref"),
        "close_condition": handoff.get("close_condition"),
    }
    for key, value in expected.items():
        if payload_task.get(key) != value:
            errors.append(f"{task_id}: {key} does not match manifest")
    return errors


def _validate_readme(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing README.md: {path}"]
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if "does not close any gate" not in text:
        errors.append("README.md must state that the workspace does not close any gate")
    if "Do not place secrets" not in text:
        errors.append("README.md must warn operators not to place secrets in the workspace")
    return errors


def _validate_operator_checklist(payload: dict[str, Any], workspace_dir: Path) -> list[str]:
    errors: list[str] = []
    checklist = payload.get("operator_checklist")
    if not isinstance(checklist, str) or not checklist.strip():
        return ["operator_checklist is required"]
    path = _resolve_path(checklist)
    if not path.exists():
        return [f"missing operator checklist file: {checklist}"]
    if not _is_relative_to(path.resolve(), workspace_dir.resolve()):
        errors.append(f"operator checklist file must stay inside workspace: {checklist}")
    text = path.read_text(encoding="utf-8")
    required_snippets = {
        "does not close gates": "operator checklist must state that it does not close gates",
        "Do not place secrets": "operator checklist must warn against secrets",
        "## Quick Start": "operator checklist must include quick start steps",
        "## Task Checklist": "operator checklist must include a task checklist",
        "operator-commands.ps1": "operator checklist must point to operator-commands.ps1",
        "-TaskId": "operator checklist must document task-scoped execution",
        "-RunFinalGate": "operator checklist must document final-gate execution",
        "Templates and copied drafts are not evidence": "operator checklist must reject template-as-evidence closure",
        "Redaction and security-review flags must be explicit `false`": (
            "operator checklist must require explicit false redaction/security-review flags"
        ),
        "production_ready: false": "operator checklist must preserve non-production posture",
        "stable_declaration: forbidden": "operator checklist must preserve stable declaration posture",
    }
    for snippet, message in required_snippets.items():
        if snippet not in text:
            errors.append(message)
    for task in payload.get("tasks", []):
        task_id = task.get("id", "<unknown>")
        if task_id not in text:
            errors.append(f"{task_id}: operator checklist missing task id")
        for result in task.get("required_results", []):
            if str(result) not in text:
                errors.append(f"{task_id}: operator checklist missing required result {result}")
        plan = task.get("workspace_command_plan", {})
        output_ref = plan.get("resolved_output_ref") or task.get("output_ref")
        if isinstance(output_ref, str) and output_ref and output_ref not in text:
            errors.append(f"{task_id}: operator checklist missing output ref")
        validator = _validator_for_task(task)
        if isinstance(validator, str) and validator and validator not in text:
            errors.append(f"{task_id}: operator checklist missing strict validator")
    return errors


def _validate_operator_commands(payload: dict[str, Any], workspace_dir: Path) -> list[str]:
    errors: list[str] = []
    operator_commands = payload.get("operator_commands")
    if not isinstance(operator_commands, str) or not operator_commands.strip():
        return ["operator_commands is required"]
    path = _resolve_path(operator_commands)
    if not path.exists():
        return [f"missing operator commands file: {operator_commands}"]
    if not _is_relative_to(path.resolve(), workspace_dir.resolve()):
        errors.append(f"operator commands file must stay inside workspace: {operator_commands}")
    text = path.read_text(encoding="utf-8")
    required_snippets = {
        "does not prove closure": "operator commands must state that they do not prove closure",
        "preflight_plan_closure_external.py": "operator commands must run external preflight",
        "--require-external-inputs": "operator commands must require external inputs",
        "validate_plan_closure_gate.py": "operator commands must include the strict closure gate",
        "validate_kimi_plan_completion_audit.py": "operator commands must validate the completion audit before the strict gate",
        "Do not put secrets": "operator commands must warn against secrets",
        "$repoRoot": "operator commands must define the repository root",
        "Set-Location -LiteralPath $repoRoot": "operator commands must switch to the repository root",
        "$python = Join-Path $repoRoot": "operator commands must define the Python interpreter path",
        "Test-Path -LiteralPath $python": "operator commands must check the Python interpreter path",
        "& $python": "operator commands must invoke Python through the checked interpreter",
        "param(": "operator commands must expose task-selection parameters",
        "[ValidateSet(": "operator commands must constrain task selection values",
        "$TaskId": "operator commands must support task-scoped execution",
        "--task-id": "operator commands must pass task scope to preflight",
        "$RunFinalGate": "operator commands must expose the final-gate override",
        "Skipping final strict gate for single-task run": "operator commands must skip the final gate by default for single-task runs",
    }
    for snippet, message in required_snippets.items():
        if snippet not in text:
            errors.append(message)
    audit_index = _first_script_index(text, "validate_kimi_plan_completion_audit.py")
    strict_gate_index = _first_script_index(text, "validate_plan_closure_gate.py")
    if audit_index != -1 and strict_gate_index != -1 and audit_index > strict_gate_index:
        errors.append("operator commands must run completion audit before the strict closure gate")
    for task in payload.get("tasks", []):
        task_id = task.get("id", "<unknown>")
        plan = task.get("workspace_command_plan", {})
        command = plan.get("command_with_draft_inputs")
        script_ref = _script_ref(command)
        if script_ref and script_ref not in text:
            errors.append(f"{task_id}: operator commands missing workspace command")
        for binding in plan.get("prepared_input_bindings", []):
            if not isinstance(binding, dict):
                continue
            prepared_input = binding.get("prepared_input")
            if isinstance(prepared_input, str) and prepared_input and prepared_input not in text:
                errors.append(f"{task_id}: operator commands missing prepared input path: {prepared_input}")
        output_ref = plan.get("resolved_output_ref")
        if isinstance(output_ref, str) and output_ref and output_ref not in text:
            errors.append(f"{task_id}: operator commands missing resolved output validator path")
        condition = f"$TaskId -in @('all', '{task_id}')"
        if condition not in text:
            errors.append(f"{task_id}: operator commands missing task selection condition")
    return errors


def _script_ref(command: Any) -> str | None:
    if not isinstance(command, str):
        return None
    match = re.search(r"scripts[\\/][^\s'\"]+\.py", command)
    if not match:
        return None
    return match.group(0)


def _first_script_index(text: str, script_name: str) -> int:
    normalized = text.replace("/", "\\")
    needle = f"scripts\\{script_name}"
    return normalized.find(needle)


def _validator_for_task(task: dict[str, Any]) -> str:
    validator = task.get("validator_command") or ""
    resolved_output = task.get("workspace_command_plan", {}).get("resolved_output_ref")
    if not resolved_output:
        return validator
    current_evidence = task.get("current_evidence")
    if isinstance(current_evidence, str) and current_evidence:
        validator = _replace_path_token(validator, current_evidence, resolved_output)
    output_ref = task.get("output_ref")
    if isinstance(output_ref, str) and output_ref:
        validator = _replace_path_token(validator, output_ref, resolved_output)
    return validator


def _replace_path_token(command: str, original: str, replacement: str) -> str:
    result = command
    for value in {original, original.replace("\\", "/"), original.replace("/", "\\")}:
        result = result.replace(value, replacement)
    return result


def _validate_prepared_inputs(
    payload: dict[str, Any],
    manifest: dict[str, Any] | None,
    workspace_dir: Path,
) -> list[str]:
    errors: list[str] = []
    manifest_templates = _manifest_templates(manifest)
    for task in payload.get("tasks", []):
        task_id = task.get("id", "<unknown>")
        prepared_inputs = task.get("prepared_inputs")
        if not isinstance(prepared_inputs, list):
            errors.append(f"{task_id}: prepared_inputs must be a list")
            continue
        if task.get("input_templates") == [] and prepared_inputs:
            errors.append(f"{task_id}: live/no-template task must not have prepared_inputs")
        for prepared in prepared_inputs:
            if not isinstance(prepared, dict):
                errors.append(f"{task_id}: prepared input must be an object")
                continue
            source = prepared.get("source_template")
            target = prepared.get("prepared_input")
            if source not in manifest_templates:
                errors.append(f"{task_id}: source_template is not listed in the current manifest: {source}")
            if prepared.get("action") != "copied_template_for_operator_edit":
                errors.append(f"{task_id}: prepared input action must be copied_template_for_operator_edit")
            if not isinstance(target, str) or not target.strip():
                errors.append(f"{task_id}: prepared_input is required")
                continue
            target_path = _resolve_path(target)
            if not target_path.exists():
                errors.append(f"{task_id}: missing prepared input: {target}")
                continue
            if not _is_relative_to(target_path.resolve(), workspace_dir.resolve()):
                errors.append(f"{task_id}: prepared input must stay inside workspace: {target}")
            if "-draft-" not in target_path.name:
                errors.append(f"{task_id}: prepared input filename must contain -draft-: {target_path.name}")
            if _looks_like_completed_evidence(target_path.name):
                errors.append(f"{task_id}: prepared input looks like completed evidence: {target_path.name}")
    return errors


def _validate_workspace_command_plans(payload: dict[str, Any], workspace_dir: Path) -> list[str]:
    errors: list[str] = []
    for task in payload.get("tasks", []):
        task_id = task.get("id", "<unknown>")
        plan = task.get("workspace_command_plan")
        if not isinstance(plan, dict):
            errors.append(f"{task_id}: workspace_command_plan must be an object")
            continue
        if plan.get("command_template") != task.get("build_or_run_command"):
            errors.append(f"{task_id}: command_template must match build_or_run_command")
        if not isinstance(plan.get("command_with_draft_inputs"), str) or not plan["command_with_draft_inputs"].strip():
            errors.append(f"{task_id}: command_with_draft_inputs is required")
        if plan.get("writes_completed_evidence_to_workspace") is not False:
            errors.append(f"{task_id}: writes_completed_evidence_to_workspace must be false")
        output_ref = plan.get("resolved_output_ref")
        if isinstance(output_ref, str) and output_ref:
            output_path = _resolve_path(output_ref)
            if _is_relative_to(output_path.resolve(), workspace_dir.resolve()):
                errors.append(f"{task_id}: resolved_output_ref must not be inside handoff workspace")
        prepared = {
            item.get("prepared_input"): item.get("source_template")
            for item in task.get("prepared_inputs", [])
            if isinstance(item, dict)
        }
        bindings = plan.get("prepared_input_bindings")
        if not isinstance(bindings, list):
            errors.append(f"{task_id}: prepared_input_bindings must be a list")
            continue
        if not task.get("prepared_inputs") and bindings:
            errors.append(f"{task_id}: task without prepared inputs must not have prepared_input_bindings")
        for binding in bindings:
            if not isinstance(binding, dict):
                errors.append(f"{task_id}: prepared input binding must be an object")
                continue
            prepared_input = binding.get("prepared_input")
            source_template = binding.get("source_template")
            if prepared.get(prepared_input) != source_template:
                errors.append(f"{task_id}: prepared input binding does not match prepared_inputs: {prepared_input}")
    return errors


def _validate_workspace_files(workspace_dir: Path) -> list[str]:
    errors: list[str] = []
    for path in workspace_dir.rglob("*"):
        if path.is_file() and _looks_like_completed_evidence(path.name):
            errors.append(f"workspace contains completed-evidence-looking file: {path}")
    return errors


def _manifest_templates(manifest: dict[str, Any] | None) -> set[str]:
    if not manifest:
        return set()
    return {
        template
        for task in manifest.get("tasks", [])
        for template in task.get("handoff", {}).get("input_templates", [])
    }


def _tasks_by_id(items: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        return {}
    return {
        item["id"]: item
        for item in items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def _looks_like_completed_evidence(filename: str) -> bool:
    return (
        any(filename.startswith(prefix) for prefix in COMPLETED_EVIDENCE_PREFIXES)
        and "-draft-" not in filename
        and "-template-" not in filename
    )


def _resolve_path(value: str) -> Path:
    normalized = Path(str(value).replace("\\", "/"))
    if normalized.is_absolute():
        return normalized
    return ROOT / normalized


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a 9b77f9c external closure handoff workspace.")
    parser.add_argument("workspace", help="Handoff workspace directory or handoff.json path.")
    parser.add_argument("--manifest", default=None, help="Manifest JSON path to validate against.")
    args = parser.parse_args(argv)

    errors = validate_workspace(
        Path(args.workspace),
        manifest_path=Path(args.manifest) if args.manifest else None,
    )
    result = {"path": args.workspace, "passed": not errors, "errors": errors}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
