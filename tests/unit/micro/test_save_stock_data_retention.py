"""Unit tests for save_stock_data_custom retention threading (TR-006 / S002-007).

Verifies the legacy write path now resolves its destructive ``retention_days``
from ``Settings().market.retention_days`` (``DOGE_RETENTION_DAYS``, default
730) when no explicit arg is passed, that an explicit arg still overrides,
and that the per-ticker prune is applied independently per ticker.

Scenarios (from the S002-007 spec ``testsToAdd``):
- settings-resolved cutoff: retention_days=None -> Settings().market.retention_days
- explicit-arg override: retention_days=60 honored over the settings default
- per-ticker prune: each ticker pruned independently
"""
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Test shim: put src/ on sys.path (documented exception, see test_settings.py:17-18).
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

import pandas as pd
import pytest

from doge.config import get_settings
from doge.config.settings import reset_settings
from micro.database import init_db_custom, save_stock_data_custom


def _make_row(ticker: str, date_str: str, close: float = 10.0) -> dict:
    """Build one OHLCV row dict matching the stock_prices schema."""
    return {
        "ticker": ticker,
        "date": date_str,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": 1000,
        "amount": close * 1000,
    }


def _seed_raw_rows(db_path: str, rows: list[dict]) -> None:
    """Insert rows directly via sqlite3, bypassing save_stock_data_custom's
    incremental guard, so we can place old rows the prune must remove.
    """
    conn = sqlite3.connect(db_path)
    conn.executemany(
        "INSERT OR REPLACE INTO stock_prices "
        "(ticker, date, open, high, low, close, volume, amount) "
        "VALUES (:ticker, :date, :open, :high, :low, :close, :volume, :amount)",
        rows,
    )
    conn.commit()
    conn.close()


def _row_dates(db_path: str, ticker: str) -> list[str]:
    """Return the sorted list of date strings still present for a ticker."""
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "SELECT date FROM stock_prices WHERE ticker = ? ORDER BY date", (ticker,)
    )
    dates = [r[0] for r in cur.fetchall()]
    conn.close()
    return dates


@pytest.fixture(autouse=True)
def _clean_env_and_cache(monkeypatch):
    """Reset DOGE_RETENTION_DAYS and the settings singleton around each test."""
    monkeypatch.delenv("DOGE_RETENTION_DAYS", raising=False)
    reset_settings()
    yield
    reset_settings()


class TestSettingsResolvedRetention:
    def test_save_stock_data_custom_uses_settings_when_retention_none(
        self, monkeypatch, tmp_path
    ):
        # Arrange — pin settings to a retention we can observe (300 days).
        monkeypatch.setenv("DOGE_RETENTION_DAYS", "300")
        reset_settings()
        assert get_settings().market.retention_days == 300

        db_path = str(tmp_path / "cn.db")
        init_db_custom(db_path)
        today = datetime.now().strftime("%Y-%m-%d")
        # Pre-seed rows from 1 .. 400 days old for ticker AAA (exclude today so the
        # today-dated trigger row is newer than max_existing -> append path runs -> prune runs).
        old_rows = [
            _make_row("AAA", (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d"))
            for d in range(1, 401)
        ]
        _seed_raw_rows(db_path, old_rows)

        # Act — call with retention_days=None (the new default); this resolves
        # 300 from Settings and triggers the per-ticker prune for AAA.
        trigger = pd.DataFrame([_make_row("AAA", today, close=99.0)])
        save_stock_data_custom(trigger, db_path, retention_days=None)

        # Assert — rows older than 300 days are pruned; a row near day 200 survives.
        dates = _row_dates(db_path, "AAA")
        cutoff = (datetime.now() - timedelta(days=300)).strftime("%Y-%m-%d")
        assert all(d >= cutoff for d in dates), f"row older than cutoff survived: {dates[:3]}"
        # And rows that should survive (e.g. ~200 days old) are still present.
        day_200 = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
        surviving = [d for d in dates if d <= day_200]
        assert surviving, "rows within the 300-day window were incorrectly pruned"

    def test_save_stock_data_custom_explicit_arg_overrides_settings(
        self, monkeypatch, tmp_path
    ):
        # Arrange — settings default is 730; we pass retention_days=60 explicitly.
        assert get_settings().market.retention_days == 730
        db_path = str(tmp_path / "cn.db")
        init_db_custom(db_path)
        today = datetime.now().strftime("%Y-%m-%d")
        # Pre-seed rows from 1 .. 100 days old (exclude today so trigger appends + prunes).
        old_rows = [
            _make_row("BBB", (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d"))
            for d in range(1, 101)
        ]
        _seed_raw_rows(db_path, old_rows)

        # Act — explicit 60 must override the 730 settings default.
        trigger = pd.DataFrame([_make_row("BBB", today, close=88.0)])
        save_stock_data_custom(trigger, db_path, retention_days=60)

        # Assert — rows older than 60 days are pruned (would survive under 730).
        dates = _row_dates(db_path, "BBB")
        cutoff = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        assert all(d >= cutoff for d in dates), (
            "explicit retention_days=60 was not honored over settings default"
        )
        # And the 70-day-old row is gone (proves 60, not 730, applied).
        day_70 = (datetime.now() - timedelta(days=70)).strftime("%Y-%m-%d")
        assert not any(d <= day_70 for d in dates), (
            "70-day-old row survived — explicit override did not take effect"
        )


class TestPerTickerPrune:
    def test_prune_is_per_ticker(self, monkeypatch, tmp_path):
        # Arrange — retention 60 days; seed two tickers with different spreads.
        db_path = str(tmp_path / "cn.db")
        init_db_custom(db_path)
        today = datetime.now().strftime("%Y-%m-%d")
        # Seed rows from 1..100 days old (exclude today so the trigger appends + prunes).
        rows_ccc = [
            _make_row("CCC", (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d"))
            for d in range(1, 101)  # 1..100 days old
        ]
        rows_ddd = [
            _make_row("DDD", (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d"))
            for d in range(1, 101)  # 1..100 days old
        ]
        _seed_raw_rows(db_path, rows_ccc + rows_ddd)

        # Act — trigger a prune for CCC only (retention_days=60).
        trigger_ccc = pd.DataFrame([_make_row("CCC", today, close=77.0)])
        save_stock_data_custom(trigger_ccc, db_path, retention_days=60)

        # Assert — CCC pruned to the 60-day window, DDD untouched (still 100 rows).
        ccc_dates = _row_dates(db_path, "CCC")
        ddd_dates = _row_dates(db_path, "DDD")
        cutoff = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        assert all(d >= cutoff for d in ccc_dates), "CCC was not pruned"
        # DDD retains its full seeded spread (no row was deleted for DDD).
        assert len(ddd_dates) == 100, (
            f"DDD was incorrectly pruned (expected 100 rows, got {len(ddd_dates)})"
        )
        # A 70-day-old DDD row still exists (proves the WHERE ticker=? clause scopes the delete).
        day_70 = (datetime.now() - timedelta(days=70)).strftime("%Y-%m-%d")
        assert any(d <= day_70 for d in ddd_dates), (
            "DDD lost rows it should not have — prune is not scoped to ticker"
        )
