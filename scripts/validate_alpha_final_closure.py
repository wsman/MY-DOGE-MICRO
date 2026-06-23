from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_alpha_remote_ci_success import (
    success_run_urls,
    validate as validate_remote_ci_success,
)
from scripts.validate_plan_closure_gate import validate_all


PLAN = Path(r"C:\Users\Aby\.claude\plans\alpha-magical-peach.md")
MATURITY = ROOT / "docs" / "progress" / "runtime-maturity.yaml"


def validate(
    remote_ci_payload: dict[str, Any],
    *,
    evidence_path: str | Path,
    expected_head_sha: str,
    plan_text: str,
    maturity_text: str,
    gate_output: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> list[str]:
    errors = validate_remote_ci_success(
        remote_ci_payload,
        expected_head_sha=expected_head_sha,
        evidence_path=evidence_path,
        require_canonical_path=True,
        root=root,
    )
    gate_output = validate_all(allow_open=True) if gate_output is None else gate_output

    head_sha = remote_ci_payload.get("head_sha")
    if not isinstance(head_sha, str):
        head_sha = ""
    short_sha = head_sha[:7]
    urls = success_run_urls(remote_ci_payload)
    evidence_ref = _canonical_evidence_ref(evidence_path)

    _validate_final_plan(
        plan_text,
        expected_head_sha=expected_head_sha,
        short_sha=short_sha,
        success_urls=urls,
        evidence_ref=evidence_ref,
        errors=errors,
    )
    _validate_maturity(
        maturity_text,
        expected_head_sha=expected_head_sha,
        success_urls=urls,
        evidence_ref=evidence_ref,
        errors=errors,
    )
    _validate_gate_output(gate_output, plan_text=plan_text, errors=errors)
    return errors


def _validate_final_plan(
    plan_text: str,
    *,
    expected_head_sha: str,
    short_sha: str,
    success_urls: list[str],
    evidence_ref: str,
    errors: list[str],
) -> None:
    required_snippets = [
        "- [x] Remote CI success is linked for the repaired target SHA",
        "- [x] Remote CI success is linked for the target HEAD",
        expected_head_sha,
        short_sha,
        evidence_ref,
        "`production_ready: false`",
        "`stable_declaration: forbidden`",
        "Level 3 `experimental`",
    ]
    for snippet in required_snippets:
        if snippet not in plan_text:
            errors.append(f"final plan missing required closure snippet: {snippet}")

    forbidden_snippets = [
        "- [ ] Remote CI success is linked for the repaired target SHA",
        "- [ ] Remote CI success is linked for the target HEAD",
    ]
    for snippet in forbidden_snippets:
        if snippet in plan_text:
            errors.append(f"final plan must not leave remote CI unchecked: {snippet}")

    if not success_urls:
        errors.append("remote CI evidence must provide at least one success run URL for final closure")
    for url in success_urls:
        if url not in plan_text:
            errors.append(f"final plan missing remote CI success run URL: {url}")


def _validate_maturity(
    maturity_text: str,
    *,
    expected_head_sha: str,
    success_urls: list[str],
    evidence_ref: str,
    errors: list[str],
) -> None:
    required_snippets = [
        "stable_declaration: forbidden",
        "level_3_sdk_platform: experimental",
        "production_ready: false",
        expected_head_sha,
        evidence_ref,
    ]
    for snippet in required_snippets:
        if snippet not in maturity_text:
            errors.append(f"runtime maturity missing final closure snippet: {snippet}")
    for url in success_urls:
        if url not in maturity_text:
            errors.append(f"runtime maturity missing remote CI success run URL: {url}")


def _validate_gate_output(gate_output: dict[str, Any], *, plan_text: str, errors: list[str]) -> None:
    if gate_output.get("schema") != "doge.plan_closure_gate.v1":
        errors.append("closure gate output schema must be doge.plan_closure_gate.v1")
    if not gate_output.get("acceptable"):
        errors.append("closure gate must be acceptable for final Alpha closure")
    summary = gate_output.get("summary", {})
    if summary.get("total") != 6:
        errors.append(f"closure gate summary must report 6 total gates, found {summary}")
    if summary.get("failed", 0) or summary.get("invalid", 0):
        errors.append(f"closure gate must have no failed/invalid gates, found {summary}")
    if gate_output.get("result") == "open":
        if summary.get("open") != 5 or summary.get("passed") != 1:
            errors.append(f"controlled-open Alpha closure must report 5 open / 1 passed gates, found {summary}")
        if "controlled open gates" not in plan_text and "controlled-open" not in plan_text:
            errors.append("final plan must explicitly preserve controlled-open Alpha gates")
    elif gate_output.get("result") != "passed":
        errors.append(f"closure gate result must be open or passed, found {gate_output.get('result')}")
    if (
        "docs/archive/audits/external-gate-next-actions-2026-06-23.md" not in plan_text
        and "production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json" not in plan_text
    ):
        errors.append("final plan must reference current external gate next-actions or closure manifest evidence")
    _validate_gate_details(gate_output, errors=errors)


def _validate_gate_details(gate_output: dict[str, Any], *, errors: list[str]) -> None:
    expected_ids = {"S017-002", "S017-003", "W3-live", "AUTH-prod", "S017-006", "S017-007"}
    gates = gate_output.get("gates")
    if not isinstance(gates, list):
        errors.append("closure gate output must include gates list")
        return
    by_id = {gate.get("id"): gate for gate in gates if isinstance(gate, dict)}
    missing_ids = sorted(expected_ids - set(by_id))
    unexpected_ids = sorted(set(by_id) - expected_ids)
    if missing_ids:
        errors.append("closure gate output missing gate ids: " + ", ".join(missing_ids))
    if unexpected_ids:
        errors.append("closure gate output has unexpected gate ids: " + ", ".join(unexpected_ids))
    required_fields = [
        "id",
        "title",
        "status",
        "evidence",
        "evidence_result",
        "next_action",
        "passing_results",
        "strict_command",
        "strict_errors",
    ]
    for gate_id in sorted(expected_ids & set(by_id)):
        gate = by_id[gate_id]
        for field in required_fields:
            if field not in gate:
                errors.append(f"closure gate {gate_id} missing required field: {field}")
        status = gate.get("status")
        if status == "open":
            if not gate.get("next_action"):
                errors.append(f"closure gate {gate_id} must include next_action while open")
            if not gate.get("strict_errors"):
                errors.append(f"closure gate {gate_id} must include strict_errors while open")
        elif status == "passed":
            if gate.get("strict_errors"):
                errors.append(f"closure gate {gate_id} passed gate must not include strict_errors")
        else:
            errors.append(f"closure gate {gate_id} status must be open or passed")


def _canonical_evidence_ref(evidence_path: str | Path) -> str:
    return (Path("production/qa/evidence/ci") / Path(evidence_path).name).as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate final closure for the Alpha Magical Peach plan after exact-SHA remote CI success."
    )
    parser.add_argument("--remote-ci-evidence", required=True, type=Path)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--plan", default=str(PLAN))
    parser.add_argument("--maturity", default=str(MATURITY))
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root for canonical evidence path validation.")
    args = parser.parse_args(argv)

    payload = json.loads(args.remote_ci_evidence.read_text(encoding="utf-8"))
    errors = validate(
        payload,
        evidence_path=args.remote_ci_evidence,
        expected_head_sha=args.expected_head,
        plan_text=Path(args.plan).read_text(encoding="utf-8"),
        maturity_text=Path(args.maturity).read_text(encoding="utf-8"),
        root=args.root,
    )
    result = {
        "passed": not errors,
        "errors": errors,
        "remote_ci_evidence": str(args.remote_ci_evidence),
        "expected_head": args.expected_head,
        "success_run_urls": success_run_urls(payload),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
