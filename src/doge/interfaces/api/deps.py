"""FastAPI dependency providers for the API interface layer.

This module is the **single sanctioned site** where API routers import
infrastructure-backed ports. Routers MUST NOT import ``sqlite3``, ``duckdb``,
or any legacy connection helper directly; they request a port via
``Depends(deps.get_*)`` and this module wires the default adapter through the
composition root.

Mirrors ``doge.core.services.composition`` for the FastAPI lifecycle.
"""

from fastapi import Request

from doge.config import Settings, get_settings
from doge.core.ports.repository import IReportRepository, ISchemaBrowser, IStockRepository, INoteRepository
from doge.core.services import composition


def get_settings_dep() -> Settings:
    """Return the current ``Settings`` singleton."""
    return get_settings()


def get_report_repository() -> IReportRepository:
    """Provide the default SQLite-backed report repository."""
    return composition.build_report_repository()


def get_schema_browser() -> ISchemaBrowser:
    """Provide the default SQLite-backed schema browser."""
    return composition.build_schema_browser()


def get_stock_repository() -> IStockRepository:
    """Provide the default DuckDB-backed stock repository."""
    return composition.build_stock_repository()


def get_note_repository() -> INoteRepository:
    """Provide the default SQLite-backed note repository."""
    return composition.build_note_repository()


def get_request_state(request: Request) -> dict:
    """Expose FastAPI request state to handlers that need it."""
    return request.state
