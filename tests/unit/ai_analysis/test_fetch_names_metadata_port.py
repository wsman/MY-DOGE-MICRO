"""Regression tests for fetch_names.py metadata-port migration (S006-006).

Verifies that ``fetch_batch_yfinance`` delegates to ``ITickerMetadataSource``
rather than calling ``yfinance.Ticker(...).info`` directly. The module is
CLI/IO-shaped, so these tests use dependency injection and in-memory SQLite to
avoid real network calls.
"""
from unittest.mock import MagicMock

import pytest

from ai_analysis import fetch_names


class FakeMetadataSource:
    """In-memory fake for ITickerMetadataSource."""

    def __init__(self, data):
        self._data = data
        self.calls = []

    def get_metadata(self, ticker: str, market: str):
        self.calls.append((ticker, market))
        return self._data.get(ticker)


@pytest.fixture
def empty_notes_db(tmp_path, monkeypatch):
    """Point fetch_names at a temporary research_db with the stock_names table."""
    db_path = tmp_path / "research.db"
    conn = fetch_names.sqlite3.connect(str(db_path))
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

    class _FakeDb:
        research_db = db_path
        dir = tmp_path

    monkeypatch.setattr(
        fetch_names,
        "_NOTES_DB",
        _FakeDb(),
        raising=False,
    )
    monkeypatch.setattr(fetch_names, "NOTES_DB", str(db_path))
    monkeypatch.setattr(fetch_names, "CACHE_PATH", str(tmp_path / "meta_cache.json"))
    return db_path


def _load_saved(empty_notes_db):
    """Return all rows from the temporary stock_names table."""
    conn = fetch_names.sqlite3.connect(str(empty_notes_db))
    cur = conn.cursor()
    cur.execute("SELECT ticker, name_cn, sector FROM stock_names ORDER BY ticker")
    rows = cur.fetchall()
    conn.close()
    return rows


class TestFetchBatchYfinanceDelegatesToMetadataPort:
    def test_calls_metadata_source_not_yfinance(self, empty_notes_db, monkeypatch, capsys):
        """fetch_batch_yfinance must use ITickerMetadataSource, not yf.Ticker."""
        fake = FakeMetadataSource({
            "AAPL": {"name": "Apple Inc.", "sector": "Technology"},
            "TSLA": {"name": "Tesla, Inc.", "sector": "Consumer Cyclical"},
        })
        monkeypatch.setattr(
            fetch_names,
            "build_metadata_source",
            lambda: fake,
        )
        # Ensure no accidental yfinance import is used.
        yfinance_imported = {"called": False}
        real_import = __builtins__["__import__"]

        def _guard_import(name, *args, **kwargs):
            if name == "yfinance" or name.startswith("yfinance."):
                yfinance_imported["called"] = True
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _guard_import)

        fetch_names.fetch_batch_yfinance(["AAPL", "TSLA"], market="us")

        captured = capsys.readouterr()
        assert fake.calls == [("AAPL", "us"), ("TSLA", "us")]
        assert yfinance_imported["called"] is False
        assert "Done: 2/2 names fetched" in captured.out

        rows = _load_saved(empty_notes_db)
        assert rows == [
            ("AAPL", "Apple Inc.", "Technology"),
            ("TSLA", "Tesla, Inc.", "Consumer Cyclical"),
        ]

    def test_saves_fallback_when_metadata_returns_none(self, empty_notes_db, monkeypatch, capsys):
        fake = FakeMetadataSource({})
        monkeypatch.setattr(fetch_names, "build_metadata_source", lambda: fake)

        fetch_names.fetch_batch_yfinance(["MISSING"], market="cn")

        rows = _load_saved(empty_notes_db)
        assert rows == [("MISSING", "MISSING", "")]

    def test_skips_tickers_already_present(self, empty_notes_db, monkeypatch):
        fake = FakeMetadataSource({"AAPL": {"name": "Apple Inc.", "sector": "Technology"}})
        monkeypatch.setattr(fetch_names, "build_metadata_source", lambda: fake)

        # Pre-populate one ticker.
        fetch_names.save_name("AAPL", "Existing", "Existing", "us", "Old", "")

        fetch_names.fetch_batch_yfinance(["AAPL"], market="us")

        assert fake.calls == []  # skipped because already present
        rows = _load_saved(empty_notes_db)
        assert rows == [("AAPL", "Existing", "Old")]

    def test_injected_metadata_source_takes_precedence(self, empty_notes_db):
        """The metadata_source keyword argument bypasses build_metadata_source."""
        fake = FakeMetadataSource({"600000.SH": {"name": "China Test", "sector": "Financials"}})

        fetch_names.fetch_batch_yfinance(
            ["600000.SH"], market="cn", metadata_source=fake
        )

        assert fake.calls == [("600000.SH", "cn")]
        rows = _load_saved(empty_notes_db)
        assert rows == [("600000.SH", "China Test", "Financials")]
