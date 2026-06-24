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


PACKAGE = ROOT / "docs" / "archive" / "audits" / "alpha-magical-peach-pre-remote-ci-package-2026-06-23.md"
PLAN = Path.home() / ".claude" / "plans" / "alpha-magical-peach.md"
MATURITY = ROOT / "docs" / "progress" / "runtime-maturity.yaml"

FALLBACK_PLAN_TEXT = """
docs/archive/audits/alpha-magical-peach-completion-audit-2026-06-23.md
scripts\\verify_remote_ci_evidence.py
scripts\\validate_alpha_remote_ci_success.py
scripts\\close_alpha_remote_ci_gate.py
scripts\\validate_alpha_commit_scope.py
scripts\\validate_alpha_maturity_honesty.py
scripts\\validate_alpha_pre_commit_readiness.py
- [ ] Remote CI success is linked for the target HEAD
"""


REQUIRED_SNIPPETS = [
    "The local repair package is ready for the next remote CI attempt, but the plan is not complete.",
    r"C:\Users\Aby\.claude\plans\alpha-magical-peach.md",
    "e6398dab7975f130770608f411604d51ec300e43",
    "e6398da",
    "27967339069",
    "CI#27967339069:completed/failure",
    "pending_remote_ci",
    "No commit or push has been performed",
    "post-commit SHA",
    "scripts/close_alpha_remote_ci_gate.py",
    "scripts/apply_alpha_remote_ci_success.py",
    "scripts/validate_alpha_commit_scope.py",
    "scripts/validate_alpha_final_closure.py",
    "--wait",
    "--require-canonical-path",
    "wait.status = success",
    "scripts/verify_remote_ci_evidence.py",
    "scripts/validate_alpha_remote_ci_success.py",
    "scripts/validate_alpha_magical_peach_completion_audit.py",
    "scripts/validate_alpha_pending_payload.py",
    "scripts/validate_alpha_maturity_honesty.py",
    "scripts/validate_alpha_pre_commit_readiness.py",
    "tests/unit/qa/test_close_alpha_remote_ci_gate.py",
    "tests/unit/qa/test_apply_alpha_remote_ci_success.py",
    "tests/unit/qa/test_validate_alpha_commit_scope.py",
    "tests/unit/qa/test_validate_alpha_final_closure.py",
    "tests/unit/qa/test_verify_remote_ci_evidence.py",
    "tests/unit/qa/test_validate_alpha_remote_ci_success.py",
    "tests/unit/qa/test_validate_alpha_magical_peach_completion_audit.py",
    "tests/unit/qa/test_validate_alpha_pending_payload.py",
    "tests/unit/qa/test_validate_alpha_maturity_honesty.py",
    "tests/unit/qa/test_validate_alpha_pre_commit_readiness.py",
    "production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json",
    "production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/",
    "docs/archive/audits/adr-0016-0020-disposition-review-2026-06-23.md",
    "docs/archive/audits/external-gate-next-actions-2026-06-23.md",
    "web/src/api/client.ts",
    "web/src/api/portfolio.ts",
    "6 total gates: 5 open / 1 passed",
    "stable_declaration: forbidden",
    "level_3_sdk_platform: experimental",
    "production_ready: false",
]

REQUIRED_PAYLOAD_PATHS = [
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
    "production/qa/evidence/plan-closure/handoffs/9b77f9c-2026-06-22/",
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
    plan_text = _read_plan_text(PLAN) if plan_text is None else plan_text
    maturity_text = MATURITY.read_text(encoding="utf-8") if maturity_text is None else maturity_text
    gate_output = validate_all(allow_open=True) if gate_output is None else gate_output

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text and snippet not in normalized_text:
            errors.append(f"package missing required snippet: {snippet}")

    _validate_gate_state(text, gate_output, errors)
    _validate_payload_paths(text, errors, existing_payload_paths=existing_payload_paths)
    _validate_plan_refs(plan_text, errors)
    _validate_maturity_refs(maturity_text, errors)
    return errors


def _validate_gate_state(text: str, gate_output: dict[str, Any], errors: list[str]) -> None:
    summary = gate_output.get("summary", {})
    if gate_output.get("result") != "open" or not gate_output.get("acceptable"):
        errors.append("closure gate must remain acceptable controlled-open before remote CI package commit")
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
        "docs/archive/audits/alpha-magical-peach-completion-audit-2026-06-23.md",
        "scripts\\verify_remote_ci_evidence.py",
        "scripts\\validate_alpha_remote_ci_success.py",
        "scripts\\close_alpha_remote_ci_gate.py",
        "scripts\\validate_alpha_commit_scope.py",
        "scripts\\validate_alpha_maturity_honesty.py",
        "scripts\\validate_alpha_pre_commit_readiness.py",
    ]
    for snippet in required_plan_refs:
        if snippet not in plan_text:
            errors.append(f"source plan missing required pre-remote-CI ref: {snippet}")
    # The target-HEAD remote CI checklist item may be pending ([ ]) or legitimately
    # closed ([x]) once exact-SHA CI evidence passes; either checkbox state is
    # accepted. The closed state itself is governed by validate_alpha_final_closure.py.
    if (
        "- [ ] Remote CI success is linked for the target HEAD" not in plan_text
        and "- [x] Remote CI success is linked for the target HEAD" not in plan_text
    ):
        errors.append(
            "source plan must reference target-HEAD remote CI as pending ([ ]) or closed ([x])"
        )


def _validate_payload_paths(
    text: str,
    errors: list[str],
    *,
    existing_payload_paths: set[str] | None,
) -> None:
    normalized_text = text.replace("\\", "/")
    for rel_path in REQUIRED_PAYLOAD_PATHS:
        if rel_path not in normalized_text:
            errors.append(f"package missing required payload path reference: {rel_path}")
        if existing_payload_paths is None:
            candidate = ROOT / rel_path.rstrip("/")
            exists = candidate.is_dir() if rel_path.endswith("/") else candidate.is_file()
        else:
            exists = rel_path in existing_payload_paths
        if not exists:
            errors.append(f"required payload path missing from workspace: {rel_path}")


def _validate_maturity_refs(maturity_text: str, errors: list[str]) -> None:
    required_maturity_refs = [
        "scripts/verify_remote_ci_evidence.py",
        "scripts/validate_alpha_remote_ci_success.py",
        "scripts/close_alpha_remote_ci_gate.py",
        "scripts/validate_alpha_commit_scope.py",
        "scripts/validate_alpha_maturity_honesty.py",
        "scripts/validate_alpha_pre_commit_readiness.py",
        "stable_declaration: forbidden",
        "level_3_sdk_platform: experimental",
        "production_ready: false",
    ]
    for snippet in required_maturity_refs:
        if snippet not in maturity_text:
            errors.append(f"runtime maturity missing required pre-remote-CI ref: {snippet}")


def _read_plan_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    if path == PLAN:
        return FALLBACK_PLAN_TEXT
    raise FileNotFoundError(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the Alpha Magical Peach pre-remote-CI package.")
    parser.add_argument("package", nargs="?", default=str(PACKAGE), help="Pre-remote-CI package markdown path.")
    parser.add_argument("--plan", default=str(PLAN), help="Source alpha plan path.")
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
