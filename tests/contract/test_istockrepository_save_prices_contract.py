"""Contract tests for IStockRepository.save_prices (S002-006 / ADR-0003:222).

BLOCKING gate per sprint-002-cdd-followup.md:159 and ADR-0003:222:
"A write that fails inside save_prices raises StorageWriteError and is logged
(not swallowed)."

Verifies:
- ``IStockRepository`` declares ``save_prices(market, frame) -> int``
- ``SQLiteStorageRepository.save_prices`` round-trips rows readable back via
  ``get_prices`` (through the read-side delegate)
- ``SQLiteStorageRepository.save_prices`` raises ``StorageWriteError`` on
  failure (BLOCKING)
- ``DuckDBStockRepository.save_prices`` raises ``NotImplementedError`` (the
  DuckDB adapter is read-only by design — single-logical-writer principle)
- a placeholder assertion that retention is honored (full assertion belongs
  to S002-007)
"""
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from doge.core.ports.repository import IStockRepository, StorageWriteError
from doge.infrastructure.database.repositories import DuckDBStockRepository
from doge.infrastructure.database.sqlite_storage import SQLiteStorageRepository


# ── Helpers ───────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS stock_prices (
    ticker TEXT,
    date TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    amount REAL,
    PRIMARY KEY (ticker, date)
)
"""


def _make_frame(ticker: str = "000001.SZ", rows: int = 3) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [ticker] * rows,
            "date": [f"2026-01-0{i}" for i in range(1, rows + 1)],
            "open": [10.0 + i for i in range(rows)],
            "high": [11.0 + i for i in range(rows)],
            "low": [9.0 + i for i in range(rows)],
            "close": [10.5 + i for i in range(rows)],
            "volume": [1000 * (i + 1) for i in range(rows)],
            "amount": [10000.0 * (i + 1) for i in range(rows)],
        }
    )


def _init_db(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ── Tests ─────────────────────────────────────────────────────────────────

class TestSavePricesInterfaceMethodExists:
    def test_save_prices_interface_method_exists(self):
        """IStockRepository MUST declare save_prices(market, frame) -> int."""
        # Arrange / Act
        # The abstract method must be present on the interface.
        assert hasattr(IStockRepository, "save_prices"), (
            "IStockRepository must declare save_prices per ADR-0003:130-131"
        )
        method = getattr(IStockRepository, "save_prices")
        assert getattr(method, "__isabstractmethod__", False), (
            "save_prices must be an @abstractmethod on IStockRepository"
        )

        # Inspect the signature for the documented (market, frame) -> int shape.
        import inspect

        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        # 'self' plus 'market' and 'frame'
        assert "market" in params and "frame" in params, (
            f"save_prices params must include market and frame; got {params}"
        )


class TestSavePricesRepositoryImplRoundTrips:
    def test_save_prices_repository_impl_round_trips(self, tmp_path, monkeypatch):
        """SQLiteStorageRepository.save_prices writes rows readable back."""
        # Arrange — point Settings().db.cn_db at a fresh fixture DB.
        db_path = tmp_path / "market_cn.db"
        _init_db(db_path)

        from doge.config import settings as settings_module

        # Build a Settings with cn_db pinned to the fixture path.
        monkeypatch.setenv("DOGE_CN_DB", str(db_path))
        settings_module.reset_settings()

        # Inject a mock read-side repo so get_prices reads the same fixture DB.
        read_repo = MagicMock(spec=IStockRepository)

        def _get_prices(ticker, market, days=20):
            conn = sqlite3.connect(str(db_path))
            try:
                cur = conn.execute(
                    "SELECT date, open, high, low, close, volume, amount "
                    "FROM stock_prices WHERE ticker = ? ORDER BY date DESC LIMIT ?",
                    (ticker, days),
                )
                rows = [
                    {
                        "date": r[0], "open": r[1], "high": r[2], "low": r[3],
                        "close": r[4], "volume": r[5], "amount": r[6],
                    }
                    for r in cur.fetchall()
                ]
                return rows
            finally:
                conn.close()

        read_repo.get_prices.side_effect = _get_prices

        repo = SQLiteStorageRepository(read_repo=read_repo)
        frame = _make_frame(rows=3)

        # Act
        appended = repo.save_prices("cn", frame)

        # Assert — rows are readable back via get_prices.
        prices = repo.get_prices("000001.SZ", "cn", days=10)
        assert len(prices) == 3, (
            f"expected 3 rows readable back; got {len(prices)}"
        )
        assert appended >= 0  # row count delta is best-effort but non-negative

        # Cleanup the settings singleton so other tests are unaffected.
        settings_module.reset_settings()


class TestSavePricesRaisesStorageWriteErrorOnFailure:
    def test_save_prices_raises_storage_write_error_on_failure(
        self, tmp_path, monkeypatch
    ):
        """BLOCKING (ADR-0003:222): a write failure raises StorageWriteError."""
        # Arrange — force the legacy writer to raise by monkeypatching the
        # save_stock_data_custom import inside SQLiteStorageRepository.save_prices.
        db_path = tmp_path / "market_cn.db"
        _init_db(db_path)

        from doge.config import settings as settings_module

        monkeypatch.setenv("DOGE_CN_DB", str(db_path))
        settings_module.reset_settings()

        read_repo = MagicMock(spec=IStockRepository)
        repo = SQLiteStorageRepository(read_repo=read_repo)

        # Inject a failing legacy writer via the SAME module the adapter
        # imports lazily (``from micro.database import save_stock_data_custom``
        # inside save_prices). Patching ``micro.database`` is picked up because
        # the adapter re-reads the attribute at call time.
        import micro.database as legacy_db

        def _failing_save(data, db_path, retention_days=None):
            raise sqlite3.OperationalError("forced underlying write failure")

        monkeypatch.setattr(legacy_db, "save_stock_data_custom", _failing_save)

        # Act + Assert
        with pytest.raises(StorageWriteError):
            repo.save_prices("cn", _make_frame())

        settings_module.reset_settings()


class TestDuckDBRepositorySavePricesRaisesNotImplemented:
    def test_duckdb_repository_save_prices_raises_not_implemented(self):
        """The read-only DuckDB adapter refuses writes by contract.

        Single-logical-writer principle: writes route through
        SQLiteStorageRepository only.
        """
        # Arrange
        repo = DuckDBStockRepository()

        # Act + Assert
        with pytest.raises(NotImplementedError):
            repo.save_prices("cn", _make_frame())


class TestSavePricesHonorsRetentionParam:
    def test_save_prices_honors_retention_param(self, tmp_path, monkeypatch):
        """Placeholder retention assertion.

        Full retention-days invariant (DOGE_RETENTION_DAYS >= 730) is owned by
        S002-007; here we only confirm the method accepts the centralized
        retention path without erroring on a normal write.
        """
        # Arrange
        db_path = tmp_path / "market_cn.db"
        _init_db(db_path)

        from doge.config import settings as settings_module

        monkeypatch.setenv("DOGE_CN_DB", str(db_path))
        settings_module.reset_settings()

        read_repo = MagicMock(spec=IStockRepository)
        read_repo.get_prices.return_value = []
        repo = SQLiteStorageRepository(read_repo=read_repo)

        # Act — a normal write under the default retention must succeed.
        appended = repo.save_prices("cn", _make_frame(rows=2))

        # Assert — no exception, and rows landed in the fixture DB.
        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.execute(
                "SELECT COUNT(*) FROM stock_prices WHERE ticker = ?",
                ("000001.SZ",),
            )
            assert cur.fetchone()[0] == 2
        finally:
            conn.close()

        settings_module.reset_settings()
