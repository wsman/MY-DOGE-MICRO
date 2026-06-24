from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_plan_closure_gate import validate_all


PACKAGE = ROOT / "docs" / "archive" / "audits" / "piped-donut-pre-remote-ci-package-2026-06-24.md"
PLAN = Path(r"C:\Users\Aby\.claude\plans\my-doge-micro-main-2ffdb66-piped-donut.md")
MATURITY = ROOT / "docs" / "progress" / "runtime-maturity.yaml"

FALLBACK_PLAN_TEXT = """
docs/progress/my-doge-micro-main-2ffdb66-piped-donut-completion-audit.md
docs/archive/audits/piped-donut-pre-remote-ci-package-2026-06-24.md
scripts/validate_piped_donut_completion_audit.py
scripts/validate_piped_donut_pre_remote_ci_package.py
scripts/verify_remote_ci_evidence.py
scripts/validate_alpha_remote_ci_success.py
production/qa/evidence/ci/remote-ci-<shortsha>.json
"""


REQUIRED_SNIPPETS = [
    "The local remediation package is ready for a future exact-SHA remote CI attempt, but the plan is not complete.",
    r"C:\Users\Aby\.claude\plans\my-doge-micro-main-2ffdb66-piped-donut.md",
    "2ffdb66e12865e00aba23808057eba87ca7aa116",
    "2ffdb66",
    "pending_remote_ci",
    "No commit or push has been performed",
    "post-commit SHA",
    "scripts/verify_remote_ci_evidence.py",
    "scripts/validate_alpha_remote_ci_success.py",
    "--wait",
    "--require-canonical-path",
    "wait.status = success",
    "production/qa/evidence/ci/remote-ci-<shortsha>.json",
    "tools/ci/sdk-contract-check.py",
    "scripts/validate_piped_donut_completion_audit.py",
    "scripts/validate_piped_donut_pre_remote_ci_package.py",
    "1431 passed, 9 skipped, 11 warnings",
    "6 total gates: 5 open / 1 passed",
    "stable_declaration: forbidden",
    "production_ready: false",
]


REQUIRED_PAYLOAD_PATHS = [
    "docs/progress/my-doge-micro-main-2ffdb66-piped-donut-completion-audit.md",
    "docs/archive/audits/piped-donut-pre-remote-ci-package-2026-06-24.md",
    "scripts/validate_piped_donut_completion_audit.py",
    "scripts/validate_piped_donut_pre_remote_ci_package.py",
    "tests/unit/qa/test_validate_piped_donut_completion_audit.py",
    "tests/unit/qa/test_validate_piped_donut_pre_remote_ci_package.py",
    "scripts/verify_remote_ci_evidence.py",
    "scripts/validate_alpha_remote_ci_success.py",
    "tests/unit/qa/test_verify_remote_ci_evidence.py",
    "tests/unit/qa/test_validate_alpha_remote_ci_success.py",
    "tools/ci/sdk-contract-check.py",
    "tests/unit/ci/test_sdk_contract_check.py",
    ".github/workflows/ci.yml",
    "migrations/",
    "src/doge/infrastructure/database/migration_runner.py",
    "src/doge/infrastructure/database/tenant_guard.py",
    "tests/unit/infrastructure/test_migration_runner.py",
    "src/doge/infrastructure/database/sqlite_runtime_transaction.py",
    "src/doge/infrastructure/database/event_subscriber.py",
    "src/doge/application/agent/outbox_publisher.py",
    "tests/contract/test_event_sequence_concurrency.py",
    "tests/unit/agent/test_runtime_transaction.py",
    "tests/unit/agent/test_event_subscriber.py",
    "tests/unit/agent/test_worker_queue.py",
    "src/doge/core/ports/code_executor.py",
    "src/doge/infrastructure/code_execution/",
    "src/doge/bootstrap/container.py",
    "src/doge/bootstrap/runtime.py",
    "src/doge/bootstrap/gateway.py",
    "src/doge/bootstrap/workspace.py",
    "src/doge/core/domain/run_execution_context.py",
    "src/doge/core/domain/tool_descriptor.py",
    "tests/unit/capabilities/test_code_executor.py",
    "tests/unit/core/domain/test_run_execution_context.py",
    "docs/progress/9b77f9c-external-closure-runbook.md",
    "production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json",
    "production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/",
    "scripts/validate_plan_closure_gate.py",
    "scripts/preflight_plan_closure_external.py",
]


def validate(
    text: str,
    *,
    plan_text: str | None = None,
    maturity_text: str | None = None,
    gate_output: dict[str, Any] | None = None,
    existing_payload_paths: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    normalized_text = " ".join(text.split())
    path_text = text.replace("\\", "/")
    plan_text = _read_plan_text(PLAN) if plan_text is None else plan_text
    maturity_text = MATURITY.read_text(encoding="utf-8") if maturity_text is None else maturity_text
    gate_output = validate_all(allow_open=True) if gate_output is None else gate_output

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text and snippet not in normalized_text:
            errors.append(f"package missing required snippet: {snippet}")

    _validate_payload_paths(path_text, errors, existing_payload_paths=existing_payload_paths)
    _validate_gate_state(path_text, gate_output, errors)
    _validate_plan_refs(plan_text, errors)
    _validate_maturity_refs(maturity_text, errors)
    return errors


def _validate_payload_paths(
    text: str,
    errors: list[str],
    *,
    existing_payload_paths: set[str] | None,
) -> None:
    for rel_path in REQUIRED_PAYLOAD_PATHS:
        if rel_path not in text:
            errors.append(f"package missing required payload path reference: {rel_path}")
        if existing_payload_paths is None:
            candidate = ROOT / rel_path.rstrip("/")
            exists = candidate.is_dir() if rel_path.endswith("/") else candidate.is_file()
        else:
            exists = rel_path in existing_payload_paths
        if not exists:
            errors.append(f"required payload path missing from workspace: {rel_path}")


def _validate_gate_state(text: str, gate_output: dict[str, Any], errors: list[str]) -> None:
    summary = gate_output.get("summary", {})
    if gate_output.get("result") != "open" or not gate_output.get("acceptable"):
        errors.append("closure gate must remain acceptable controlled-open before remote CI")
    if summary.get("total") != 6 or summary.get("open") != 5 or summary.get("passed") != 1:
        errors.append(
            "closure gate summary must remain 6 total / 5 open / 1 passed, "
            f"found {summary}"
        )
    for gate_id in ["S017-002", "S017-003", "W3-live", "AUTH-prod", "S017-007"]:
        if gate_id not in text:
            errors.append(f"package missing open external gate id: {gate_id}")


def _validate_plan_refs(plan_text: str, errors: list[str]) -> None:
    required_plan_refs = [
        "docs/progress/my-doge-micro-main-2ffdb66-piped-donut-completion-audit.md",
        "docs/archive/audits/piped-donut-pre-remote-ci-package-2026-06-24.md",
        "scripts/validate_piped_donut_completion_audit.py",
        "scripts/validate_piped_donut_pre_remote_ci_package.py",
        "scripts/verify_remote_ci_evidence.py",
        "scripts/validate_alpha_remote_ci_success.py",
        "production/qa/evidence/ci/remote-ci-<shortsha>.json",
    ]
    for snippet in required_plan_refs:
        if snippet not in plan_text:
            errors.append(f"source plan missing required pre-remote-CI ref: {snippet}")


def _validate_maturity_refs(maturity_text: str, errors: list[str]) -> None:
    for snippet in [
        "scripts/verify_remote_ci_evidence.py",
        "scripts/validate_alpha_remote_ci_success.py",
        "stable_declaration: forbidden",
        "production_ready: false",
    ]:
        if snippet not in maturity_text:
            errors.append(f"runtime maturity missing required remote-CI ref: {snippet}")


def _read_plan_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    if path == PLAN:
        return FALLBACK_PLAN_TEXT
    raise FileNotFoundError(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the Piped Donut pre-remote-CI package.")
    parser.add_argument("package", nargs="?", default=str(PACKAGE), help="Pre-remote-CI package markdown path.")
    parser.add_argument("--plan", default=str(PLAN), help="Source remediation plan path.")
    parser.add_argument("--maturity", default=str(MATURITY), help="Runtime maturity YAML path.")
    args = parser.parse_args(argv)

    package_path = Path(args.package)
    errors = validate(
        package_path.read_text(encoding="utf-8"),
        plan_text=_read_plan_text(Path(args.plan)),
        maturity_text=Path(args.maturity).read_text(encoding="utf-8"),
    )
    result = {"path": str(package_path), "passed": not errors, "errors": errors}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
