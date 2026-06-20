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
from doge.infrastructure.database.sqlite_uow import SQLiteAgentUnitOfWork
from doge.infrastructure.database.sqlite_storage import SQLiteStorageRepository
from doge.infrastructure.data_source.tdx_file_scanner import TDXFileScanner
from doge.infrastructure.data_source.yfinance_metadata import YFinanceMetadataSource
from doge.infrastructure.agent.inmemory_runtime import InMemoryResearchAgentRuntime
from doge.infrastructure.agent.persisted_runtime import PersistedResearchAgentRuntime
from doge.infrastructure.agent.scripted_model import ScriptedAgentModel
from doge.infrastructure.llm.deepseek_client import DeepSeekClient
from doge.infrastructure.llm.kimi_client import KimiAgentModel

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
from doge.application.use_cases.run_use_cases import ExecuteRun, ResumeRun
from doge.application.use_cases.session_use_cases import AppendTurn, CreateSession, ListSessions, ResumeSession
from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.tools import build_default_tool_registry
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
        from doge.infrastructure.data_source.tdx import TDXDataSource
        data_source = TDXDataSource()
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
        llm_client = DeepSeekClient()
    if report_repo is None:
        report_repo = build_report_repository()
    return GenerateMacroReportUseCase(view_repo, llm_client, report_repo)


def build_kimi_agent_model() -> KimiAgentModel:
    """Build the default Kimi agent-capable model adapter."""
    return KimiAgentModel()


def build_agent_repositories(db_path=None):
    """Build all SQLite-backed agent repositories for a shared database path."""
    return {
        "sessions": SQLiteSessionRepository(db_path),
        "runs": SQLiteRunRepository(db_path),
        "events": SQLiteEventRepository(db_path),
        "artifacts": SQLiteArtifactRepository(db_path),
        "approvals": SQLiteApprovalRepository(db_path),
        "documents": SQLiteDocumentRepository(db_path),
        "run_queue": SQLiteRunQueue(db_path),
        "idempotency": SQLiteIdempotencyStore(db_path),
    }


def build_agent_runtime_kernel(model=None, tool_registry=None, event_publisher=None, db_path=None) -> RuntimeKernel:
    """Build the persisted agent runtime kernel."""
    repos = build_agent_repositories(db_path)
    if model is None:
        model = build_kimi_agent_model() if get_settings().kimi.api_key else ScriptedAgentModel()
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
    )


def build_research_agent_runtime(model=None, tool_registry=None) -> InMemoryResearchAgentRuntime:
    """Build the in-memory research-agent runtime for the interview demo."""
    if model is None:
        model = build_kimi_agent_model() if get_settings().kimi.api_key else ScriptedAgentModel()
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


def build_agent_document_repository(db_path=None):
    """Build the default persisted document repository."""
    return SQLiteDocumentRepository(db_path)


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
) -> GenerateIndustryReportUseCase:
    """Alias for :func:`build_generate_industry_report_use_case`."""
    return build_generate_industry_report_use_case(ranking_service, llm_client)


def build_generate_industry_report_use_case(
    ranking_service=None,
    llm_client=None,
) -> GenerateIndustryReportUseCase:
    """Build a :class:`GenerateIndustryReportUseCase` with default adapters."""
    return GenerateIndustryReportUseCase(
        ranking_service if ranking_service is not None else build_ranking_service(),
        llm_client if llm_client is not None else DeepSeekClient(),
    )


def _warn_legacy_composition() -> None:
    """Deprecation helper — not part of public API."""
    warnings.warn(
        "doge.core.services.composition is deprecated; "
        "use doge.application.composition instead",
        DeprecationWarning,
        stacklevel=3,
    )
