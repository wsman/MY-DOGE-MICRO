"""Application package root.

Factory exports remain available for compatibility, but they are resolved
through ``doge.application.composition`` only when explicitly requested.
"""

from __future__ import annotations

from doge.application import contracts, use_cases

_FACTORY_EXPORTS = {
    "build_agent_document_repository",
    "build_agent_evidence_repository",
    "build_agent_idempotency_store",
    "build_agent_repositories",
    "build_agent_run_queue",
    "build_agent_runtime_kernel",
    "build_agent_unit_of_work",
    "build_anomaly_service",
    "build_append_turn_use_case",
    "build_breadth_service",
    "build_capability_registry_use_case",
    "build_catalog_use_case",
    "build_claim_repository",
    "build_create_session_use_case",
    "build_default_tool_registry",
    "build_enterprise_governance_repository",
    "build_event_subscriber",
    "build_execute_run_use_case",
    "build_file_upload_service",
    "build_generate_anomaly_report_use_case",
    "build_generate_industry_report_use_case",
    "build_generate_macro_report_use_case",
    "build_generate_market_overview_use_case",
    "build_get_run_snapshot_use_case",
    "build_industry_report_use_case",
    "build_kimi_agent_model",
    "build_list_sessions_use_case",
    "build_manage_notes_use_case",
    "build_metadata_source",
    "build_note_repository",
    "build_page_extraction_service",
    "build_persisted_research_agent_runtime",
    "build_platform_repository",
    "build_populate_stock_names_use_case",
    "build_portfolio_repository",
    "build_portfolio_service",
    "build_query_ticker_use_case",
    "build_rag_service",
    "build_ranking_service",
    "build_report_repository",
    "build_research_agent_runtime",
    "build_research_case_service",
    "build_resume_run_use_case",
    "build_resume_session_use_case",
    "build_risk_service",
    "build_run_summary_use_case",
    "build_runtime_outbox_repository",
    "build_scan_market_use_case",
    "build_scenario_service",
    "build_schema_browser",
    "build_secret_provider",
    "build_stock_name_repository",
    "build_stock_repository",
    "build_stock_service",
    "build_tdx_data_source",
    "build_tdx_server_list",
    "build_view_repository",
    "build_view_service",
    "build_workflow_service",
    "refresh_views",
}

__all__ = ["contracts", "use_cases", *_FACTORY_EXPORTS]


def __getattr__(name: str):
    if name in _FACTORY_EXPORTS:
        from doge.application import composition

        return getattr(composition, name)
    raise AttributeError(f"module 'doge.application' has no attribute {name!r}")
