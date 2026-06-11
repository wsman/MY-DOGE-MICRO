"""SQLite storage write repository — owns the single logical writer for market prices.

Per ADR-0003 (Storage Repository Contract) and the single-logical-writer
principle (``market-data-storage.md:301``), all writes to the ``stock_prices``
SQLite tables flow through this adapter. Read-side access (analytical views)
remains owned by :class:`~doge.infrastructure.database.repositories.DuckDBStockRepository`,
which attaches the same SQLite files read-only via DuckDB.

This adapter wraps the legacy free function
:func:`src.micro.database.save_stock_data_custom` (which already honors the
centralized ``DOGE_RETENTION_DAYS`` knob wired by S002-007). Failures are
translated into
:class:`~doge.core.ports.repository.StorageWriteError` (the typed error
surfacing half of TR-006; the previous behavior swallowed every write
exception with a bare ``except Exception: pass``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from doge.config import get_settings
from doge.core.ports.repository import IStockRepository, StorageWriteError

logger = logging.getLogger(__name__)


class SQLiteStorageRepository(IStockRepository):
    """Write-capable market price repository backed by direct SQLite access.

    ``save_prices`` delegates to the legacy
    ``save_stock_data_custom`` writer and translates any failure into a
    ``StorageWriteError`` (with the original exception chained via
    ``__cause__``).

    The read-side methods (``get_prices`` / ``get_overview`` /
    ``get_sync_state``) are satisfied by delegating to a
    :class:`~doge.infrastructure.database.repositories.DuckDBStockRepository`
    instance. This keeps a single ``IStockRepository`` interface (no
    read/write port split) while preserving the single-logical-writer rule:
    only this class writes, DuckDB reads.
    """

    def __init__(self, read_repo: Optional[IStockRepository] = None):
        """Initialize the storage repository.

        Args:
            read_repo: Optional read-side repository used to satisfy the
                read methods of ``IStockRepository``. Defaults to a fresh
                ``DuckDBStockRepository``. Pass a mock/fake in tests.
        """
        # Lazy import avoids a circular dependency at module load time
        # (repositories.py imports from this package's __init__).
        if read_repo is None:
            from doge.infrastructure.database.repositories import (
                DuckDBStockRepository,
            )
            read_repo = DuckDBStockRepository()
        self._read_repo = read_repo

    # ── Write side ────────────────────────────────────────────────────────

    def save_prices(self, market: str, frame) -> int:
        """Persist ``frame`` to the market SQLite database.

        Args:
            market: ``"cn"`` or ``"us"`` — selects the target DB path via
                centralized ``Settings().db`` (``cn_db`` / ``us_db``).
            frame: A pandas ``DataFrame`` with the OHLCV + ``ticker`` columns
                expected by ``save_stock_data_custom``.

        Returns:
            The number of rows appended to ``stock_prices``.

        Raises:
            StorageWriteError: If the underlying write fails for any reason
                (PK violation, unwritable path, schema mismatch, ...). The
                original exception is preserved on ``__cause__``.
            ValueError: If ``market`` is not ``"cn"`` or ``"us"``.
        """
        if market == "cn":
            db_path: Path = get_settings().db.cn_db
        elif market == "us":
            db_path = get_settings().db.us_db
        else:
            raise ValueError(
                f"unknown market {market!r}; expected 'cn' or 'us'"
            )

        rows_before = self._count_rows(db_path, frame)
        # Legacy writer, imported as a proper package (``micro`` is a package
        # under ``src/``). Imported lazily so this module is import-safe even
        # before the legacy path is initialized, and to avoid a circular import
        # at module load time.
        from micro.database import save_stock_data_custom

        try:
            save_stock_data_custom(frame, str(db_path))
        except StorageWriteError:
            # Already typed by the legacy function (S002-006); propagate as-is.
            raise
        except Exception as exc:
            logger.error(
                "save_prices failed market=%s db=%s: %s",
                market, db_path, exc, exc_info=True,
            )
            raise StorageWriteError(
                f"write failed for market={market} db={db_path}: {exc}"
            ) from exc

        rows_after = self._count_rows(db_path, frame)
        appended = max(0, rows_after - rows_before)
        return appended

    @staticmethod
    def _count_rows(db_path: Path, frame) -> int:
        """Count rows currently stored for the frame's ticker.

        Returns ``0`` if the frame has no ``ticker`` column or the DB is
        unreadable — counting is best-effort, never raises.
        """
        try:
            import sqlite3

            if frame is None or getattr(frame, "empty", False):
                return 0
            ticker = frame["ticker"].iloc[0] if "ticker" in getattr(frame, "columns", []) else None
            if not ticker:
                return 0
            conn = sqlite3.connect(str(db_path))
            try:
                cur = conn.execute(
                    "SELECT COUNT(*) FROM stock_prices WHERE ticker = ?",
                    (str(ticker),),
                )
                row = cur.fetchone()
                return int(row[0]) if row else 0
            finally:
                conn.close()
        except Exception:
            return 0

    # ── Read side (delegated) ─────────────────────────────────────────────

    def get_prices(self, ticker: str, market: str, days: int = 20):
        return self._read_repo.get_prices(ticker, market, days)

    def get_overview(self, ticker: str, market: str) -> dict:
        return self._read_repo.get_overview(ticker, market)

    def get_sync_state(self, tickers):
        return self._read_repo.get_sync_state(tickers)
