from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Callable, NamedTuple


ROOT = Path(__file__).resolve().parents[1]
HANDOFF = "production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22"


class CommandSpec(NamedTuple):
    command_id: str
    argv: list[str]


def _py(command_id: str, *args: str) -> CommandSpec:
    return CommandSpec(command_id, [sys.executable, *args])


def _cmd(command_id: str, *args: str) -> CommandSpec:
    return CommandSpec(command_id, [*args])


FAST_COMMANDS = [
    _py("alpha_pre_remote_ci_package", "scripts/validate_alpha_pre_remote_ci_package.py"),
    _py("alpha_pending_payload", "scripts/validate_alpha_pending_payload.py"),
    _py("alpha_maturity_honesty", "scripts/validate_alpha_maturity_honesty.py"),
    _py("alpha_commit_scope", "scripts/validate_alpha_commit_scope.py"),
    _py("alpha_completion_audit", "scripts/validate_alpha_magical_peach_completion_audit.py"),
    _py("plan_closure_gate_allow_open", "scripts/validate_plan_closure_gate.py", "--allow-open"),
    _py("plan_closure_manifest", "scripts/validate_plan_closure_manifest.py"),
    _py("plan_closure_handoff", "scripts/validate_plan_closure_handoff.py", HANDOFF),
    _py("plan_closure_runbook", "scripts/validate_plan_closure_runbook.py"),
    _py("governance_yaml_shape", "scripts/validate_governance_yaml_shape.py"),
    _py("git_diff_check", "scripts/check_diff_whitespace.py"),
]

PENDING_SCOPE_COMMAND_IDS = {
    "alpha_pending_payload",
    "alpha_commit_scope",
}

FULL_EXTRA_COMMANDS = [
    _py(
        "alpha_script_compile",
        "-m",
        "py_compile",
        "scripts/verify_remote_ci_evidence.py",
        "scripts/validate_alpha_remote_ci_success.py",
        "scripts/validate_alpha_commit_scope.py",
        "scripts/validate_alpha_maturity_honesty.py",
        "scripts/apply_alpha_remote_ci_success.py",
        "scripts/close_alpha_remote_ci_gate.py",
        "scripts/validate_alpha_final_closure.py",
        "scripts/validate_alpha_pre_commit_readiness.py",
    ),
    _py(
        "alpha_focused_qa",
        "-m",
        "pytest",
        "tests/unit/qa/test_verify_remote_ci_evidence.py",
        "tests/unit/qa/test_validate_alpha_remote_ci_success.py",
        "tests/unit/qa/test_validate_alpha_commit_scope.py",
        "tests/unit/qa/test_validate_alpha_maturity_honesty.py",
        "tests/unit/qa/test_apply_alpha_remote_ci_success.py",
        "tests/unit/qa/test_close_alpha_remote_ci_gate.py",
        "tests/unit/qa/test_validate_alpha_final_closure.py",
        "tests/unit/qa/test_validate_alpha_magical_peach_completion_audit.py",
        "tests/unit/qa/test_validate_alpha_pre_remote_ci_package.py",
        "tests/unit/qa/test_validate_alpha_pending_payload.py",
        "tests/unit/qa/test_validate_alpha_pre_commit_readiness.py",
        "-q",
    ),
    _py(
        "s017_governance_docs",
        "-m",
        "pytest",
        "tests/unit/governance/test_s017_planning_docs.py",
        "-q",
    ),
    _py(
        "adr_lifecycle_status",
        "-m",
        "pytest",
        "tests/unit/governance/test_adr_lifecycle_status.py",
        "-q",
    ),
]


Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def validate(
    *,
    mode: str = "fast",
    runner: Runner | None = None,
    include_pending_scope: bool = True,
) -> dict[str, object]:
    commands = [
        command
        for command in FAST_COMMANDS
        if include_pending_scope or command.command_id not in PENDING_SCOPE_COMMAND_IDS
    ]
    if mode == "full":
        commands.extend(FULL_EXTRA_COMMANDS)
    elif mode != "fast":
        raise ValueError(f"unsupported mode: {mode}")

    runner = _run if runner is None else runner
    results = []
    errors = []
    for command in commands:
        completed = runner(command.argv)
        item = {
            "id": command.command_id,
            "command": " ".join(command.argv),
            "returncode": completed.returncode,
            "stdout_tail": _tail(completed.stdout),
            "stderr_tail": _tail(completed.stderr),
        }
        results.append(item)
        if completed.returncode != 0:
            errors.append(f"{command.command_id} failed with exit code {completed.returncode}")

    return {
        "passed": not errors,
        "errors": errors,
        "mode": mode,
        "commands": results,
        "pending_scope_checked": include_pending_scope,
        "remote_ci_post_commit_required": True,
        "schema": "doge.alpha_pre_commit_readiness.v1",
    }


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")


def _tail(text: str | None, *, limit: int = 1200) -> str:
    if text is None:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Alpha Magical Peach local pre-commit readiness gate."
    )
    parser.add_argument(
        "--mode",
        choices=["fast", "full"],
        default="fast",
        help="fast runs validators only; full also runs focused compile/pytest gates.",
    )
    parser.add_argument(
        "--skip-pending-scope",
        action="store_true",
        help=(
            "Skip validators that require the full Alpha repair package to still be "
            "pending in git status. Use only for post-commit CI or follow-up repair commits."
        ),
    )
    args = parser.parse_args(argv)

    result = validate(mode=args.mode, include_pending_scope=not args.skip_pending_scope)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
