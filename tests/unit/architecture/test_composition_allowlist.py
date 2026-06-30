"""Compatibility allowlist for ``doge.application.composition``."""

from __future__ import annotations

import ast
from pathlib import Path

import doge.application.composition as composition


PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMPOSITION_PATH = PROJECT_ROOT / "src" / "doge" / "application" / "composition.py"
COMPATIBILITY_REGISTRY = PROJECT_ROOT / "docs" / "architecture" / "compatibility-surfaces.md"

_GATEWAY_BACKED = (
    "build_view_repository",
    "build_view_service",
    "build_stock_repository",
    "build_stock_service",
    "build_report_repository",
    "build_schema_browser",
    "build_note_repository",
    "build_stock_name_repository",
    "build_metadata_source",
    "build_ranking_service",
    "build_breadth_service",
    "build_anomaly_service",
    "refresh_views",
    "build_storage_repository",
    "build_tdx_data_source",
    "build_tdx_server_list",
    "build_scan_market_use_case",
    "build_generate_macro_report_use_case",
    "build_secret_provider",
    "build_kimi_agent_model",
    "build_default_text_llm_client",
    "build_file_upload_service",
    "build_page_extraction_service",
    "build_rag_service",
    "build_claim_repository",
    "build_financial_statement_repository",
    "build_company_announcement_repository",
    "build_consensus_estimate_repository",
    "build_industry_classification_source",
    "build_risk_factor_source",
    "build_tool_application_service",
    "build_python_analysis_executor",
    "build_portfolio_service",
    "build_risk_service",
    "build_scenario_service",
    "build_manage_notes_use_case",
    "build_query_ticker_use_case",
    "build_generate_market_overview_use_case",
    "build_generate_anomaly_report_use_case",
    "build_catalog_use_case",
    "build_populate_stock_names_use_case",
    "build_industry_report_use_case",
    "build_generate_industry_report_use_case",
)

_RUNTIME_BACKED = (
    "build_agent_repositories",
    "build_agent_runtime_kernel",
    "build_runtime_outbox_repository",
    "build_event_subscriber",
    "build_model_router",
    "build_agent_backends",
    "build_research_agent_runtime",
    "build_persisted_research_agent_runtime",
    "build_macro_strategist_agent_use_case",
    "build_industry_analyzer_agent_use_case",
    "build_agent_document_repository",
    "build_agent_evidence_repository",
    "build_agent_run_queue",
    "build_agent_idempotency_store",
    "build_agent_unit_of_work",
    "build_create_session_use_case",
    "build_resume_session_use_case",
    "build_list_sessions_use_case",
    "build_append_turn_use_case",
    "build_default_tool_registry",
    "build_execute_run_use_case",
    "build_resume_run_use_case",
    "build_get_run_snapshot_use_case",
    "build_run_summary_use_case",
    "build_capability_registry_use_case",
)

_WORKSPACE_BACKED = (
    "build_portfolio_repository",
    "build_platform_repository",
    "build_enterprise_governance_repository",
    "build_research_case_service",
    "build_workflow_service",
)

_COMPOSITION_ALLOWLIST = (*_GATEWAY_BACKED, *_RUNTIME_BACKED, *_WORKSPACE_BACKED)


def test_composition_module_has_exactly_allowlisted_public_callables() -> None:
    actual = {
        name
        for name, value in vars(composition).items()
        if not name.startswith("_") and callable(value)
    }

    assert actual == set(_COMPOSITION_ALLOWLIST)


def test_composition_allowlist_has_no_duplicates() -> None:
    assert len(_GATEWAY_BACKED) == 43
    assert len(_RUNTIME_BACKED) == 25
    assert len(_WORKSPACE_BACKED) == 5
    assert len(_COMPOSITION_ALLOWLIST) == len(set(_COMPOSITION_ALLOWLIST)) == 73


def test_composition_allowlist_is_documented() -> None:
    registry = COMPATIBILITY_REGISTRY.read_text(encoding="utf-8")

    missing = [name for name in _COMPOSITION_ALLOWLIST if name not in registry]

    assert missing == []


def test_composition_module_does_not_import_infrastructure_adapters_directly() -> None:
    tree = ast.parse(COMPOSITION_PATH.read_text(encoding="utf-8"), filename=str(COMPOSITION_PATH))
    illegal = [
        name
        for name in _import_targets(tree)
        if name == "doge.infrastructure" or name.startswith("doge.infrastructure.")
    ]

    assert illegal == []


def _import_targets(tree: ast.AST) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports
