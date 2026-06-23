from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_plan_closure_gate import validate_all


DEFAULT_OUTPUT = (
    ROOT
    / "production"
    / "qa"
    / "evidence"
    / "plan-closure"
    / "9b77f9c-external-closure-manifest.json"
)

HANDOFFS = {
    "S017-002": {
        "kind": "live_runner",
        "input_templates": [],
        "input_refs": ["env:DOGE_LIVE_KIMI=1", "env:MOONSHOT_API_KEY", "optional:env:DOGE_LIVE_KIMI_AGENT_SDK=1"],
        "build_or_run_command": (
            ".\\.venv\\Scripts\\python.exe scripts\\run_kimi_live_smoke.py "
            "--output-dir production/qa/evidence/live"
        ),
        "output_ref": "production/qa/evidence/live/kimi-live-smoke-2026-06-22.json",
        "close_condition": "result must be passed; blocked evidence remains open",
    },
    "S017-003": {
        "kind": "evidence_builder",
        "input_templates": ["production/qa/evidence/provider/provider-decisions-template-2026-06-22.json"],
        "input_refs": ["production/qa/evidence/provider/provider-decisions-YYYY-MM-DD.json"],
        "build_or_run_command": (
            ".\\.venv\\Scripts\\python.exe scripts\\build_financial_provider_approval_evidence.py "
            "--decisions production/qa/evidence/provider/provider-decisions-YYYY-MM-DD.json "
            "--output production/qa/evidence/provider/financial-provider-approval-YYYY-MM-DD.json "
            "--created-at \"YYYY-MM-DDTHH:MM:SSZ\""
        ),
        "output_ref": "production/qa/evidence/provider/financial-provider-approval-YYYY-MM-DD.json",
        "close_condition": "result must be approved; needs_revision/rejected evidence remains open",
    },
    "W3-live": {
        "kind": "evidence_builder",
        "input_templates": [
            "production/qa/evidence/eval/live-kimi-observations-template-2026-06-22.json",
            "production/qa/evidence/eval/approved-thresholds-template-2026-06-22.json",
            "production/qa/evidence/eval/material-manifest-template-2026-06-22.json",
            "production/qa/evidence/eval/label-manifest-template-2026-06-22.json",
            "production/qa/evidence/eval/trend-history-template-2026-06-22.jsonl",
        ],
        "input_refs": [
            "production/qa/evidence/eval/live-kimi-observations-redacted.json",
            "production/qa/evidence/eval/approved-thresholds.json",
            "production/qa/evidence/eval/material-manifest-approved.json",
            "production/qa/evidence/eval/label-manifest-approved.json",
            "production/qa/evidence/eval/trend-history.jsonl",
        ],
        "build_or_run_command": (
            ".\\.venv\\Scripts\\python.exe scripts\\build_analyst_benchmark_evidence.py "
            "--observations production/qa/evidence/eval/live-kimi-observations-redacted.json "
            "--thresholds production/qa/evidence/eval/approved-thresholds.json "
            "--output production/qa/evidence/eval/analyst-benchmark-YYYY-MM-DD.json "
            "--material-manifest-ref production/qa/evidence/eval/material-manifest-approved.json "
            "--label-manifest-ref production/qa/evidence/eval/label-manifest-approved.json "
            "--label-policy-ref docs/progress/financial-eval-gold-set.md "
            "--live-observation-ref production/qa/evidence/eval/live-kimi-observations-redacted.json "
            "--trend-history-ref production/qa/evidence/eval/trend-history.jsonl "
            "--analyst-role research-qa-analyst --analyst-initials \"<initials>\" "
            "--reviewed-at \"YYYY-MM-DDTHH:MM:SSZ\""
        ),
        "output_ref": "production/qa/evidence/eval/analyst-benchmark-YYYY-MM-DD.json",
        "close_condition": "result must be passed; failed evidence remains open",
    },
    "AUTH-prod": {
        "kind": "evidence_builder",
        "input_templates": [
            "production/qa/evidence/enterprise/enterprise-production-observations-template-2026-06-22.json"
        ],
        "input_refs": ["production/qa/evidence/enterprise/enterprise-production-observations-YYYY-MM-DD.json"],
        "build_or_run_command": (
            ".\\.venv\\Scripts\\python.exe scripts\\build_enterprise_production_validation_evidence.py "
            "--observations production/qa/evidence/enterprise/enterprise-production-observations-YYYY-MM-DD.json "
            "--output production/qa/evidence/enterprise/enterprise-production-validation-YYYY-MM-DD.json "
            "--created-at \"YYYY-MM-DDTHH:MM:SSZ\""
        ),
        "output_ref": "production/qa/evidence/enterprise/enterprise-production-validation-YYYY-MM-DD.json",
        "close_condition": "result must be passed; failed evidence remains open",
    },
    "S017-006": {
        "kind": "evidence_builder",
        "input_templates": ["production/qa/evidence/manual/screen-reader-observations-template-2026-06-22.json"],
        "input_refs": ["production/qa/evidence/manual/screen-reader-observations-YYYY-MM-DD.json"],
        "build_or_run_command": (
            ".\\.venv\\Scripts\\python.exe scripts\\build_screen_reader_evidence.py "
            "--observations production/qa/evidence/manual/screen-reader-observations-YYYY-MM-DD.json "
            "--output production/qa/evidence/manual/research-agent-screen-reader-manual-YYYY-MM-DD.json "
            "--created-at \"YYYY-MM-DDTHH:MM:SSZ\""
        ),
        "output_ref": "production/qa/evidence/manual/research-agent-screen-reader-manual-YYYY-MM-DD.json",
        "close_condition": "result must be passed; failed evidence remains open",
    },
    "S017-007": {
        "kind": "evidence_builder",
        "input_templates": ["production/qa/evidence/sdk/sdk-release-decisions-template-2026-06-22.json"],
        "input_refs": ["production/qa/evidence/sdk/sdk-release-decisions-approved.json"],
        "build_or_run_command": (
            ".\\.venv\\Scripts\\python.exe scripts\\build_sdk_release_approval_evidence.py "
            "--decisions production/qa/evidence/sdk/sdk-release-decisions-approved.json "
            "--output production/qa/evidence/sdk/sdk-release-approval-YYYY-MM-DD.json "
            "--created-at \"YYYY-MM-DDTHH:MM:SSZ\""
        ),
        "output_ref": "production/qa/evidence/sdk/sdk-release-approval-YYYY-MM-DD.json",
        "close_condition": "result must be approved; needs_revision/rejected evidence remains open",
    },
}


def build_manifest(*, generated_at: str | None = None) -> dict[str, Any]:
    gate = validate_all(allow_open=True)
    return {
        "schema": "doge.plan_closure_execution_manifest.v1",
        "source_plan": gate["source_plan"],
        "source_plan_check": _source_plan_check(gate["source_plan"]),
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "closure_gate": {
            "result": gate["result"],
            "acceptable_with_open_items": gate["acceptable"],
            "summary": gate["summary"],
            "posture": gate["posture"],
        },
        "operator_rule": (
            "Complete each task to its required_results, run its validator_command without allow-template/"
            "allow-blocked flags, then run scripts/validate_plan_closure_gate.py without --allow-open."
        ),
        "tasks": [_task_from_gate(item) for item in gate["gates"]],
    }


def _task_from_gate(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "title": item["title"],
        "current_status": item["status"],
        "current_result": item["evidence_result"],
        "required_results": item["passing_results"],
        "current_evidence": item["evidence"],
        "fallback_evidence": item["fallback_evidence"],
        "completed_evidence_glob": item["completed_glob"],
        "validator_command": item["strict_command"],
        "next_action": item["next_action"],
        "current_blockers": item["strict_errors"],
        "can_close_now": item["status"] == "passed",
        "handoff": HANDOFFS[item["id"]],
    }


def _source_plan_check(source_plan: str) -> dict[str, Any]:
    if _is_external_path_ref(source_plan):
        return {
            "path": source_plan,
            "exists": False,
            "sha256": None,
            "bytes": None,
            "external_to_repo": True,
            "reason": "source plan path is external to the repository and is not hashed in CI",
        }
    path = Path(source_plan)
    if not path.exists():
        return {
            "path": source_plan,
            "exists": False,
            "sha256": None,
            "bytes": None,
            "external_to_repo": False,
        }
    content = path.read_bytes()
    return {
        "path": source_plan,
        "exists": True,
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
        "external_to_repo": False,
    }


def _is_external_path_ref(source_plan: str) -> bool:
    if re.match(r"^[A-Za-z]:[\\/]", source_plan):
        return True
    path = Path(source_plan)
    if not path.is_absolute():
        return False
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return True
    return False


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the 9b77f9c external closure execution manifest.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON path.")
    args = parser.parse_args(argv)

    manifest = build_manifest()
    output = Path(args.output)
    write_manifest(output, manifest)
    print(json.dumps({"path": str(output), "tasks": len(manifest["tasks"])}, indent=2, sort_keys=True))
    summary = manifest["closure_gate"]["summary"]
    return 0 if summary["invalid"] == 0 and summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
