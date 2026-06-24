"""Canonical composition root for the application layer.

This module is the **single sanctioned site** where ports are wired to their
concrete infrastructure adapters. It builds both the low-level service factories
(previously in ``doge.core.services.composition``) and the new application-layer
use-case factories.

Rules enforced by layer-gate tests:

- ``doge.application.use_cases`` and ``doge.application.contracts`` import NO
  infrastructure.
- ``doge.core.services`` imports NO infrastructure (directly).
- ``doge.interfaces.*`` import NO infrastructure except through this module.
"""

from __future__ import annotations

import warnings
from typing import Optional

# ── Core ports ──
from doge.core.ports.file_scanner import ITdxFileScanner
from doge.core.ports.market_view import IMarketViewRepository
from doge.core.ports.metadata import ITickerMetadataSource
from doge.core.ports.secrets import ISecretProvider
from doge.core.ports.repository import (
    IReportRepository,
    ISchemaBrowser,
    IStockRepository,
    INoteRepository,
    IStockNameRepository,
)

# ── Core services ──
from doge.core.services.anomaly_service import AnomalyService
from doge.core.services.breadth_service import BreadthService
from doge.core.services.ranking_service import RankingService
from doge.core.services.stock_service import StockService
from doge.core.services.view_service import ViewService

# ── Infrastructure adapters (this is the only application module allowed to import them) ──
from doge.infrastructure.database.market_view_repository import DuckDBMarketViewRepository
from doge.infrastructure.database.repositories import (
    DuckDBStockRepository,
    SQLiteReportRepository,
    SQLiteSchemaBrowser,
    SQLiteNoteRepository,
    SQLiteStockNameRepository,
)
from doge.infrastructure.database.agent_repositories import (
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteDocumentRepository,
    SQLiteEventRepository,
    SQLiteIdempotencyStore,
    SQLiteRunQueue,
    SQLiteRunRepository,
    SQLiteSessionRepository,
)
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository
from doge.infrastructure.database.embedding_cache import SQLiteEmbeddingCache
from doge.infrastructure.database.enterprise_governance import SQLiteEnterpriseGovernanceRepository
from doge.infrastructure.database.claim_repository import SQLiteClaimRepository
from doge.infrastructure.database.portfolio_repository import SQLitePortfolioRepository, demo_portfolio
from doge.infrastructure.database.platform_repository import SQLitePlatformRepository
from doge.infrastructure.database.sqlite_uow import SQLiteAgentUnitOfWork
from doge.infrastructure.database.sqlite_runtime_transaction import SQLiteOutboxRepository, SQLiteRuntimeTransactionFactory
from doge.infrastructure.database.event_subscriber import SQLiteEventSubscriber
from doge.infrastructure.database.sqlite_storage import SQLiteStorageRepository
from doge.infrastructure.data_source.tdx_file_scanner import TDXFileScanner
from doge.infrastructure.data_source.tdx_server_list import ConfigTDXServerList
from doge.infrastructure.data_source.yfinance_metadata import YFinanceMetadataSource
from doge.infrastructure.agent.inmemory_runtime import InMemoryResearchAgentRuntime
from doge.infrastructure.agent.backends import KimiAgentSdkBackend
from doge.infrastructure.agent.persisted_runtime import PersistedResearchAgentRuntime
from doge.infrastructure.agent.scripted_model import ScriptedAgentModel
from doge.infrastructure.documents.local_parser import LocalDocumentParser
from doge.infrastructure.finance.local_connectors import (
    LocalNoteAnnouncementRepository,
    StaticIndustryClassificationSource,
    StaticRiskFactorSource,
    StockOverviewFinancialStatementRepository,
    UnavailableConsensusEstimateRepository,
)
from doge.infrastructure.llm.deepseek_client import DeepSeekClient
from doge.infrastructure.llm.kimi_client import KimiAgentModel
from doge.infrastructure.llm.kimi_text_client import KimiTextClient
from doge.infrastructure.llm.kimi_files_client import KimiFilesClient
from doge.infrastructure.llm.embedding_client import HashingEmbeddingProvider
from doge.infrastructure.secrets import EnvSecretProvider, ProcessSecretProvider
from doge.infrastructure.vector.sqlite_store import SQLiteVectorStore

# ── Application use cases ──
from doge.application.use_cases.scan_market import ScanMarketUseCase
from doge.application.use_cases.generate_macro_report import GenerateMacroReportUseCase
from doge.application.use_cases.manage_notes import ManageNotesUseCase
from doge.application.use_cases.query_ticker import QueryTickerUseCase
from doge.application.use_cases.generate_market_overview import GenerateMarketOverviewUseCase
from doge.application.use_cases.generate_anomaly_report import GenerateAnomalyReportUseCase
from doge.application.use_cases.generate_catalog import GenerateCatalogUseCase
from doge.application.use_cases.populate_stock_names import PopulateStockNamesUseCase
from doge.application.use_cases.generate_industry_report import GenerateIndustryReportUseCase
from doge.application.use_cases.industry_analyzer import IndustryAnalyzerAgentUseCase
from doge.application.use_cases.macro_strategist import MacroStrategistAgentUseCase
from doge.application.use_cases.run_use_cases import ExecuteRun, ResumeRun
from doge.application.use_cases.run_summary import BuildRunSummary
from doge.application.use_cases.capability_registry import BuildCapabilityRegistry
from doge.application.capabilities.registry import (
    ApiCapabilityProvider,
    FeatureCapabilityProvider,
    MaturityCapabilityProvider,
    ModelProviderCapabilityProvider,
    ToolRegistryCapabilityProvider,
)
from doge.application.use_cases.session_use_cases import AppendTurn, CreateSession, ListSessions, ResumeSession
from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_router import ModelRouter
from doge.application.agent.tool_service import ToolApplicationService
from doge.application.agent.tools import build_default_tool_registry as _build_tool_registry
from doge.application.capabilities.executors import DisabledCodeExecutor, SubprocessCodeExecutor
from doge.application.services.file_upload_service import FileUploadService
from doge.application.services.page_extraction_service import PageExtractionService
from doge.application.services.rag_service import RAGService
from doge.application.services.portfolio_service import PortfolioService, RiskService, ScenarioService
from doge.application.services.citation_service import CitationService
from doge.application.services.claim_validation_service import ClaimValidationService
from doge.config import get_settings
from doge.platform.workspace.application import ResearchCaseService, WorkflowService


# ── Low-level service factories (migrated from doge.core.services.composition) ──

def build_view_repository(read_only: bool = True) -> IMarketViewRepository:
    """Construct the default read-only DuckDB market-view repository."""
    return _gateway_container().build_view_repository(read_only=read_only)


def build_view_service(
    repo: IMarketViewRepository | None = None,
) -> ViewService:
    """Build a :class:`ViewService` with an injected (or default) repository."""
    return _gateway_container().build_view_service(repo)


def build_stock_repository(read_only: bool = True) -> IStockRepository:
    """Construct the default read-only DuckDB stock repository."""
    return _gateway_container().build_stock_repository()


def build_stock_service(
    repo: IStockRepository | None = None,
) -> StockService:
    """Build a :class:`StockService` with an injected (or default) repository."""
    return _gateway_container().build_stock_service(repo)


def build_report_repository() -> IReportRepository:
    """Construct the default SQLite-backed report repository."""
    return _gateway_container().build_report_repository()


def build_schema_browser() -> ISchemaBrowser:
    """Construct the default SQLite-backed schema browser."""
    return _gateway_container().build_schema_browser()


def build_note_repository() -> INoteRepository:
    """Construct the default SQLite-backed note repository."""
    return _gateway_container().build_note_repository()


def build_stock_name_repository() -> IStockNameRepository:
    """Construct the default SQLite-backed stock-name repository."""
    return _gateway_container().build_stock_name_repository()


def build_metadata_source(
    max_retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
) -> ITickerMetadataSource:
    """Construct the default yfinance-backed ticker metadata source."""
    return _gateway_container().build_metadata_source(
        max_retries=max_retries,
        retry_delay=retry_delay,
    )


def build_ranking_service(
    repo: IMarketViewRepository | None = None,
) -> RankingService:
    """Build a :class:`RankingService` with an injected (or default) repository."""
    return _gateway_container().build_ranking_service(repo)


def build_breadth_service(
    repo: IMarketViewRepository | None = None,
) -> BreadthService:
    """Build a :class:`BreadthService` with an injected (or default) repository."""
    return _gateway_container().build_breadth_service(repo)


def build_anomaly_service(
    repo: IMarketViewRepository | None = None,
) -> AnomalyService:
    """Build an :class:`AnomalyService` with an injected (or default) repository."""
    return _gateway_container().build_anomaly_service(repo)


def refresh_views() -> None:
    """Materialize the DuckDB analytical views after a market-data scan."""
    _gateway_container().refresh_views()


def build_storage_repository() -> SQLiteStorageRepository:
    """Construct the default SQLite single-logical-writer storage repository."""
    return _gateway_container().build_storage_repository()


def build_tdx_data_source(preferred_server: str | None = None):
    """Construct the default TDX market data source."""
    return _gateway_container().build_tdx_data_source(preferred_server=preferred_server)


def build_tdx_server_list():
    """Construct the configured TDX server-list adapter."""
    return _gateway_container().build_tdx_server_list()


# ── Application use-case factories ──


def build_scan_market_use_case(
    stock_repo: IStockRepository | None = None,
    data_source: IMarketDataSource | None = None,
    file_scanner: ITdxFileScanner | None = None,
    refresh_views_callable=None,
) -> ScanMarketUseCase:
    """Build a :class:`ScanMarketUseCase` with default adapters.

    Args:
        stock_repo: Defaults to the SQLite single-logical-writer storage
            repository (required for ``ensure_schema`` / ``save_prices``).
        data_source: Defaults to ``TDXDataSource`` (lazy import so opentdx is
            not required at import time).
        file_scanner: Defaults to ``TDXFileScanner`` for local .day scans.
        refresh_views_callable: Defaults to :func:`refresh_views`.
    """
    return _gateway_container().build_scan_market_use_case(
        stock_repo=stock_repo,
        data_source=data_source,
        file_scanner=file_scanner,
        refresh_views_callable=refresh_views_callable,
    )


def build_generate_macro_report_use_case(
    view_repo: IMarketViewRepository | None = None,
    llm_client=None,
    report_repo: IReportRepository | None = None,
) -> GenerateMacroReportUseCase:
    """Build a :class:`GenerateMacroReportUseCase` with default adapters."""
    return _gateway_container().build_generate_macro_report_use_case(
        view_repo=view_repo,
        llm_client=llm_client,
        report_repo=report_repo,
    )


def build_secret_provider() -> ISecretProvider:
    """Build the configured secret provider."""
    return _gateway_container().build_secret_provider()


def build_kimi_agent_model(secret_provider=None) -> KimiAgentModel:
    """Build the default Kimi agent-capable model adapter."""
    return _gateway_container().build_kimi_agent_model(secret_provider)


def build_default_text_llm_client():
    """Build the default text-generation client for macro/industry use cases."""
    return _gateway_container().build_default_text_llm_client()


def build_agent_repositories(db_path=None):
    """Build all SQLite-backed agent repositories for a shared database path."""
    return _runtime_container(db_path).build_agent_repositories()


def build_agent_runtime_kernel(model=None, tool_registry=None, event_publisher=None, db_path=None) -> RuntimeKernel:
    """Build the persisted agent runtime kernel (delegates to RuntimeContainer)."""
    return _runtime_container(db_path).build_agent_runtime_kernel(
        model=model,
        tool_registry=tool_registry,
        event_publisher=event_publisher,
    )


def build_runtime_outbox_repository(db_path=None):
    """Build the persisted runtime event outbox repository."""
    return _runtime_container(db_path).build_runtime_outbox_repository()


def build_event_subscriber(db_path=None, *, poll_interval_seconds: float = 0.1):
    """Build the persisted runtime event subscriber."""
    return _runtime_container(db_path).build_event_subscriber(
        poll_interval_seconds=poll_interval_seconds,
    )


def build_model_router(document_repository=None) -> ModelRouter:
    """Build the application model router (delegates to RuntimeContainer)."""
    return _runtime_container().build_model_router(document_repository=document_repository)


def build_agent_backends(secret_provider=None):
    """Build optional agent runtime backends keyed by router backend id."""
    return _runtime_container().build_agent_backends(secret_provider=secret_provider)


def build_research_agent_runtime(model=None, tool_registry=None) -> InMemoryResearchAgentRuntime:
    """Build the in-memory research-agent runtime for the interview demo."""
    return _runtime_container().build_research_agent_runtime(model=model, tool_registry=tool_registry)


def build_persisted_research_agent_runtime(model=None, tool_registry=None, event_publisher=None, db_path=None):
    """Build the repository-backed runtime for CLI, daemon and SDK paths."""
    return _runtime_container(db_path).build_persisted_research_agent_runtime(
        model=model,
        tool_registry=tool_registry,
        event_publisher=event_publisher,
    )


def build_macro_strategist_agent_use_case(runtime=None) -> MacroStrategistAgentUseCase:
    """Build the RuntimeKernel-backed macro strategist wrapper."""
    return _runtime_container().build_macro_strategist_agent_use_case(runtime)


def build_industry_analyzer_agent_use_case(runtime=None) -> IndustryAnalyzerAgentUseCase:
    """Build the RuntimeKernel-backed industry analyzer wrapper."""
    return _runtime_container().build_industry_analyzer_agent_use_case(runtime)


def build_agent_document_repository(db_path=None):
    """Build the default persisted document repository."""
    return _runtime_container(db_path).build_agent_document_repository()


def build_agent_evidence_repository(db_path=None):
    """Build the default persisted page/chunk/evidence repository."""
    return _runtime_container(db_path).build_agent_evidence_repository()


def build_file_upload_service(db_path=None, kimi_files_client=None):
    """Build the default file upload service for API and CLI attach paths."""
    return _gateway_container(db_path).build_file_upload_service(
        kimi_files_client=kimi_files_client,
    )


def build_page_extraction_service(db_path=None):
    """Build the local page/chunk extraction service."""
    return PageExtractionService(
        evidence_repository=build_agent_evidence_repository(db_path),
        parser=LocalDocumentParser(),
    )


def build_rag_service(db_path=None):
    """Build the local-first RAG service over extracted evidence chunks."""
    return _gateway_container(db_path).build_rag_service()


def build_claim_repository(db_path=None):
    """Build the claim/citation repository."""
    return _gateway_container(db_path).build_claim_repository()


def build_portfolio_repository(db_path=None):
    """Build the portfolio repository and ensure the demo portfolio exists."""
    return _workspace_container(db_path).build_portfolio_repository()


def build_platform_repository(db_path=None):
    """Build the platform workspace/project/case/template repository."""
    return SQLitePlatformRepository(db_path)


def build_enterprise_governance_repository(db_path=None):
    """Build the enterprise ACL and audit repository."""
    return SQLiteEnterpriseGovernanceRepository(db_path)


def build_research_case_service(
    runtime=None,
    repo=None,
    governance=None,
    db_path=None,
    *,
    capability_registry_enabled: bool = True,
) -> ResearchCaseService:
    """Build the case-centered platform service used by API, CLI, and MCP."""
    if repo is None:
        repo = build_platform_repository(db_path)
    if governance is None:
        governance = build_enterprise_governance_repository(db_path)
    if runtime is None:
        runtime = build_persisted_research_agent_runtime(db_path=db_path)
    return ResearchCaseService(
        repo,
        governance,
        runtime,
        document_repository=build_agent_document_repository(db_path),
        portfolio_repository=build_portfolio_repository(db_path),
        capability_registry=build_capability_registry_use_case(),
        capability_registry_enabled=capability_registry_enabled,
    )


def build_workflow_service(repo=None, governance=None, db_path=None) -> WorkflowService:
    """Build the workflow-template service used by API, CLI, and MCP."""
    if repo is None:
        repo = build_platform_repository(db_path)
    if governance is None:
        governance = SQLiteEnterpriseGovernanceRepository(db_path)
    return WorkflowService(repo, governance)


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


def build_tool_application_service(db_path=None) -> ToolApplicationService:
    """Build the fully injected application service used by agent tools."""
    return _gateway_container(db_path).build_tool_application_service()


def build_python_analysis_executor(settings=None):
    """Build the explicitly configured Python analysis executor."""
    return _gateway_container().build_python_analysis_executor(settings)


def build_default_tool_registry(entitlement_checker=None, context=None, db_path=None):
    """Build the default tool registry with application dependencies injected."""
    return _runtime_container(db_path).build_default_tool_registry(
        entitlement_checker=entitlement_checker,
        context=context,
    )


def build_portfolio_service(db_path=None):
    return _gateway_container(db_path).build_portfolio_service()


def build_risk_service(db_path=None):
    return _gateway_container(db_path).build_risk_service()


def build_scenario_service(db_path=None):
    return _gateway_container(db_path).build_scenario_service()


def build_agent_run_queue(db_path=None):
    """Build the durable run queue adapter."""
    return _runtime_container(db_path).build_agent_run_queue()


def build_agent_idempotency_store(db_path=None):
    """Build the durable idempotency-key adapter."""
    return _runtime_container(db_path).build_agent_idempotency_store()


def build_agent_unit_of_work(db_path=None, event_publisher=None):
    """Build the transactional unit of work for agent run enqueue."""
    return _runtime_container(db_path).build_agent_unit_of_work(event_publisher=event_publisher)


def build_create_session_use_case(db_path=None) -> CreateSession:
    return CreateSession(SQLiteSessionRepository(db_path))


def build_resume_session_use_case(db_path=None) -> ResumeSession:
    return ResumeSession(SQLiteSessionRepository(db_path))


def build_list_sessions_use_case(db_path=None) -> ListSessions:
    return ListSessions(SQLiteSessionRepository(db_path))


def build_append_turn_use_case(db_path=None) -> AppendTurn:
    return AppendTurn(SQLiteSessionRepository(db_path))


def build_execute_run_use_case(model=None, tool_registry=None, db_path=None) -> ExecuteRun:
    return _runtime_container(db_path).build_execute_run_use_case(model=model, tool_registry=tool_registry)


def build_resume_run_use_case(model=None, tool_registry=None, db_path=None) -> ResumeRun:
    return _runtime_container(db_path).build_resume_run_use_case(model=model, tool_registry=tool_registry)


def build_run_summary_use_case(runtime=None, evidence_repository=None, db_path=None) -> BuildRunSummary:
    """Build the structured run summary/citation/eval use case."""
    return _runtime_container(db_path).build_run_summary_use_case(
        runtime=runtime,
        evidence_repository=evidence_repository,
    )


def build_capability_registry_use_case() -> BuildCapabilityRegistry:
    """Build the redacted capability discovery use case."""
    return _runtime_container().build_capability_registry_use_case()


def build_manage_notes_use_case(
    note_repo: INoteRepository | None = None,
) -> ManageNotesUseCase:
    """Build a :class:`ManageNotesUseCase` with the default note repository."""
    return _gateway_container().build_manage_notes_use_case(note_repo)


def build_query_ticker_use_case(
    stock_repo: IStockRepository | None = None,
    note_repo: INoteRepository | None = None,
    metadata_source: ITickerMetadataSource | None = None,
) -> QueryTickerUseCase:
    """Build a :class:`QueryTickerUseCase` with default adapters."""
    return QueryTickerUseCase(
        stock_repo if stock_repo is not None else build_stock_repository(),
        note_repo if note_repo is not None else build_note_repository(),
        metadata_source if metadata_source is not None else build_metadata_source(),
    )


def build_generate_market_overview_use_case(
    view_repo: IMarketViewRepository | None = None,
    breadth_service=None,
    ranking_service=None,
    anomaly_service=None,
) -> GenerateMarketOverviewUseCase:
    """Build a :class:`GenerateMarketOverviewUseCase` with default adapters."""
    return GenerateMarketOverviewUseCase(
        view_repo if view_repo is not None else build_view_repository(),
        breadth_service if breadth_service is not None else build_breadth_service(),
        ranking_service if ranking_service is not None else build_ranking_service(),
        anomaly_service if anomaly_service is not None else build_anomaly_service(),
    )


def build_generate_anomaly_report_use_case(
    view_repo: IMarketViewRepository | None = None,
    anomaly_service=None,
) -> GenerateAnomalyReportUseCase:
    """Build a :class:`GenerateAnomalyReportUseCase` with the default service."""
    return GenerateAnomalyReportUseCase(
        view_repo if view_repo is not None else build_view_repository(),
        anomaly_service if anomaly_service is not None else build_anomaly_service(),
    )


def build_catalog_use_case(
    schema_browser: ISchemaBrowser | None = None,
    view_service=None,
) -> GenerateCatalogUseCase:
    """Build a :class:`GenerateCatalogUseCase` with default adapters."""
    return GenerateCatalogUseCase(
        schema_browser if schema_browser is not None else build_schema_browser(),
        view_service if view_service is not None else build_view_service(),
    )


def build_populate_stock_names_use_case(
    stock_repo: IStockRepository | None = None,
    name_repo: IStockNameRepository | None = None,
    metadata_source: ITickerMetadataSource | None = None,
) -> PopulateStockNamesUseCase:
    """Build a :class:`PopulateStockNamesUseCase` with default adapters."""
    return PopulateStockNamesUseCase(
        stock_repo if stock_repo is not None else build_stock_repository(),
        name_repo if name_repo is not None else build_stock_name_repository(),
        metadata_source if metadata_source is not None else build_metadata_source(),
    )


def build_industry_report_use_case(
    ranking_service=None,
    llm_client=None,
    stock_service=None,
    rag_service=None,
    report_repository=None,
    claim_repository=None,
) -> GenerateIndustryReportUseCase:
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
) -> GenerateIndustryReportUseCase:
    """Build a :class:`GenerateIndustryReportUseCase` with default adapters."""
    return _gateway_container().build_generate_industry_report_use_case(
        ranking_service=ranking_service,
        llm_client=llm_client,
        stock_service=stock_service,
        rag_service=rag_service,
        report_repository=report_repository,
        claim_repository=claim_repository,
    )


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
