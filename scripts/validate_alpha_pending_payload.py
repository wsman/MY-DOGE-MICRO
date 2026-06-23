from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_alpha_pre_remote_ci_package import REQUIRED_PAYLOAD_PATHS


REQUIRED_PENDING_PATHS = [
    "docs/archive/audits/alpha-magical-peach-completion-audit-2026-06-23.md",
    "docs/archive/audits/alpha-magical-peach-pre-remote-ci-package-2026-06-23.md",
    "docs/archive/audits/remote-ci-handoff-2026-06-23.md",
    "scripts/validate_alpha_magical_peach_completion_audit.py",
    "scripts/validate_alpha_pre_remote_ci_package.py",
    "scripts/validate_alpha_pending_payload.py",
    "scripts/validate_alpha_maturity_honesty.py",
    "scripts/validate_alpha_pre_commit_readiness.py",
    "scripts/apply_alpha_remote_ci_success.py",
    "scripts/close_alpha_remote_ci_gate.py",
    "scripts/validate_alpha_commit_scope.py",
    "scripts/validate_alpha_final_closure.py",
    "scripts/validate_alpha_remote_ci_success.py",
    "scripts/verify_remote_ci_evidence.py",
    "tests/unit/qa/test_validate_alpha_magical_peach_completion_audit.py",
    "tests/unit/qa/test_validate_alpha_pre_remote_ci_package.py",
    "tests/unit/qa/test_validate_alpha_pending_payload.py",
    "tests/unit/qa/test_validate_alpha_maturity_honesty.py",
    "tests/unit/qa/test_validate_alpha_pre_commit_readiness.py",
    "tests/unit/qa/test_apply_alpha_remote_ci_success.py",
    "tests/unit/qa/test_close_alpha_remote_ci_gate.py",
    "tests/unit/qa/test_validate_alpha_commit_scope.py",
    "tests/unit/qa/test_validate_alpha_final_closure.py",
    "tests/unit/qa/test_validate_alpha_remote_ci_success.py",
    "tests/unit/qa/test_verify_remote_ci_evidence.py",
    "production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json",
    "scripts/validate_plan_closure_gate.py",
    "scripts/export_plan_closure_manifest.py",
    "scripts/prepare_plan_closure_handoff.py",
    "scripts/validate_plan_closure_handoff.py",
    "scripts/preflight_plan_closure_external.py",
    "tests/unit/qa/test_export_plan_closure_manifest.py",
    "tests/unit/qa/test_plan_closure_input_templates.py",
    "tests/unit/qa/test_preflight_plan_closure_external.py",
    "tests/unit/qa/test_prepare_plan_closure_handoff.py",
    "docs/archive/audits/adr-0016-0020-disposition-review-2026-06-23.md",
    "docs/archive/audits/external-gate-next-actions-2026-06-23.md",
    "docs/progress/runtime-maturity.yaml",
    "production/sprints/sprint-017-external-validation-and-provider-hardening.md",
    "tests/unit/governance/test_s017_planning_docs.py",
    "web/src/api/client.ts",
    "web/src/api/portfolio.ts",
]

REQUIRED_PENDING_PREFIXES = [
    "production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/",
]


def validate(status_lines: list[str]) -> list[str]:
    errors: list[str] = []
    pending_paths = _pending_paths(status_lines)
    for required_path in REQUIRED_PENDING_PATHS:
        if required_path not in pending_paths:
            errors.append(f"required path missing from pending commit payload: {required_path}")
    for required_path in REQUIRED_PENDING_PATHS:
        if required_path not in REQUIRED_PAYLOAD_PATHS:
            errors.append(f"required pending path is not listed in pre-remote package payload: {required_path}")
    for required_prefix in REQUIRED_PENDING_PREFIXES:
        if not any(path.startswith(required_prefix) for path in pending_paths):
            errors.append(f"required directory missing from pending commit payload: {required_prefix}")
        if required_prefix not in REQUIRED_PAYLOAD_PATHS:
            errors.append(f"required pending directory is not listed in pre-remote package payload: {required_prefix}")
    return errors


def _pending_paths(status_lines: list[str]) -> set[str]:
    paths: set[str] = set()
    for line in status_lines:
        if len(line) < 4:
            continue
        path_text = line[3:]
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1]
        path_text = path_text.strip().strip('"').replace("\\", "/")
        paths.add(path_text)
    return paths


def _git_status_porcelain() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate that critical Alpha pre-remote-CI files are still pending for the next commit."
    )
    parser.add_argument(
        "--status-file",
        type=Path,
        help="Optional file containing git status --porcelain=v1 output for tests or offline validation.",
    )
    args = parser.parse_args(argv)

    if args.status_file:
        status_lines = args.status_file.read_text(encoding="utf-8").splitlines()
    else:
        status_lines = _git_status_porcelain()
    errors = validate(status_lines)
    result = {
        "passed": not errors,
        "errors": errors,
        "required_pending_paths": REQUIRED_PENDING_PATHS,
        "required_pending_prefixes": REQUIRED_PENDING_PREFIXES,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
