"""FastAPI dependency providers for the API interface layer.

This module is the **single sanctioned site** where API routers import
application-layer factories. Routers MUST NOT import ``sqlite3``, ``duckdb``,
or any legacy connection helper directly; they request a port/use case via
``Depends(deps.get_*)`` and this module wires the default adapter through
``doge.application.composition``.
"""

from fastapi import Request

from doge.config import Settings, get_settings
from doge.core.ports.metadata import ITickerMetadataSource
from doge.core.ports.repository import IReportRepository, ISchemaBrowser, IStockRepository, INoteRepository
from doge import application as app_composition
from doge.infrastructure.database.sqlite_storage import SQLiteStorageRepository


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


def get_metadata_source() -> ITickerMetadataSource:
    """Provide the default yfinance-backed ticker metadata source."""
    return app_composition.build_metadata_source()


def get_storage_repository() -> SQLiteStorageRepository:
    """Provide the single-logical-writer SQLite storage repository.

    Used by the scan router for schema bootstrap. Exposed here so the router
    does not import an infrastructure adapter directly.
    """
    return SQLiteStorageRepository()


def get_request_state(request: Request) -> dict:
    """Expose FastAPI request state to handlers that need it."""
    return request.state
