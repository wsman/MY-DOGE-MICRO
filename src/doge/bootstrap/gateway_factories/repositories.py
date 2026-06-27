"""Gateway factory helpers for repository adapters."""
from __future__ import annotations
from doge.infrastructure.database.claim_repository import SQLiteClaimRepository
from doge.infrastructure.database.market_view_repository import DuckDBMarketViewRepository
from doge.infrastructure.database.repositories import (
    DuckDBStockRepository,
    SQLiteNoteRepository,
    SQLiteReportRepository,
    SQLiteSchemaBrowser,
    SQLiteStockNameRepository,
)
from doge.infrastructure.database.sqlite_storage import SQLiteStorageRepository


def build_report_repository():
    return SQLiteReportRepository()


def build_schema_browser():
    return SQLiteSchemaBrowser()


def build_stock_repository():
    return DuckDBStockRepository()


def build_note_repository():
    return SQLiteNoteRepository()


def build_stock_name_repository():
    return SQLiteStockNameRepository()


def build_view_repository(*, read_only: bool = True):
    return DuckDBMarketViewRepository(read_only=read_only)


def build_claim_repository(db_path):
    return SQLiteClaimRepository(db_path)


def build_storage_repository():
    return SQLiteStorageRepository()
