import json
from pathlib import Path

from scripts.build_analyst_benchmark_evidence import build_evidence as build_analyst_benchmark
from scripts.build_enterprise_production_validation_evidence import build_evidence as build_enterprise
from scripts.build_financial_provider_approval_evidence import build_evidence as build_provider
from scripts.build_screen_reader_evidence import build_evidence as build_screen_reader
from scripts.build_sdk_release_approval_evidence import build_evidence as build_sdk
from scripts.validate_analyst_benchmark_evidence import validate as validate_analyst_benchmark
from scripts.validate_enterprise_production_validation_evidence import validate as validate_enterprise
from scripts.validate_financial_provider_approval_evidence import validate as validate_provider
from scripts.validate_screen_reader_evidence import validate as validate_screen_reader
from scripts.validate_sdk_release_approval_evidence import validate as validate_sdk


ROOT = Path(__file__).resolve().parents[3]


def test_provider_decision_template_builds_non_closing_evidence():
    payload = build_provider(
        decisions_path=ROOT / "production/qa/evidence/provider/provider-decisions-template-2026-06-22.json",
        created_at="2026-06-22T06:00:00Z",
    )

    assert payload["result"] == "needs_revision"
    assert payload["issue_refs"] == ["S017-003-TEMPLATE"]
    assert _has_placeholder_error(validate_provider(payload), "S017-003-TEMPLATE")


def test_sdk_release_decision_template_builds_non_closing_evidence():
    payload = build_sdk(
        decisions_path=ROOT / "production/qa/evidence/sdk/sdk-release-decisions-template-2026-06-22.json",
        created_at="2026-06-22T06:00:00Z",
    )

    assert payload["result"] == "needs_revision"
    assert payload["issue_refs"] == ["S017-007-TEMPLATE"]
    assert _has_placeholder_error(validate_sdk(payload), "S017-007-TEMPLATE")


def test_screen_reader_observation_template_builds_failed_evidence():
    payload = build_screen_reader(
        observations_path=ROOT / "production/qa/evidence/manual/screen-reader-observations-template-2026-06-22.json",
        created_at="2026-06-22T06:00:00Z",
    )

    assert payload["result"] == "failed"
    assert payload["issues"] == ["S017-006-TEMPLATE"]
    errors = validate_screen_reader(payload)
    assert _has_placeholder_error(errors, "S017-006-TEMPLATE")
    assert _has_placeholder_error(errors, "TEMPLATE_BROWSER")


def test_enterprise_production_observation_template_builds_failed_evidence():
    payload = build_enterprise(
        observations_path=ROOT / "production/qa/evidence/enterprise/enterprise-production-observations-template-2026-06-22.json",
        created_at="2026-06-22T06:00:00Z",
    )

    assert payload["result"] == "failed"
    assert payload["issue_refs"] == ["AUTH-PROD-TEMPLATE"]
    assert _has_placeholder_error(validate_enterprise(payload), "AUTH-PROD-TEMPLATE")


def test_analyst_benchmark_input_templates_build_failed_evidence():
    payload = build_analyst_benchmark(
        gold_cases_path=ROOT / "tests/eval/gold_cases.json",
        observations_path=ROOT / "production/qa/evidence/eval/live-kimi-observations-template-2026-06-22.json",
        thresholds_path=ROOT / "production/qa/evidence/eval/approved-thresholds-template-2026-06-22.json",
        material_manifest_ref="production/qa/evidence/eval/material-manifest-template-2026-06-22.json",
        label_manifest_ref="production/qa/evidence/eval/label-manifest-template-2026-06-22.json",
        label_policy_ref="docs/progress/financial-eval-gold-set.md",
        live_observation_ref="production/qa/evidence/eval/live-kimi-observations-template-2026-06-22.json",
        trend_history_ref="production/qa/evidence/eval/trend-history-template-2026-06-22.jsonl",
        analyst_role="research-qa-analyst",
        analyst_initials="QA",
        reviewed_at="2026-06-22T06:00:00Z",
        created_at="2026-06-22T06:01:00Z",
        issue_refs=["W3-LIVE-TEMPLATE"],
    )

    assert payload["result"] == "failed"
    assert payload["issue_refs"] == ["W3-LIVE-TEMPLATE"]
    assert _has_placeholder_error(validate_analyst_benchmark(payload), "W3-LIVE-TEMPLATE")


def test_manifest_handoff_input_templates_exist_and_are_json_or_jsonl():
    manifest = json.loads((ROOT / "production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json").read_text(encoding="utf-8"))
    templates = [
        template
        for task in manifest["tasks"]
        for template in task["handoff"].get("input_templates", [])
    ]

    assert templates
    for template in templates:
        path = ROOT / template
        assert path.exists()
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        else:
            assert path.suffix == ".jsonl"
            assert path.read_text(encoding="utf-8").strip()


def _has_placeholder_error(errors: list[str], placeholder: str) -> bool:
    return any(f"unresolved placeholder: {placeholder}" in error for error in errors)
