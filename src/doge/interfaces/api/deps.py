"""FastAPI dependency providers for the API interface layer.

This module is the **single sanctioned site** where API routers import
application-layer factories. Routers MUST NOT import ``sqlite3``, ``duckdb``,
or any legacy connection helper directly; they request a port/use case via
``Depends(deps.get_*)`` and this module wires the default adapter through
``doge.application.composition``.
"""

import os

from fastapi import Header, HTTPException, Request

from doge.config import Settings, get_settings
from doge.core.ports.metadata import ITickerMetadataSource
from doge.core.ports.repository import IReportRepository, ISchemaBrowser, IStockRepository, INoteRepository
from doge.core.ports.tdx_server_list import ITDXServerList
from doge import application as app_composition
from doge.infrastructure.database.sqlite_storage import SQLiteStorageRepository

_research_agent_runtime = None
_persisted_research_agent_runtime = None
_event_bus = None
_worker = None
_run_queue = None
_idempotency_store = None
_agent_unit_of_work = None
_file_upload_service = None


def get_settings_dep() -> Settings:
    """Return the current ``Settings`` singleton."""
    return get_settings()


def get_report_repository() -> IReportRepository:
    """Provide the default SQLite-backed report repository."""
    return app_composition.build_report_repository()


def get_schema_browser() -> ISchemaBrowser:
    """Provide the default SQLite-backed schema browser."""
    return app_composition.build_schema_browser()


def get_stock_repository() -> IStockRepository:
    """Provide the default DuckDB-backed stock repository."""
    return app_composition.build_stock_repository()


def get_note_repository() -> INoteRepository:
    """Provide the default SQLite-backed note repository."""
    return app_composition.build_note_repository()


def get_manage_notes_use_case():
    """Provide the default ``ManageNotesUseCase``."""
    return app_composition.build_manage_notes_use_case()


def get_generate_macro_report_use_case():
    """Provide the default ``GenerateMacroReportUseCase``."""
    return app_composition.build_generate_macro_report_use_case()


def get_generate_industry_report_use_case():
    """Provide the default ``GenerateIndustryReportUseCase``."""
    return app_composition.build_generate_industry_report_use_case()


def get_research_agent_runtime():
    """Provide the process-local in-memory research agent runtime."""
    global _research_agent_runtime
    if _research_agent_runtime is None:
        _research_agent_runtime = app_composition.build_research_agent_runtime()
    return _research_agent_runtime


def get_event_bus():
    """Provide the in-process event bus for daemon/v1 streams."""
    global _event_bus
    if _event_bus is None:
        from doge.application.agent.event_bus import EventBus

        _event_bus = EventBus()
    return _event_bus


def get_persisted_research_agent_runtime():
    """Provide the repository-backed research agent runtime."""
    global _persisted_research_agent_runtime
    if _persisted_research_agent_runtime is None:
        _persisted_research_agent_runtime = app_composition.build_persisted_research_agent_runtime(
            event_publisher=get_event_bus()
        )
    return _persisted_research_agent_runtime


def get_agent_document_repository():
    """Provide the persisted document repository."""
    return app_composition.build_agent_document_repository()


def get_file_upload_service():
    """Provide the shared file upload service."""
    global _file_upload_service
    if _file_upload_service is None:
        _file_upload_service = app_composition.build_file_upload_service()
    return _file_upload_service


def get_agent_session_repository():
    """Provide the persisted session repository."""
    return app_composition.build_agent_repositories()["sessions"]


def get_run_queue():
    """Provide the durable agent run queue."""
    global _run_queue
    if _run_queue is None:
        _run_queue = app_composition.build_agent_run_queue()
    return _run_queue


def get_idempotency_store():
    """Provide the durable idempotency-key store."""
    global _idempotency_store
    if _idempotency_store is None:
        _idempotency_store = app_composition.build_agent_idempotency_store()
    return _idempotency_store


def get_agent_unit_of_work():
    """Provide the transactional unit of work for daemon enqueue."""
    global _agent_unit_of_work
    if _agent_unit_of_work is None:
        _agent_unit_of_work = app_composition.build_agent_unit_of_work(event_publisher=get_event_bus())
    return _agent_unit_of_work


def get_daemon_worker():
    """Provide the singleton daemon worker."""
    global _worker
    if _worker is None:
        from doge.application.agent.worker import AsyncioWorker

        _worker = AsyncioWorker(
            get_persisted_research_agent_runtime(),
            get_agent_session_repository(),
            get_run_queue(),
            get_idempotency_store(),
            get_agent_unit_of_work(),
        )
    return _worker


def require_api_token(authorization: str | None = Header(default=None)):
    """Require bearer auth only when DOGE_API_TOKEN is configured."""
    expected = os.environ.get("DOGE_API_TOKEN")
    if not expected:
        return None
    if authorization != f"Bearer {expected}":
        raise HTTPException(401, "unauthorized")
    return None


def get_metadata_source() -> ITickerMetadataSource:
    """Provide the default yfinance-backed ticker metadata source."""
    return app_composition.build_metadata_source()


def get_storage_repository() -> SQLiteStorageRepository:
    """Provide the single-logical-writer SQLite storage repository.

    Used by the scan router for schema bootstrap. Exposed here so the router
    does not import an infrastructure adapter directly.
    """
    return SQLiteStorageRepository()


def get_tdx_server_list() -> ITDXServerList:
    """Provide the configured TDX server directory adapter."""
    return app_composition.build_tdx_server_list()


def get_request_state(request: Request) -> dict:
    """Expose FastAPI request state to handlers that need it."""
    return request.state
