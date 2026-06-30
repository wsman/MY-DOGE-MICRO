"""Compatibility shim for the application composition root.

Historically this module was the single sanctioned site where ports were wired
to concrete infrastructure adapters. That wiring has moved into the bootstrap
containers (:class:`~doge.bootstrap.runtime.RuntimeContainer`,
:class:`~doge.bootstrap.gateway.GatewayContainer`,
:class:`~doge.bootstrap.workspace.WorkspaceContainer`), which are the real
composition roots. Every public factory here is now a thin delegate to the
appropriate bootstrap container so legacy callers keep working.

This module intentionally imports **no** infrastructure adapters directly; all
adapter construction lives in the bootstrap layer.
"""

from __future__ import annotations

import warnings


# ── Gateway-backed factories ──


def build_view_repository(read_only=True):
    """Construct the default read-only DuckDB market-view repository."""
    return _gateway_container().build_view_repository(read_only=read_only)


def build_view_service(repo=None):
    """Build a ``ViewService`` with an injected (or default) repository."""
    return _gateway_container().build_view_service(repo)


def build_stock_repository(read_only=True):
    """Construct the default read-only DuckDB stock repository."""
    return _gateway_container().build_stock_repository()


def build_stock_service(repo=None):
    """Build a ``StockService`` with an injected (or default) repository."""
    return _gateway_container().build_stock_service(repo)


def build_report_repository():
    """Construct the default SQLite-backed report repository."""
    return _gateway_container().build_report_repository()


def build_schema_browser():
    """Construct the default SQLite-backed schema browser."""
    return _gateway_container().build_schema_browser()


def build_note_repository():
    """Construct the default SQLite-backed note repository."""
    return _gateway_container().build_note_repository()


def build_stock_name_repository():
    """Construct the default SQLite-backed stock-name repository."""
    return _gateway_container().build_stock_name_repository()


def build_metadata_source(max_retries=None, retry_delay=None):
    """Construct the default yfinance-backed ticker metadata source."""
    return _gateway_container().build_metadata_source(
        max_retries=max_retries,
        retry_delay=retry_delay,
    )


def build_ranking_service(repo=None):
    """Build a ``RankingService`` with an injected (or default) repository."""
    return _gateway_container().build_ranking_service(repo)


def build_breadth_service(repo=None):
    """Build a ``BreadthService`` with an injected (or default) repository."""
    return _gateway_container().build_breadth_service(repo)


def build_anomaly_service(repo=None):
    """Build an ``AnomalyService`` with an injected (or default) repository."""
    return _gateway_container().build_anomaly_service(repo)


def refresh_views():
    """Materialize the DuckDB analytical views after a market-data scan."""
    _gateway_container().refresh_views()


def build_storage_repository():
    """Construct the default SQLite single-logical-writer storage repository."""
    return _gateway_container().build_storage_repository()


def build_tdx_data_source(preferred_server=None):
    """Construct the default TDX market data source."""
    return _gateway_container().build_tdx_data_source(preferred_server=preferred_server)


def build_tdx_server_list():
    """Construct the configured TDX server-list adapter."""
    return _gateway_container().build_tdx_server_list()


def build_scan_market_use_case(stock_repo=None, data_source=None, file_scanner=None, refresh_views_callable=None):
    """Build a ``ScanMarketUseCase`` with default adapters."""
    return _gateway_container().build_scan_market_use_case(
        stock_repo=stock_repo,
        data_source=data_source,
        file_scanner=file_scanner,
        refresh_views_callable=refresh_views_callable,
    )


def build_generate_macro_report_use_case(view_repo=None, llm_client=None, report_repo=None):
    """Build a ``GenerateMacroReportUseCase`` with default adapters."""
    return _gateway_container().build_generate_macro_report_use_case(
        view_repo=view_repo,
        llm_client=llm_client,
        report_repo=report_repo,
    )


def build_secret_provider():
    """Build the configured secret provider."""
    return _gateway_container().build_secret_provider()


def build_kimi_agent_model(secret_provider=None):
    """Build the default Kimi agent-capable model adapter."""
    return _gateway_container().build_kimi_agent_model(secret_provider)


def build_default_text_llm_client():
    """Build the default text-generation client for macro/industry use cases."""
    return _gateway_container().build_default_text_llm_client()


def build_file_upload_service(db_path=None, kimi_files_client=None):
    """Build the default file upload service for API and CLI attach paths."""
    return _gateway_container(db_path).build_file_upload_service(
        kimi_files_client=kimi_files_client,
    )


def build_page_extraction_service(db_path=None):
    """Build the local page/chunk extraction service."""
    return _gateway_container(db_path).build_page_extraction_service()


def build_rag_service(db_path=None):
    """Build the local-first RAG service over extracted evidence chunks."""
    return _gateway_container(db_path).build_rag_service()


def build_claim_repository(db_path=None):
    """Build the claim/citation repository."""
    return _gateway_container(db_path).build_claim_repository()


def build_financial_statement_repository():
    """Build the configured financial statement connector."""
    return _gateway_container().build_financial_statement_repository()


def build_company_announcement_repository():
    """Build the configured company announcement connector."""
    return _gateway_container().build_company_announcement_repository()


def build_consensus_estimate_repository():
    """Build the configured consensus estimate connector."""
    return _gateway_container().build_consensus_estimate_repository()


def build_industry_classification_source():
    """Build the configured industry classification source."""
    return _gateway_container().build_industry_classification_source()


def build_risk_factor_source():
    """Build the configured risk factor source."""
    return _gateway_container().build_risk_factor_source()


def build_tool_application_service(db_path=None):
    """Build the fully injected application service used by agent tools."""
    return _gateway_container(db_path).build_tool_application_service()


def build_python_analysis_executor(settings=None):
    """Build the explicitly configured Python analysis executor."""
    return _gateway_container().build_python_analysis_executor(settings)


def build_portfolio_service(db_path=None):
    return _gateway_container(db_path).build_portfolio_service()


def build_risk_service(db_path=None):
    return _gateway_container(db_path).build_risk_service()


def build_scenario_service(db_path=None):
    return _gateway_container(db_path).build_scenario_service()


def build_manage_notes_use_case(note_repo=None):
    """Build a ``ManageNotesUseCase`` with the default note repository."""
    return _gateway_container().build_manage_notes_use_case(note_repo)


def build_query_ticker_use_case(stock_repo=None, note_repo=None, metadata_source=None):
    """Build a ``QueryTickerUseCase`` with default adapters."""
    return _gateway_container().build_query_ticker_use_case(
        stock_repo=stock_repo,
        note_repo=note_repo,
        metadata_source=metadata_source,
    )


def build_generate_market_overview_use_case(
    view_repo=None,
    breadth_service=None,
    ranking_service=None,
    anomaly_service=None,
):
    """Build a ``GenerateMarketOverviewUseCase`` with default adapters."""
    return _gateway_container().build_generate_market_overview_use_case(
        view_repo=view_repo,
        breadth_service=breadth_service,
        ranking_service=ranking_service,
        anomaly_service=anomaly_service,
    )


def build_generate_anomaly_report_use_case(view_repo=None, anomaly_service=None):
    """Build a ``GenerateAnomalyReportUseCase`` with the default service."""
    return _gateway_container().build_generate_anomaly_report_use_case(
        view_repo=view_repo,
        anomaly_service=anomaly_service,
    )


def build_catalog_use_case(schema_browser=None, view_service=None):
    """Build a ``GenerateCatalogUseCase`` with default adapters."""
    return _gateway_container().build_catalog_use_case(
        schema_browser=schema_browser,
        view_service=view_service,
    )


def build_populate_stock_names_use_case(stock_repo=None, name_repo=None, metadata_source=None):
    """Build a ``PopulateStockNamesUseCase`` with default adapters."""
    return _gateway_container().build_populate_stock_names_use_case(
        stock_repo=stock_repo,
        name_repo=name_repo,
        metadata_source=metadata_source,
    )


def build_industry_report_use_case(
    ranking_service=None,
    llm_client=None,
    stock_service=None,
    rag_service=None,
    report_repository=None,
    claim_repository=None,
):
    """Alias for :func:`build_generate_industry_report_use_case`."""
    return build_generate_industry_report_use_case(
        ranking_service,
        llm_client,
        stock_service=stock_service,
        rag_service=rag_service,
        report_repository=report_repository,
        claim_repository=claim_repository,
    )


def build_generate_industry_report_use_case(
    ranking_service=None,
    llm_client=None,
    stock_service=None,
    rag_service=None,
    report_repository=None,
    claim_repository=None,
):
    """Build a ``GenerateIndustryReportUseCase`` with default adapters."""
    return _gateway_container().build_generate_industry_report_use_case(
        ranking_service=ranking_service,
        llm_client=llm_client,
        stock_service=stock_service,
        rag_service=rag_service,
        report_repository=report_repository,
        claim_repository=claim_repository,
    )


# ── Runtime-backed factories ──


def build_agent_repositories(db_path=None):
    """Build all SQLite-backed agent repositories for a shared database path."""
    return _runtime_container(db_path).build_agent_repositories()


def build_agent_runtime_kernel(model=None, tool_registry=None, event_publisher=None, db_path=None):
    """Build the persisted agent runtime kernel."""
    return _runtime_container(db_path).build_agent_runtime_kernel(
        model=model,
        tool_registry=tool_registry,
        event_publisher=event_publisher,
    )


def build_runtime_outbox_repository(db_path=None):
    """Build the persisted runtime event outbox repository."""
    return _runtime_container(db_path).build_runtime_outbox_repository()


def build_event_subscriber(db_path=None, *, poll_interval_seconds=0.1):
    """Build the persisted runtime event subscriber."""
    return _runtime_container(db_path).build_event_subscriber(
        poll_interval_seconds=poll_interval_seconds,
    )


def build_model_router(document_repository=None):
    """Build the application model router."""
    return _runtime_container().build_model_router(document_repository=document_repository)


def build_agent_backends(secret_provider=None):
    """Build optional agent runtime backends keyed by router backend id."""
    return _runtime_container().build_agent_backends(secret_provider=secret_provider)


def build_research_agent_runtime(model=None, tool_registry=None):
    """Build the in-memory research-agent runtime for the interview demo."""
    return _runtime_container().build_research_agent_runtime(model=model, tool_registry=tool_registry)


def build_persisted_research_agent_runtime(model=None, tool_registry=None, event_publisher=None, db_path=None):
    """Build the repository-backed runtime for CLI, daemon and SDK paths."""
    return _runtime_container(db_path).build_persisted_research_agent_runtime(
        model=model,
        tool_registry=tool_registry,
        event_publisher=event_publisher,
    )


def build_macro_strategist_agent_use_case(runtime=None):
    """Build the RuntimeKernel-backed macro strategist wrapper."""
    return _runtime_container().build_macro_strategist_agent_use_case(runtime)


def build_industry_analyzer_agent_use_case(runtime=None):
    """Build the RuntimeKernel-backed industry analyzer wrapper."""
    return _runtime_container().build_industry_analyzer_agent_use_case(runtime)


def build_agent_document_repository(db_path=None):
    """Build the default persisted document repository."""
    return _runtime_container(db_path).build_agent_document_repository()


def build_agent_evidence_repository(db_path=None):
    """Build the default persisted page/chunk/evidence repository."""
    return _runtime_container(db_path).build_agent_evidence_repository()


def build_agent_run_queue(db_path=None):
    """Build the durable run queue adapter."""
    return _runtime_container(db_path).build_agent_run_queue()


def build_agent_idempotency_store(db_path=None):
    """Build the durable idempotency-key adapter."""
    return _runtime_container(db_path).build_agent_idempotency_store()


def build_agent_unit_of_work(db_path=None, event_publisher=None):
    """Build the transactional unit of work for agent run enqueue."""
    return _runtime_container(db_path).build_agent_unit_of_work(event_publisher=event_publisher)


def build_create_session_use_case(db_path=None):
    return _runtime_container(db_path).build_create_session_use_case()


def build_resume_session_use_case(db_path=None):
    return _runtime_container(db_path).build_resume_session_use_case()


def build_list_sessions_use_case(db_path=None):
    return _runtime_container(db_path).build_list_sessions_use_case()


def build_append_turn_use_case(db_path=None):
    return _runtime_container(db_path).build_append_turn_use_case()


def build_default_tool_registry(entitlement_checker=None, context=None, db_path=None):
    """Build the default tool registry with application dependencies injected."""
    return _runtime_container(db_path).build_default_tool_registry(
        entitlement_checker=entitlement_checker,
        context=context,
    )


def build_execute_run_use_case(model=None, tool_registry=None, db_path=None):
    return _runtime_container(db_path).build_execute_run_use_case(model=model, tool_registry=tool_registry)


def build_resume_run_use_case(model=None, tool_registry=None, db_path=None):
    return _runtime_container(db_path).build_resume_run_use_case(model=model, tool_registry=tool_registry)


def build_get_run_snapshot_use_case(model=None, tool_registry=None, db_path=None):
    return _runtime_container(db_path).build_get_run_snapshot_use_case(model=model, tool_registry=tool_registry)


def build_run_summary_use_case(runtime=None, evidence_repository=None, db_path=None):
    """Build the structured run summary/citation/eval use case."""
    return _runtime_container(db_path).build_run_summary_use_case(
        runtime=runtime,
        evidence_repository=evidence_repository,
    )


def build_capability_registry_use_case():
    """Build the redacted capability discovery use case."""
    return _runtime_container().build_capability_registry_use_case()


# ── Workspace-backed factories ──


def build_portfolio_repository(db_path=None):
    """Build the portfolio repository and ensure the demo portfolio exists."""
    return _workspace_container(db_path).build_portfolio_repository()


def build_platform_repository(db_path=None):
    """Build the platform workspace/project/case/template repository."""
    return _workspace_container(db_path).build_platform_repository()


def build_enterprise_governance_repository(db_path=None):
    """Build the enterprise ACL and audit repository."""
    return _workspace_container(db_path).build_enterprise_governance_repository()


def build_research_case_service(
    runtime=None,
    repo=None,
    governance=None,
    db_path=None,
    *,
    capability_registry_enabled=True,
):
    """Build the case-centered platform service used by API, CLI, and MCP."""
    return _workspace_container(db_path).build_research_case_service(
        runtime=runtime,
        repo=repo,
        governance=governance,
        capability_registry_enabled=capability_registry_enabled,
    )


def build_workflow_service(repo=None, governance=None, db_path=None):
    """Build the workflow-template service used by API, CLI, and MCP."""
    return _workspace_container(db_path).build_workflow_service(repo=repo, governance=governance)


# ── Bootstrap container collaborators ──


def _runtime_container(db_path=None):
    from doge.bootstrap.runtime import build_runtime_container

    return build_runtime_container(db_path)


def _gateway_container(db_path=None):
    from doge.bootstrap.gateway import build_gateway_container

    return build_gateway_container(db_path)


def _workspace_container(db_path=None):
    from doge.bootstrap.workspace import build_workspace_container

    return build_workspace_container(db_path)


def _warn_legacy_composition() -> None:
    """Deprecation helper — not part of public API."""
    warnings.warn(
        "doge.core.services.composition is deprecated; "
        "use doge.application.composition instead",
        DeprecationWarning,
        stacklevel=3,
    )
