from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_analyst_benchmark_evidence import validate as validate_analyst_benchmark
from scripts.validate_enterprise_production_validation_evidence import validate as validate_enterprise_production
from scripts.validate_financial_provider_approval_evidence import validate as validate_financial_provider
from scripts.validate_kimi_live_smoke_evidence import validate as validate_kimi_live
from scripts.validate_screen_reader_evidence import validate as validate_screen_reader
from scripts.validate_sdk_release_approval_evidence import validate as validate_sdk_release


RUNTIME_MATURITY = ROOT / "docs" / "progress" / "runtime-maturity.yaml"


@dataclass(frozen=True)
class EvidenceGate:
    gate_id: str
    title: str
    path: Path
    validator: Callable[..., list[str]]
    allow_kwarg: str
    open_results: frozenset[str]
    passing_results: frozenset[str]
    next_action: str
    strict_command: str
    completed_glob: str | None = None


GATES = [
    EvidenceGate(
        gate_id="S017-002",
        title="Live Kimi smoke execution",
        path=ROOT / "production" / "qa" / "evidence" / "live" / "kimi-live-smoke-2026-06-22.json",
        validator=validate_kimi_live,
        allow_kwarg="allow_blocked",
        open_results=frozenset({"blocked"}),
        passing_results=frozenset({"passed"}),
        next_action=(
            "Run scripts/run_kimi_live_smoke.py in an operator-approved Kimi credential/spend window with "
            "DOGE_LIVE_KIMI=1 and MOONSHOT_API_KEY set, then replace the blocked evidence with the live result."
        ),
        strict_command=(
            ".\\.venv\\Scripts\\python.exe scripts\\validate_kimi_live_smoke_evidence.py "
            "production/qa/evidence/live/kimi-live-smoke-2026-06-22.json"
        ),
    ),
    EvidenceGate(
        gate_id="S017-003",
        title="Financial provider fixture approval",
        path=ROOT / "production" / "qa" / "evidence" / "provider" / "financial-provider-approval-template-2026-06-22.json",
        validator=validate_financial_provider,
        allow_kwarg="allow_template",
        open_results=frozenset({"not_run"}),
        passing_results=frozenset({"approved"}),
        next_action=(
            "Complete the provider approval template with product/operator decisions, license scope, fixture storage "
            "policy, freshness, provenance, and reviewer sign-off."
        ),
        strict_command=(
            ".\\.venv\\Scripts\\python.exe scripts\\validate_financial_provider_approval_evidence.py "
            "production/qa/evidence/provider/financial-provider-approval-template-2026-06-22.json"
        ),
        completed_glob="financial-provider-approval-*.json",
    ),
    EvidenceGate(
        gate_id="W3-live",
        title="Analyst-labeled financial eval benchmark",
        path=ROOT / "production" / "qa" / "evidence" / "eval" / "analyst-benchmark-template-2026-06-22.json",
        validator=validate_analyst_benchmark,
        allow_kwarg="allow_template",
        open_results=frozenset({"not_run"}),
        passing_results=frozenset({"passed"}),
        next_action=(
            "Fill the analyst benchmark evidence with real materials, human citation labels, live Kimi observations, "
            "thresholds, and trend-history metadata."
        ),
        strict_command=(
            ".\\.venv\\Scripts\\python.exe scripts\\validate_analyst_benchmark_evidence.py "
            "production/qa/evidence/eval/analyst-benchmark-template-2026-06-22.json"
        ),
        completed_glob="analyst-benchmark-*.json",
    ),
    EvidenceGate(
        gate_id="AUTH-prod",
        title="Enterprise production validation",
        path=ROOT / "production" / "qa" / "evidence" / "enterprise" / "enterprise-production-validation-template-2026-06-22.json",
        validator=validate_enterprise_production,
        allow_kwarg="allow_template",
        open_results=frozenset({"not_run"}),
        passing_results=frozenset({"passed"}),
        next_action=(
            "Execute enterprise production validation against operator-approved IdP/JWKS, secret-store command, "
            "SIEM/WORM sink, remote deployment, and data-isolation review evidence."
        ),
        strict_command=(
            ".\\.venv\\Scripts\\python.exe scripts\\validate_enterprise_production_validation_evidence.py "
            "production/qa/evidence/enterprise/enterprise-production-validation-template-2026-06-22.json"
        ),
        completed_glob="enterprise-production-validation-*.json",
    ),
    EvidenceGate(
        gate_id="S017-006",
        title="Research Agent screen-reader manual pass",
        path=ROOT / "production" / "qa" / "evidence" / "manual" / "research-agent-screen-reader-manual-template-2026-06-22.json",
        validator=validate_screen_reader,
        allow_kwarg="allow_template",
        open_results=frozenset({"not_run"}),
        passing_results=frozenset({"passed"}),
        next_action=(
            "Run the S017 screen-reader manual protocol with an approved screen reader/browser combination and "
            "record pass/fail evidence."
        ),
        strict_command=(
            ".\\.venv\\Scripts\\python.exe scripts\\validate_screen_reader_evidence.py "
            "production/qa/evidence/manual/research-agent-screen-reader-manual-template-2026-06-22.json"
        ),
        completed_glob="research-agent-screen-reader-manual-*.json",
    ),
    EvidenceGate(
        gate_id="S017-007",
        title="SDK registry publication approval",
        path=ROOT / "production" / "qa" / "evidence" / "sdk" / "sdk-release-approval-template-2026-06-22.json",
        validator=validate_sdk_release,
        allow_kwarg="allow_template",
        open_results=frozenset({"not_run"}),
        passing_results=frozenset({"approved"}),
        next_action=(
            "Complete SDK release approval with registry targets, package-name ownership, version/changelog policy, "
            "registry-backed consumer smoke, and release-manager sign-off."
        ),
        strict_command=(
            ".\\.venv\\Scripts\\python.exe scripts\\validate_sdk_release_approval_evidence.py "
            "production/qa/evidence/sdk/sdk-release-approval-template-2026-06-22.json"
        ),
        completed_glob="sdk-release-approval-*.json",
    ),
]


def validate_all(*, allow_open: bool = False) -> dict[str, Any]:
    gate_results = [_validate_gate(gate, allow_open=allow_open) for gate in GATES]
    posture_errors = _validate_non_production_posture()
    summary = {
        "total": len(gate_results),
        "passed": sum(1 for item in gate_results if item["status"] == "passed"),
        "open": sum(1 for item in gate_results if item["status"] == "open"),
        "failed": sum(1 for item in gate_results if item["status"] == "failed"),
        "invalid": sum(1 for item in gate_results if item["status"] == "invalid"),
    }
    complete = summary["passed"] == summary["total"] and not posture_errors
    acceptable = complete or (allow_open and summary["failed"] == 0 and summary["invalid"] == 0 and not posture_errors)
    return {
        "schema": "doge.plan_closure_gate.v1",
        "source_plan": "C:\\Users\\Aby\\.claude\\plans\\9b77f9c-kimi-twinkly-map.md",
        "result": "complete" if complete else "open",
        "acceptable": acceptable,
        "summary": summary,
        "posture": {
            "runtime_maturity": _display_path(RUNTIME_MATURITY),
            "production_ready_false": "production_ready: false" in _runtime_text(),
            "stable_declaration_forbidden": "stable_declaration: forbidden" in _runtime_text(),
            "errors": posture_errors,
        },
        "gates": gate_results,
    }


def _validate_gate(gate: EvidenceGate, *, allow_open: bool) -> dict[str, Any]:
    evidence_path = _resolve_evidence_path(gate)
    if not evidence_path.exists():
        return _gate_result(gate, status="invalid", result=None, strict_errors=[f"missing evidence: {evidence_path}"])
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    strict_errors = gate.validator(payload)
    allowed_errors = gate.validator(payload, **{gate.allow_kwarg: True})
    result = payload.get("result")

    if not strict_errors:
        status = "passed" if result in gate.passing_results else "failed"
    elif result in gate.open_results and not allowed_errors:
        status = "open"
    elif not allowed_errors:
        status = "failed"
    else:
        status = "invalid"

    return _gate_result(
        gate,
        status=status,
        result=result,
        strict_errors=strict_errors,
        allowed_errors=allowed_errors,
        evidence_path=_display_path(evidence_path),
    )


def _resolve_evidence_path(gate: EvidenceGate) -> Path:
    if not gate.completed_glob:
        return gate.path
    completed = [
        path
        for path in gate.path.parent.glob(gate.completed_glob)
        if path.is_file() and "template" not in path.name
    ]
    if not completed:
        return gate.path
    return max(completed, key=lambda path: path.stat().st_mtime)


def _gate_result(
    gate: EvidenceGate,
    *,
    status: str,
    result: Any,
    strict_errors: list[str],
    allowed_errors: list[str] | None = None,
    evidence_path: str | None = None,
) -> dict[str, Any]:
    return {
        "id": gate.gate_id,
        "title": gate.title,
        "status": status,
        "evidence": evidence_path,
        "fallback_evidence": _display_path(gate.path),
        "completed_glob": gate.completed_glob,
        "evidence_result": result,
        "passing_results": sorted(gate.passing_results),
        "next_action": gate.next_action,
        "strict_command": _strict_command(gate, evidence_path),
        "strict_errors": strict_errors,
        "allowed_errors": allowed_errors or [],
    }


def _strict_command(gate: EvidenceGate, evidence_path: str | None) -> str:
    if not evidence_path:
        return gate.strict_command
    fallback = _display_path(gate.path)
    return gate.strict_command.replace(fallback, evidence_path)


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _validate_non_production_posture() -> list[str]:
    text = _runtime_text()
    errors: list[str] = []
    if not re.search(r"(?m)^stable_declaration:\s*forbidden\s*$", text):
        errors.append("runtime maturity must keep stable_declaration: forbidden")
    if not re.search(r"(?m)^\s+production_ready:\s*false\s*$", text):
        errors.append("runtime maturity must keep maturity_labels.production_ready: false")
    return errors


def _runtime_text() -> str:
    return RUNTIME_MATURITY.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the 9b77f9c plan external closure gate.")
    parser.add_argument("--allow-open", action="store_true", help="Return 0 when remaining gates are controlled open items.")
    args = parser.parse_args(argv)

    result = validate_all(allow_open=args.allow_open)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["acceptable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
