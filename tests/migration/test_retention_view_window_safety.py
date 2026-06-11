"""BLOCKING migration test: retention_days vs analytical-view window safety.

This is the BLOCKING acceptance test named in
production/epics/ep-storage-consistency/EPIC.md and sprint-002-cdd-followup.md
for story S002-007 / TR-006. It proves the destructive retention prune no
longer silently truncates the widest analytical view (vw_market_breadth_cn,
INTERVAL 730 DAYS).

Pipeline under test:
  SQLite cn DB (seeded with N tickers x 400 calendar days)
    -> save_stock_data_custom(retention_days=None -> Settings default 730)
    -> DuckDB views refreshed against the tmp SQLite (data/views.sql)
    -> SELECT from vw_market_breadth_cn
    -> assert MIN(date) <= today - 180d  (rows survive past the OLD 180d boundary)

Plus regression guards:
  - retention default >= 730 (pins the safe-default invariant)
  - DOGE_RETENTION_DAYS env override honored / empty-string falls back
  - save_stock_data_custom honors Settings retention end-to-end
  - widest view window (max INTERVAL N DAYS) <= retention_days

TRAP (per spec synthesis note #7): the DuckDB views are absent until
data/views.sql is EXECUTED against the tmp DuckDB. This test does that
explicitly between seed and assert — without it vw_market_breadth_cn is absent.

TRAP #2: data/views.sql ATTACHes 'data/market_data_cn.db' by RELATIVE path.
The test rewrites those ATTACH paths in-flight to point at the tmp SQLite
files so the view sees the seeded rows.
"""
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Test shim: put src/ on sys.path (documented exception, see test_settings.py:17-18).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import duckdb
import pandas as pd
import pytest

from doge.config import get_settings
from doge.config.settings import reset_settings
from micro.database import init_db_custom, save_stock_data_custom

VIEWS_SQL_PATH = _PROJECT_ROOT / "data" / "views.sql"


def _make_row(ticker: str, date_str: str, close: float) -> dict:
    """One OHLCV row matching the stock_prices schema."""
    return {
        "ticker": ticker,
        "date": date_str,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": 1_000_000,
        "amount": close * 1_000_000,
    }


def _seed_cn_db(cn_db_path: str, tickers: list[str], calendar_days: int) -> None:
    """Seed ``tickers`` x ``calendar_days`` of synthetic OHLCV directly into the
    SQLite cn DB, dated from yesterday back to today - calendar_days (today is
    deliberately excluded so a today-dated trigger row is always newer than
    max_existing, which makes save_stock_data_custom's incremental-append path
    run and reach the per-ticker prune).
    """
    init_db_custom(cn_db_path)
    rows: list[dict] = []
    base = datetime.now()
    # Give each ticker a distinct close so daily returns vary (so the breadth
    # classifier produces non-NULL advancers/decliners).
    for i, ticker in enumerate(tickers):
        for d in range(1, calendar_days + 1):  # 1..calendar_days (exclude today)
            date_str = (base - timedelta(days=d)).strftime("%Y-%m-%d")
            close = 10.0 + i + (d % 5)  # wobble so close != prev_close
            rows.append(_make_row(ticker, date_str, close))
    conn = sqlite3.connect(cn_db_path)
    conn.executemany(
        "INSERT OR REPLACE INTO stock_prices "
        "(ticker, date, open, high, low, close, volume, amount) "
        "VALUES (:ticker, :date, :open, :high, :low, :close, :volume, :amount)",
        rows,
    )
    conn.commit()
    conn.close()


def _rewrite_attach_paths(sql_text: str, cn_db_path: str, us_db_path: str) -> str:
    """Rewrite the relative ATTACH paths in data/views.sql to absolute tmp paths.

    data/views.sql uses:
      ATTACH IF NOT EXISTS 'data/market_data_cn.db' AS cn (TYPE sqlite);
      ATTACH IF NOT EXISTS 'data/market_data_us.db' AS us (TYPE sqlite);
    We redirect both to the test-controlled tmp files so the view sees seeded rows.
    """
    sql_text = re.sub(
        r"ATTACH\s+IF\s+NOT\s+EXISTS\s+'[^']+'\s+AS\s+cn\s+\(TYPE\s+sqlite\)",
        f"ATTACH IF NOT EXISTS '{cn_db_path.replace(os.sep, '/')}' AS cn (TYPE sqlite)",
        sql_text,
        flags=re.IGNORECASE,
    )
    sql_text = re.sub(
        r"ATTACH\s+IF\s+NOT\s+EXISTS\s+'[^']+'\s+AS\s+us\s+\(TYPE\s+sqlite\)",
        f"ATTACH IF NOT EXISTS '{us_db_path.replace(os.sep, '/')}' AS us (TYPE sqlite)",
        sql_text,
        flags=re.IGNORECASE,
    )
    return sql_text


def _strip_sql_comments(sql_text: str) -> str:
    """Remove full-line and trailing ``--`` comments so statement splitting on
    ``;`` yields executable bodies (mirrors the production refresh which parses
    data/views.sql statement-by-statement). Inline ``--`` inside a statement is
    left untouched where it begins a line.
    """
    cleaned_lines = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue  # drop full-line comments
        # Drop trailing inline comments (naive but sufficient for views.sql,
        # which has no '--' inside string literals).
        if "--" in line:
            line = line.split("--", 1)[0]
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _refresh_views(duckdb_path: str, cn_db_path: str, us_db_path: str) -> None:
    """Execute data/views.sql against a tmp DuckDB, creating the analytical views
    over the tmp SQLite files. This is the catalog_generator refresh step the
    spec synthesis (note #7) warns is required or vw_market_breadth_cn is absent.
    """
    sql_text = VIEWS_SQL_PATH.read_text(encoding="utf-8")
    sql_text = _rewrite_attach_paths(sql_text, cn_db_path, us_db_path)
    sql_text = _strip_sql_comments(sql_text)
    con = duckdb.connect(duckdb_path)
    try:
        try:
            con.execute("INSTALL sqlite")
        except duckdb.Error:
            pass  # already installed
        con.execute("LOAD sqlite")
        # Best-effort per-statement execution (mirrors DuckDBConnection.refresh_views
        # duckdb.py:78-80 which swallows per-view failures).
        for stmt in sql_text.split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                con.execute(stmt)
            except duckdb.Error:
                pass
    finally:
        con.close()


@pytest.fixture(autouse=True)
def _clean_env_and_cache(monkeypatch):
    """Reset DOGE_RETENTION_DAYS and the settings singleton around each test."""
    monkeypatch.delenv("DOGE_RETENTION_DAYS", raising=False)
    reset_settings()
    yield
    reset_settings()


class TestRetentionViewWindowSafety:
    def test_retention_default_is_at_least_730(self):
        """Pins the safe-default invariant; would fail before S002-007 (no field)."""
        assert get_settings().market.retention_days >= 730

    def test_doge_retention_days_env_override_honored(self, monkeypatch):
        monkeypatch.setenv("DOGE_RETENTION_DAYS", "900")
        reset_settings()
        assert get_settings().market.retention_days == 900

    def test_empty_string_doge_retention_days_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("DOGE_RETENTION_DAYS", "")
        reset_settings()
        assert get_settings().market.retention_days == 730

    def test_save_stock_data_custom_honors_settings_retention(self, tmp_path):
        """End-to-end: rows older than Settings().market.retention_days are pruned
        and rows within the window survive (proves settings.py -> database.py threading).
        """
        # Arrange
        retention = get_settings().market.retention_days  # 730 default
        cn_db_path = str(tmp_path / "market_data_cn.db")
        init_db_custom(cn_db_path)
        today = datetime.now().strftime("%Y-%m-%d")
        # Seed 1..400d old directly (exclude today so the today-dated trigger
        # appends -> reaches the prune). 400 < 730 retention, so nothing should be pruned.
        rows = [
            _make_row("000001", (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d"), 10.0)
            for d in range(1, 401)
        ]
        conn = sqlite3.connect(cn_db_path)
        conn.executemany(
            "INSERT OR REPLACE INTO stock_prices "
            "(ticker, date, open, high, low, close, volume, amount) "
            "VALUES (:ticker, :date, :open, :high, :low, :close, :volume, :amount)",
            rows,
        )
        conn.commit()
        conn.close()

        # Act — retention_days=None resolves to Settings default (730).
        trigger = pd.DataFrame([_make_row("000001", today, 12.0)])
        save_stock_data_custom(trigger, cn_db_path, retention_days=None)

        # Assert — with retention=730, the 400-day-old row (well past old 180d boundary)
        # survives. cutoff = today - 730d, so 400d-old rows are kept.
        conn = sqlite3.connect(cn_db_path)
        min_date = conn.execute(
            "SELECT MIN(date) FROM stock_prices WHERE ticker = '000001'"
        ).fetchone()[0]
        conn.close()
        cutoff = (datetime.now() - timedelta(days=retention)).strftime("%Y-%m-%d")
        assert min_date >= cutoff, f"row newer than cutoff pruned: {min_date} vs {cutoff}"
        # The 400-day-old row survives (it is within the 730-day window).
        day_400 = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        assert min_date <= day_400, (
            f"400-day-old row was pruned under retention={retention}; "
            "threading from settings.py into database.py is broken"
        )

    def test_widest_view_window_does_not_exceed_retention(self):
        """Regression guard: parse data/views.sql, extract every INTERVAL N DAYS,
        assert max(N) <= retention_days. Prevents re-widening a view without
        raising retention. (vw_volume_anomalies_cn hard-codes '2025-01-01' not
        INTERVAL — it is naturally excluded by the regex.)
        """
        # Arrange
        sql_text = VIEWS_SQL_PATH.read_text(encoding="utf-8")
        windows = [int(m) for m in re.findall(r"INTERVAL\s+(\d+)\s+DAYS", sql_text, flags=re.IGNORECASE)]
        assert windows, "no INTERVAL N DAYS found in data/views.sql — regex is stale"
        # Act / Assert
        widest = max(windows)
        retention = get_settings().market.retention_days
        assert widest <= retention, (
            f"widest view window ({widest}d) exceeds retention_days ({retention}); "
            "breadth scans will be silently truncated"
        )

    def test_breadth_scan_returns_window_promised_rows_past_old_180d_boundary(
        self, tmp_path
    ):
        """BLOCKING gate (EPIC.md acceptance). Seed N tickers x 400 calendar days,
        run save_stock_data_custom with the Settings() default retention, refresh
        the DuckDB views, query vw_market_breadth_cn, and assert MIN(date) <=
        today-180d (rows survive past the OLD 180d boundary — no silent truncation).
        """
        # Arrange — fresh tmp SQLite cn/us + tmp DuckDB
        cn_db_path = str(tmp_path / "market_data_cn.db")
        us_db_path = str(tmp_path / "market_data_us.db")
        duckdb_path = str(tmp_path / "market.duckdb")
        tickers = ["000001", "000002", "600000"]
        _seed_cn_db(cn_db_path, tickers, calendar_days=400)

        # Act 1 — run save_stock_data_custom with the Settings() default (retention_days=None).
        # This exercises the write-path threading: it must resolve 730 from Settings,
        # which keeps the 400-day-old rows (would be deleted under the old 180d default).
        retention = get_settings().market.retention_days
        assert retention >= 730
        today = datetime.now().strftime("%Y-%m-%d")
        for ticker in tickers:
            trigger = pd.DataFrame([_make_row(ticker, today, 15.0)])
            save_stock_data_custom(trigger, cn_db_path, retention_days=None)

        # Sanity — the 400-day-old rows survived the prune (retention 730 keeps them).
        conn = sqlite3.connect(cn_db_path)
        min_db_date = conn.execute("SELECT MIN(date) FROM stock_prices").fetchone()[0]
        conn.close()
        old_180d_boundary = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
        assert min_db_date <= old_180d_boundary, (
            f"rows past the old 180d boundary were pruned (min={min_db_date}); "
            "the 730 default is not actually applied"
        )

        # Act 2 — refresh DuckDB views against the tmp SQLite (the trap step).
        # Seed an empty us DB so the us-ATTACH in views.sql does not fail.
        init_db_custom(us_db_path)
        _refresh_views(duckdb_path, cn_db_path, us_db_path)

        # Act 3 — query vw_market_breadth_cn (the 730-day window view).
        # NOTE: a persisted DuckDB view referencing an attached schema needs the
        # ATTACH re-applied at query time (the attachment is connection-scoped,
        # not persisted with the view definition). We re-attach read-only here.
        con = duckdb.connect(duckdb_path, read_only=True)
        try:
            try:
                con.execute("INSTALL sqlite")
            except duckdb.Error:
                pass
            con.execute("LOAD sqlite")
            con.execute(
                f"ATTACH IF NOT EXISTS '{cn_db_path.replace(os.sep, '/')}' AS cn (TYPE sqlite, READ_ONLY)"
            )
            rows = con.execute("SELECT date FROM vw_market_breadth_cn ORDER BY date").fetchall()
        finally:
            con.close()

        # Assert — rows survive past the OLD 180d boundary: MIN(date) <= today-180d.
        # This proves the 730-day view is no longer silently truncated to ~180 days.
        assert rows, "vw_market_breadth_cn returned no rows — view refresh failed"
        view_dates = [r[0] for r in rows]
        view_min = str(min(view_dates))
        assert view_min <= old_180d_boundary, (
            f"vw_market_breadth_cn MIN(date)={view_min} is newer than the old 180d "
            f"boundary ({old_180d_boundary}); breadth is still silently truncated"
        )
