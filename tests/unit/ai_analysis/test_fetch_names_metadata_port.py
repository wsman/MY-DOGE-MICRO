"""Regression tests for PopulateStockNamesUseCase (S007-004).

Verifies that the use case delegates to ``ITickerMetadataSource`` rather than
calling ``yfinance.Ticker(...).info`` directly. Uses dependency injection with
fake adapters and in-memory SQLite to avoid real network calls.
"""
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from doge.bootstrap.gateway import GatewayContainer
def build_populate_stock_names_use_case(*a, **kw): return GatewayContainer().build_populate_stock_names_use_case(*a, **kw)
from doge.application.contracts.request import PopulateStockNamesRequest
from doge.application.use_cases.populate_stock_names import PopulateStockNamesUseCase
from doge.core.ports.metadata import ITickerMetadataSource
from doge.core.ports.repository import IStockNameRepository, IStockRepository


class FakeMetadataSource(ITickerMetadataSource):
    """In-memory fake for ITickerMetadataSource."""

    def __init__(self, data):
        self._data = data
        self.calls = []

    def get_metadata(self, ticker: str, market: str):
        self.calls.append((ticker, market))
        return self._data.get(ticker)


class FakeStockRepository(IStockRepository):
    """In-memory fake that returns a fixed ticker list."""

    def __init__(self, tickers):
        self._tickers = tickers

    def get_prices(self, ticker, market, days=20):
        return []

    def get_overview(self, ticker, market):
        return {}

    def get_sync_state(self, tickers):
        return {}

    def ensure_schema(self, market):
        pass

    def save_prices(self, market, frame):
        return 0

    def get_kline(self, ticker, market, days=120):
        return []

    def list_distinct_tickers(self, market):
        return list(self._tickers)


@pytest.fixture
def empty_name_repository(tmp_path):
    """A temporary SQLite-backed stock-name repository."""
    db_path = tmp_path / "research.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE stock_names (
            ticker TEXT PRIMARY KEY,
            name_cn TEXT,
            name_en TEXT,
            market TEXT,
            sector TEXT,
            industry TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

    from doge.infrastructure.database.repositories import SQLiteStockNameRepository
    from doge.infrastructure.database.sqlite import SQLiteConnection

    return SQLiteStockNameRepository(SQLiteConnection(str(db_path), use_row_factory=True))


def _load_saved(name_repo: IStockNameRepository):
    """Return all rows from the stock_names table."""
    return sorted(
        [(r["ticker"], r["name_cn"], r["sector"]) for r in name_repo.list_stock_names()]
    )


class TestPopulateStockNamesUseCase:
    def test_calls_metadata_source_not_yfinance(self, empty_name_repository):
        """Use case must use ITickerMetadataSource, not yf.Ticker."""
        fake_source = FakeMetadataSource({
            "AAPL": {"name": "Apple Inc.", "sector": "Technology"},
            "TSLA": {"name": "Tesla, Inc.", "sector": "Consumer Cyclical"},
        })
        fake_stock_repo = FakeStockRepository(["AAPL", "TSLA"])
        uc = PopulateStockNamesUseCase(fake_stock_repo, empty_name_repository, fake_source)

        resp = uc.execute(PopulateStockNamesRequest(market="us"))

        assert fake_source.calls == [("AAPL", "us"), ("TSLA", "us")]
        assert resp.fetched == 2
        assert resp.saved == 2
        assert resp.failed == 0
        assert _load_saved(empty_name_repository) == [
            ("AAPL", "Apple Inc.", "Technology"),
            ("TSLA", "Tesla, Inc.", "Consumer Cyclical"),
        ]

    def test_saves_fallback_when_metadata_returns_none(self, empty_name_repository):
        fake_source = FakeMetadataSource({})
        fake_stock_repo = FakeStockRepository(["MISSING"])
        uc = PopulateStockNamesUseCase(fake_stock_repo, empty_name_repository, fake_source)

        resp = uc.execute(PopulateStockNamesRequest(market="cn"))

        assert resp.saved == 0
        assert resp.failed == 1
        assert _load_saved(empty_name_repository) == [("MISSING", "MISSING", "")]

    def test_skips_tickers_already_present(self, empty_name_repository):
        fake_source = FakeMetadataSource({"AAPL": {"name": "Apple Inc.", "sector": "Technology"}})
        fake_stock_repo = FakeStockRepository(["AAPL"])
        empty_name_repository.save_name("AAPL", "Existing", "Existing", "us", "Old", "")

        uc = PopulateStockNamesUseCase(fake_stock_repo, empty_name_repository, fake_source)
        resp = uc.execute(PopulateStockNamesRequest(market="us"))

        assert fake_source.calls == []  # skipped because already present
        assert resp.fetched == 0
        assert _load_saved(empty_name_repository) == [("AAPL", "Existing", "Old")]

    def test_factory_builds_use_case(self, empty_name_repository):
        """Composition root factory wires the default adapters."""
        fake_source = FakeMetadataSource({"AAPL": {"name": "Apple Inc."}})
        uc = build_populate_stock_names_use_case(
            stock_repo=FakeStockRepository(["AAPL"]),
            name_repo=empty_name_repository,
            metadata_source=fake_source,
        )
        resp = uc.execute(PopulateStockNamesRequest(market="us"))
        assert resp.saved == 1


# TestFetchNamesShimStillWorks retired in Sprint M: it smoked the ai_analysis.fetch_names
# compat shim, which was removed with the src/ai_analysis/ root. PopulateStockNamesUseCase
# is covered by its own canonical tests.
