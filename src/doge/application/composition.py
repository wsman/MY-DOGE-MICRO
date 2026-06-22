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
from doge.infrastructure.database.sqlite_uow import SQLiteAgentUnitOfWork
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
from doge.application.use_cases.session_use_cases import AppendTurn, CreateSession, ListSessions, ResumeSession
from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_router import ModelRouter
from doge.application.agent.tool_service import ToolApplicationService
from doge.application.agent.tools import build_default_tool_registry as _build_tool_registry
from doge.application.services.file_upload_service import FileUploadService
from doge.application.services.page_extraction_service import PageExtractionService
from doge.application.services.rag_service import RAGService
from doge.application.services.portfolio_service import PortfolioService, RiskService, ScenarioService
from doge.application.services.citation_service import CitationService
from doge.application.services.claim_validation_service import ClaimValidationService
from doge.config import get_settings


# ── Low-level service factories (migrated from doge.core.services.composition) ──

def build_view_repository(read_only: bool = True) -> IMarketViewRepository:
    """Construct the default read-only DuckDB market-view repository."""
    return DuckDBMarketViewRepository(read_only=read_only)


def build_view_service(
    repo: IMarketViewRepository | None = None,
) -> ViewService:
    """Build a :class:`ViewService` with an injected (or default) repository."""
    return ViewService(repo if repo is not None else build_view_repository())


def build_stock_repository(read_only: bool = True) -> IStockRepository:
    """Construct the default read-only DuckDB stock repository."""
    return DuckDBStockRepository()


def build_stock_service(
    repo: IStockRepository | None = None,
) -> StockService:
    """Build a :class:`StockService` with an injected (or default) repository."""
    return StockService(repo if repo is not None else build_stock_repository())


def build_report_repository() -> IReportRepository:
    """Construct the default SQLite-backed report repository."""
    return SQLiteReportRepository()


def build_schema_browser() -> ISchemaBrowser:
    """Construct the default SQLite-backed schema browser."""
    return SQLiteSchemaBrowser()


def build_note_repository() -> INoteRepository:
    """Construct the default SQLite-backed note repository."""
    return SQLiteNoteRepository()


def build_stock_name_repository() -> IStockNameRepository:
    """Construct the default SQLite-backed stock-name repository."""
    return SQLiteStockNameRepository()


def build_metadata_source(
    max_retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
) -> ITickerMetadataSource:
    """Construct the default yfinance-backed ticker metadata source."""
    return YFinanceMetadataSource(max_retries=max_retries, retry_delay=retry_delay)


def build_ranking_service(
    repo: IMarketViewRepository | None = None,
) -> RankingService:
    """Build a :class:`RankingService` with an injected (or default) repository."""
    return RankingService(repo if repo is not None else build_view_repository())


def build_breadth_service(
    repo: IMarketViewRepository | None = None,
) -> BreadthService:
    """Build a :class:`BreadthService` with an injected (or default) repository."""
    return BreadthService(repo if repo is not None else build_view_repository())


def build_anomaly_service(
    repo: IMarketViewRepository | None = None,
) -> AnomalyService:
    """Build an :class:`AnomalyService` with an injected (or default) repository."""
    return AnomalyService(repo if repo is not None else build_view_repository())


def refresh_views() -> None:
    """Materialize the DuckDB analytical views after a market-data scan."""
    from doge.infrastructure.database.duckdb import DuckDBConnection
    DuckDBConnection(read_only=False).refresh_views()


def build_storage_repository() -> SQLiteStorageRepository:
    """Construct the default SQLite single-logical-writer storage repository."""
    return SQLiteStorageRepository()


def build_tdx_data_source(preferred_server: str | None = None):
    """Construct the default TDX market data source."""
    from doge.infrastructure.data_source.tdx import TDXDataSource

    return TDXDataSource(preferred_server=preferred_server)


def build_tdx_server_list():
    """Construct the configured TDX server-list adapter."""
    return ConfigTDXServerList()


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
    if stock_repo is None:
        stock_repo = build_storage_repository()
    if data_source is None:
        # Lazy import so this module can be imported without opentdx installed.
        data_source = build_tdx_data_source()
    if file_scanner is None:
        file_scanner = TDXFileScanner()
    if refresh_views_callable is None:
        refresh_views_callable = refresh_views
    return ScanMarketUseCase(
        stock_repo,
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
    if view_repo is None:
        view_repo = build_view_repository()
    if llm_client is None:
        llm_client = build_default_text_llm_client()
    if report_repo is None:
        report_repo = build_report_repository()
    return GenerateMacroReportUseCase(view_repo, llm_client, report_repo)


def build_secret_provider() -> ISecretProvider:
    """Build the configured secret provider."""
    settings = get_settings()
    provider = settings.secrets.provider
    if provider == "env":
        return EnvSecretProvider()
    if provider == "process":
        return ProcessSecretProvider(
            command=settings.secrets.process_command,
            timeout_seconds=settings.secrets.process_timeout_seconds,
            allowed_names=frozenset(settings.secrets.allowed_names),
        )
    raise ValueError(f"Unsupported DOGE_SECRET_PROVIDER: {provider}")


def build_kimi_agent_model(secret_provider=None) -> KimiAgentModel:
    """Build the default Kimi agent-capable model adapter."""
    return KimiAgentModel(secret_provider=secret_provider or build_secret_provider())


def build_default_text_llm_client():
    """Build the default text-generation client for macro/industry use cases."""
    settings = get_settings()
    secret_provider = build_secret_provider()
    if settings.llm.text_provider.lower() == "deepseek":
        return DeepSeekClient(secret_provider=secret_provider)
    return KimiTextClient(KimiAgentModel(secret_provider=secret_provider))


def build_agent_repositories(db_path=None):
    """Build all SQLite-backed agent repositories for a shared database path."""
    return {
        "sessions": SQLiteSessionRepository(db_path),
        "runs": SQLiteRunRepository(db_path),
        "events": SQLiteEventRepository(db_path),
        "artifacts": SQLiteArtifactRepository(db_path),
        "approvals": SQLiteApprovalRepository(db_path),
        "documents": SQLiteDocumentRepository(db_path),
        "evidence": SQLiteEvidenceRepository(db_path),
        "run_queue": SQLiteRunQueue(db_path),
        "idempotency": SQLiteIdempotencyStore(db_path),
        "governance": SQLiteEnterpriseGovernanceRepository(db_path),
    }


def build_agent_runtime_kernel(model=None, tool_registry=None, event_publisher=None, db_path=None) -> RuntimeKernel:
    """Build the persisted agent runtime kernel."""
    repos = build_agent_repositories(db_path)
    secret_provider = build_secret_provider()
    if model is None:
        model = build_kimi_agent_model(secret_provider) if secret_provider.get_secret("kimi.api_key") else ScriptedAgentModel()
    if tool_registry is None:
        tool_registry = build_default_tool_registry()
    return RuntimeKernel(
        model=model,
        tool_registry=tool_registry,
        run_repository=repos["runs"],
        event_repository=repos["events"],
        artifact_repository=repos["artifacts"],
        approval_repository=repos["approvals"],
        event_publisher=event_publisher,
        context_builder=ContextBuilder(
            document_repository=repos["documents"],
            evidence_repository=repos["evidence"],
            session_repository=repos["sessions"],
            run_repository=repos["runs"],
        ),
        model_router=build_model_router(document_repository=repos["documents"]),
        agent_backends=build_agent_backends(secret_provider),
        governance_repository=repos["governance"],
    )


def build_model_router(document_repository=None) -> ModelRouter:
    """Build the application model router."""
    return ModelRouter(document_repository=document_repository, settings=get_settings())


def build_agent_backends(secret_provider=None):
    """Build optional agent runtime backends keyed by router backend id."""
    settings = get_settings()
    secret_provider = secret_provider or build_secret_provider()
    return {
        "kimi_agent_sdk": KimiAgentSdkBackend(
            base_url=settings.kimi.base_url,
            model=settings.kimi.general_model,
            secret_provider=secret_provider,
        )
    }


def build_research_agent_runtime(model=None, tool_registry=None) -> InMemoryResearchAgentRuntime:
    """Build the in-memory research-agent runtime for the interview demo."""
    secret_provider = build_secret_provider()
    if model is None:
        model = build_kimi_agent_model(secret_provider) if secret_provider.get_secret("kimi.api_key") else ScriptedAgentModel()
    if tool_registry is None:
        tool_registry = build_default_tool_registry()
    return InMemoryResearchAgentRuntime(model=model, tool_registry=tool_registry)


def build_persisted_research_agent_runtime(model=None, tool_registry=None, event_publisher=None, db_path=None):
    """Build the repository-backed runtime for CLI, daemon and SDK paths."""
    return PersistedResearchAgentRuntime(
        build_agent_runtime_kernel(
            model=model,
            tool_registry=tool_registry,
            event_publisher=event_publisher,
            db_path=db_path,
        )
    )


def build_macro_strategist_agent_use_case(runtime=None) -> MacroStrategistAgentUseCase:
    """Build the RuntimeKernel-backed macro strategist wrapper."""
    if runtime is None:
        runtime = build_persisted_research_agent_runtime()
    return MacroStrategistAgentUseCase(runtime)


def build_industry_analyzer_agent_use_case(runtime=None) -> IndustryAnalyzerAgentUseCase:
    """Build the RuntimeKernel-backed industry analyzer wrapper."""
    if runtime is None:
        runtime = build_persisted_research_agent_runtime()
    return IndustryAnalyzerAgentUseCase(runtime)


def build_agent_document_repository(db_path=None):
    """Build the default persisted document repository."""
    return SQLiteDocumentRepository(db_path)


def build_agent_evidence_repository(db_path=None):
    """Build the default persisted page/chunk/evidence repository."""
    return SQLiteEvidenceRepository(db_path)


def build_file_upload_service(db_path=None, kimi_files_client=None):
    """Build the default file upload service for API and CLI attach paths."""
    settings = get_settings()
    secret_provider = build_secret_provider()
    if kimi_files_client is None and secret_provider.get_secret("kimi.api_key"):
        kimi_files_client = KimiFilesClient(secret_provider=secret_provider)
    return FileUploadService(
        build_agent_document_repository(db_path),
        storage_dir=settings.documents.storage_dir,
        max_file_bytes=settings.documents.max_file_bytes,
        parser=LocalDocumentParser(),
        kimi_files_client=kimi_files_client,
        extraction_service=build_page_extraction_service(db_path),
    )


def build_page_extraction_service(db_path=None):
    """Build the local page/chunk extraction service."""
    return PageExtractionService(
        evidence_repository=build_agent_evidence_repository(db_path),
        parser=LocalDocumentParser(),
    )


def build_rag_service(db_path=None):
    """Build the local-first RAG service over extracted evidence chunks."""
    return RAGService(
        evidence_repository=build_agent_evidence_repository(db_path),
        embedding_provider=HashingEmbeddingProvider(),
        vector_store=SQLiteVectorStore(db_path),
        embedding_cache=SQLiteEmbeddingCache(db_path),
    )


def build_claim_repository(db_path=None):
    """Build the claim/citation repository."""
    return SQLiteClaimRepository(db_path)


def build_portfolio_repository(db_path=None):
    """Build the portfolio repository and ensure the demo portfolio exists."""
    repo = SQLitePortfolioRepository(db_path)
    if repo.get("portfolio-demo") is None:
        repo.save(demo_portfolio())
    return repo


def build_financial_statement_repository():
    """Build the configured financial statement connector."""
    return StockOverviewFinancialStatementRepository(build_stock_service())


def build_company_announcement_repository():
    """Build the configured company announcement connector."""
    return LocalNoteAnnouncementRepository(build_note_repository())


def build_consensus_estimate_repository():
    """Build the configured consensus estimate connector."""
    return UnavailableConsensusEstimateRepository()


def build_industry_classification_source():
    """Build the configured industry classification source."""
    return StaticIndustryClassificationSource()


def build_risk_factor_source():
    """Build the configured risk factor source."""
    return StaticRiskFactorSource()


def build_tool_application_service(db_path=None) -> ToolApplicationService:
    """Build the fully injected application service used by agent tools."""
    return ToolApplicationService(
        stock_service_factory=build_stock_service,
        ranking_service_factory=build_ranking_service,
        breadth_service_factory=build_breadth_service,
        anomaly_service_factory=build_anomaly_service,
        view_service_factory=build_view_service,
        portfolio_service_factory=lambda: build_portfolio_service(db_path),
        risk_service_factory=lambda: build_risk_service(db_path),
        scenario_service_factory=lambda: build_scenario_service(db_path),
        rag_service_factory=lambda: build_rag_service(db_path),
        note_repository_factory=build_note_repository,
        industry_report_use_case_factory=build_generate_industry_report_use_case,
        financial_statement_repository_factory=build_financial_statement_repository,
        company_announcement_repository_factory=build_company_announcement_repository,
        consensus_estimate_repository_factory=build_consensus_estimate_repository,
        industry_classification_source_factory=build_industry_classification_source,
        view_repository_factory=lambda: build_view_repository(read_only=True),
    )


def build_default_tool_registry(entitlement_checker=None, context=None, db_path=None):
    """Build the default tool registry with application dependencies injected."""
    return _build_tool_registry(
        service=build_tool_application_service(db_path),
        entitlement_checker=entitlement_checker,
        context=context,
    )


def build_portfolio_service(db_path=None):
    return PortfolioService(build_portfolio_repository(db_path))


def build_risk_service(db_path=None):
    return RiskService(build_portfolio_repository(db_path), build_risk_factor_source())


def build_scenario_service(db_path=None):
    return ScenarioService(build_portfolio_repository(db_path), build_risk_factor_source())


def build_agent_run_queue(db_path=None):
    """Build the durable run queue adapter."""
    return SQLiteRunQueue(db_path)


def build_agent_idempotency_store(db_path=None):
    """Build the durable idempotency-key adapter."""
    return SQLiteIdempotencyStore(db_path)


def build_agent_unit_of_work(db_path=None, event_publisher=None):
    """Build the transactional unit of work for agent run enqueue."""
    return SQLiteAgentUnitOfWork(db_path, event_publisher=event_publisher)


def build_create_session_use_case(db_path=None) -> CreateSession:
    return CreateSession(SQLiteSessionRepository(db_path))


def build_resume_session_use_case(db_path=None) -> ResumeSession:
    return ResumeSession(SQLiteSessionRepository(db_path))


def build_list_sessions_use_case(db_path=None) -> ListSessions:
    return ListSessions(SQLiteSessionRepository(db_path))


def build_append_turn_use_case(db_path=None) -> AppendTurn:
    return AppendTurn(SQLiteSessionRepository(db_path))


def build_execute_run_use_case(model=None, tool_registry=None, db_path=None) -> ExecuteRun:
    runtime = build_persisted_research_agent_runtime(model=model, tool_registry=tool_registry, db_path=db_path)
    return ExecuteRun(runtime, SQLiteSessionRepository(db_path))


def build_resume_run_use_case(model=None, tool_registry=None, db_path=None) -> ResumeRun:
    runtime = build_persisted_research_agent_runtime(model=model, tool_registry=tool_registry, db_path=db_path)
    return ResumeRun(runtime)


def build_manage_notes_use_case(
    note_repo: INoteRepository | None = None,
) -> ManageNotesUseCase:
    """Build a :class:`ManageNotesUseCase` with the default note repository."""
    return ManageNotesUseCase(note_repo if note_repo is not None else build_note_repository())


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
    return GenerateIndustryReportUseCase(
        ranking_service if ranking_service is not None else build_ranking_service(),
        llm_client if llm_client is not None else build_default_text_llm_client(),
        stock_service=stock_service if stock_service is not None else build_stock_service(),
        rag_service=rag_service if rag_service is not None else build_rag_service(),
        report_repository=report_repository if report_repository is not None else build_report_repository(),
        claim_repository=claim_repository if claim_repository is not None else build_claim_repository(),
        citation_service=CitationService(),
        claim_validation_service=ClaimValidationService(),
    )


def _warn_legacy_composition() -> None:
    """Deprecation helper — not part of public API."""
    warnings.warn(
        "doge.core.services.composition is deprecated; "
        "use doge.application.composition instead",
        DeprecationWarning,
        stacklevel=3,
    )
