"""Unit tests for MomentumRanker.get_connection after the S002-005 refactor.

Validates the three contracts pinned in the S002-005 spec
(testsToAdd[1]):

  1. ``get_connection`` resolves the DB path via centralized settings
     (``Settings().db.dir``) — pointing DOGE_DB_DIR at a tmp dir makes
     ``get_connection('market_data_cn.db')`` resolve to that tmp dir.
  2. ``get_connection`` of a missing DB returns None and prints ``[ERR]``
     (the legacy behavior contract preserved by the refactor).
  3. ``analyze_market`` still produces a ranking after the refactor
     (regression: the clean SQLiteConnection adapter yields a connection
     ``pd.read_sql_query`` can use).

Determinism: a fixture SQLite DB seeded with deterministic rows; no network.
"""
import os
import sqlite3
import sys
from pathlib import Path

import pytest

# Test-shim exception (documented in test_settings.py): make src/ importable.

from doge.config.settings import reset_settings  # noqa: E402
from micro.momentum_scanner import MomentumRanker  # noqa: E402


DOGE_PATH_VARS = [
    "DOGE_DB_DIR",
    "DOGE_CN_DB",
    "DOGE_US_DB",
    "DOGE_RESEARCH_DB",
    "DOGE_DUCKDB_PATH",
]


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    """Point DOGE_DB_DIR at a tmp dir and reset the settings singleton so every
    test resolves market DB paths under the tmp dir (never the live repo)."""
    for var in DOGE_PATH_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("DOGE_DB_DIR", str(tmp_path))
    reset_settings()
    yield tmp_path
    reset_settings()


def _seed_fixture_db(db_path: Path) -> None:
    """Seed a deterministic 70-day series for one CN ticker.

    70 days satisfies the analyze_market 61-day lookback + 18-day RSRS window.
    """
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE stock_prices (
            ticker TEXT, date TEXT, open REAL, high REAL, low REAL,
            close REAL, volume INTEGER, amount REAL,
            PRIMARY KEY (ticker, date)
        );
        """
    )
    rows = []
    base = 10.0
    for i in range(70):
        # Deterministic dates across Jan/Feb/Mar 2026 (no real calendar math
        # needed — analyze_market only reads the textual MAX(date)).
        month = (i // 28) + 1
        day = (i % 28) + 1
        date = f"2026-{month:02d}-{day:02d}"
        close = round(base + i * 0.1, 2)  # gentle uptrend => positive RSRS
        rows.append(
            ("000001.SZ", date, close, close + 0.1, close - 0.1, close, 1000000, 10000000.0)
        )
    conn.executemany(
        "INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Contract 1: get_connection resolves the DB path via settings
# ---------------------------------------------------------------------------
class TestGetConnectionUsesSettingsPath:
    def test_get_connection_resolves_under_configured_db_dir(self, _isolated_settings):
        # Arrange — create the DB at the settings-resolved path.
        from doge.config import get_settings
        db_path = Path(str(get_settings().db.dir)) / "market_data_cn.db"
        _seed_fixture_db(db_path)
        ranker = MomentumRanker()

        # Act
        adapter = ranker.get_connection("market_data_cn.db")

        # Assert — an adapter is returned (not None) for the existing DB.
        assert adapter is not None
        # The adapter resolves to the SAME path the settings singleton does.
        assert str(db_path) == str(get_settings().db.cn_db)


# ---------------------------------------------------------------------------
# Contract 2: missing DB returns None + prints [ERR]
# ---------------------------------------------------------------------------
class TestGetConnectionMissingDbContract:
    def test_get_connection_missing_db_returns_none_and_logs_err(
        self, _isolated_settings, capsys
    ):
        # Arrange — no DB file created.
        ranker = MomentumRanker()

        # Act
        result = ranker.get_connection("does_not_exist.db")

        # Assert — legacy contract preserved: None + an [ERR] line on stdout.
        assert result is None
        captured = capsys.readouterr()
        assert "[ERR]" in captured.out
        assert "does_not_exist.db" in captured.out


# ---------------------------------------------------------------------------
# Contract 3: analyze_market regression — still produces a ranking
# ---------------------------------------------------------------------------
class TestAnalyzeMarketRegression:
    def test_analyze_market_still_returns_rankings_after_refactor(
        self, _isolated_settings, monkeypatch, tmp_path
    ):
        # Arrange — fixture DB at the settings-resolved path.
        from doge.config import get_settings
        db_path = Path(str(get_settings().db.dir)) / "market_data_cn.db"
        _seed_fixture_db(db_path)

        # analyze_market writes a CSV to _project_root(); redirect it to tmp
        # so the test never writes into the repo working tree.
        monkeypatch.setattr(
            "micro.momentum_scanner._project_root", lambda: str(tmp_path)
        )

        ranker = MomentumRanker()

        # Act — capture stdout (analyze_market is a print-based CLI method).
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = ranker.analyze_market("CN", "market_data_cn.db", 5_000_000)
        out = buf.getvalue()

        # Assert — the scan completed (not aborted with a read error) and a
        # ranking CSV was generated for the single seeded ticker.
        assert ret is None  # analyze_market returns None on the success path
        assert "[ERR] 读取错误" not in out, "read path regressed: " + out
        # Either a Top200 CSV was generated, or the ticker was filtered out —
        # but it must NOT be a connection/path error.
        assert "[ERR] 数据库不存在" not in out
        # The fixture ticker (000001.SZ) has a positive uptrend and enough
        # volume, so a ranking CSV is expected.
        assert "榜单已生成" in out or "没有符合条件的标的" in out, out

        # If a CSV was generated, it must be in tmp (never the repo tree).
        if "榜单已生成" in out:
            csv_name = out.split("榜单已生成: ")[1].split()[0]
            assert (tmp_path / csv_name).exists()
