from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_pr_template_records_local_closure_guardrails() -> None:
    text = _read(".github/PULL_REQUEST_TEMPLATE.md")

    for token in [
        "docs/architecture/source-layout-map.md",
        "src/doge/application/*",
        "Stable, GA, Production Ready",
        "SDK/OpenAPI drift",
        "ci-market",
        "ci-research",
        "ci-portfolio",
        "ci-quant",
        "ci-runtime-gateway",
        "ci-sdk",
        "ci-eval",
    ]:
        assert token in text


def test_selective_ci_jobs_exist_for_product_platform_and_eval() -> None:
    workflow = yaml.safe_load(_read(".github/workflows/ci.yml"))
    jobs = set(workflow["jobs"])

    assert {
        "ci-market",
        "ci-research",
        "ci-portfolio",
        "ci-quant",
        "ci-runtime-gateway",
        "ci-sdk",
        "ci-eval",
    } <= jobs


def test_operator_handoff_keeps_external_gates_pending() -> None:
    text = _read("production/qa/evidence/plan-closure/handoffs/local-closure-2026-07-03-operator-checklist.md")

    for token in [
        "S017-003",
        "W3-live",
        "AUTH-prod",
        "S017-007",
        "GO_LOCAL / PENDING_OPERATOR",
        "validate_financial_provider_approval_evidence.py",
        "validate_analyst_benchmark_evidence.py",
        "validate_enterprise_production_validation_evidence.py",
        "validate_sdk_release_approval_evidence.py",
        "production_ready: false",
        "stable_declaration: forbidden",
        "level_3_sdk_platform: experimental",
    ]:
        assert token in text


def test_daemon_operator_docs_match_current_cli_contract() -> None:
    text = _read("docs/start-here/daemon-operator.md")

    assert "doged serve --port 8901" in text
    assert "doged serve --host" not in text
    assert "not by a `--host` CLI flag" in text


def test_architecture_runtime_level_1_matches_maturity_authority() -> None:
    text = _read("docs/architecture/runtime-levels.md")

    assert "Current label: Alpha." in text
    assert "Current label: Preview." not in text
