"""Contract tests for the FastAPI service (Module #9).

Covers BUG E (BLOCKING per .claude/rules/api-code.md): every endpoint across all
six routers must have contract/integration tests for the success case, a
validation-failure (4xx) case, and at least one edge case. No auth in this
local-first API, so the auth-failure case is intentionally skipped.

Scope (route table enumerated in the fastapi-service CDD section 4):
  - GET  /api/health
  - GET  /api/stats
  - GET  /api/scan/servers
  - POST /api/scan/servers/test
  - GET  /api/scan/status
  - POST /api/scan/{market}              (validation + concurrency 409 only; the
                                          success path spawns a TDX/network
                                          background thread and is out of scope
                                          for an isolated contract test)
  - GET  /api/data/{market}/tables
  - GET  /api/data/{market}/table/{table_name}
  - GET  /api/data/{market}/ticker/{ticker}/kline
  - GET  /api/data/{market}/ticker-names
  - GET  /api/notes/ticker/{ticker}
  - POST /api/notes
  - GET  /api/notes/search
  - GET  /api/notes/recent
  - GET  /api/notes/tracked
  - DELETE /api/notes/{note_id}          (Bug A contract: 200 on delete, 404
                                          when not found)
  - GET  /api/macro/reports
  - GET  /api/macro/reports/latest
  - GET  /api/macro/reports/{report_id}
  - POST /api/macro/run                  (validation only — SSE success path
                                          hits yfinance + the LLM provider)
  - GET  /api/analysis/reports
  - GET  /api/analysis/reports/{report_id}
  - GET  /api/config
  - GET  /api/config/settings
  - PUT  /api/config/settings
  - POST /api/config/validate-tdx

Isolation rules (test-standards.md + ADR-0001 forbidden "network-dependent tests
without isolation"):
  - No live SQLite/DuckDB reads: each read router's ``_PROJECT_ROOT`` is
    redirected to a temp data dir (the DB files are absent, so endpoints return
    their documented empty/404 shapes); for the success-table path a tiny
    throwaway SQLite file is created in the temp dir.
  - The kline endpoint's ``connect_duckdb`` lazy import is monkeypatched with a
    fake that returns deterministic rows.
  - The notes endpoints receive an :class:`INoteRepository` via FastAPI
    ``Depends(deps.get_note_repository)``; the ``notes_db`` fixture isolates
    its SQLite path by setting ``DOGE_RESEARCH_DB`` and resetting the settings
    singleton (S004 Wave A; mirrors the ``temp_project_root`` pattern).
  - The config endpoints' ``_PROJECT_ROOT`` is redirected to a temp dir so the
    ``models_config.json`` / ``user_settings.json`` reads/writes never touch the
    repo working tree.
  - The SSE/streaming success paths (POST /api/scan/{market}, POST /api/macro/run)
    are NOT exercised here because they spawn background threads that call TDX
    servers and the LLM provider; only their validation-failure and concurrency
    (409) branches are tested.
"""
import json
import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap — isolated from the operator's global environment.
#
# The operator's site-packages may contain a .pth pointing at a sibling project
# (e.g. MY-DOGE-PRO) whose own ``src`` package shadows this one. We strip those
# polluting entries and insert ONLY this project's root, so ``import src.api``
# resolves to this repo. This is the documented test-shim exception
# (tests/test_settings.py:18, tests/test_macro_strategist.py:26).
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:] = [
    p for p in sys.path
    if p and "MY-DOGE-PRO" not in p and "opendoge" not in p
]

from fastapi.testclient import TestClient  # noqa: E402

from doge.interfaces.api import main as api_main  # noqa: E402
from doge.interfaces.api.routers import (  # noqa: E402
    analysis as analysis_router,
    config as config_router,
    data as data_router,
    macro as macro_router,
    notes as notes_router,
)
from doge.interfaces.api import deps  # noqa: E402

# S004 Wave A: the notes router now receives an ``INoteRepository`` via
# ``Depends(deps.get_note_repository)``; the legacy ``stock_notes.NOTES_DB``
# module global is no longer consulted. DB isolation for notes tests is done
# via ``DOGE_RESEARCH_DB`` + settings reset in the ``notes_db`` fixture below.


# ---------------------------------------------------------------------------
# Live schema for the temp stock_notes DB (mirrors tests/test_notes_crud.py).
# ---------------------------------------------------------------------------
NOTES_SCHEMA_SQL = """
CREATE TABLE stock_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    market TEXT NOT NULL DEFAULT 'cn',
    created_at TEXT NOT NULL,
    note_type TEXT DEFAULT 'comment',
    title TEXT,
    content TEXT NOT NULL,
    tags TEXT,
    price_at_note REAL,
    source TEXT DEFAULT 'user',
    deleted_at TIMESTAMP
);
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    """A FastAPI TestClient bound to the live app.

    ``httpx``-based; no real socket is opened. All side-effecting endpoints are
    isolated by the per-router fixtures below.
    """
    return TestClient(api_main.app)


@pytest.fixture
def temp_project_root(tmp_path, monkeypatch):
    """Redirect DB paths and file-I/O roots to a temp dir.

    S003-003: routers now receive repositories via FastAPI ``Depends()`` rather
    than module-global DB maps. The default providers resolve paths from
    :func:`~doge.config.get_settings`, so we point ``DOGE_DB_DIR`` at the temp
    ``data/`` directory and reset the settings singleton. ``_PROJECT_ROOT`` is
    still monkeypatched for routers that perform file I/O (config JSON,
    ticker-names JSON cache).
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Point all Settings-derived DB paths at the temp data directory.
    monkeypatch.setenv("DOGE_DB_DIR", str(data_dir))
    from doge.config import settings as settings_module

    settings_module.reset_settings()

    # Clear any leftover dependency overrides from previous tests.
    api_main.app.dependency_overrides = {}

    # File-I/O routers still use module-global _PROJECT_ROOT.
    for router in (config_router, data_router):
        monkeypatch.setattr(router, "_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(api_main, "_PROJECT_ROOT", str(tmp_path))

    yield tmp_path

    # Ensure overrides never leak between tests.
    api_main.app.dependency_overrides = {}


@pytest.fixture
def notes_db(tmp_path, monkeypatch):
    """A temp SQLite file with a fresh ``stock_notes`` table.

    S004 Wave A: the notes router now receives an :class:`INoteRepository`
    via FastAPI ``Depends(deps.get_note_repository)``. The default provider
    (:func:`doge.interfaces.api.deps.get_note_repository`) builds a
    :class:`SQLiteNoteRepository` whose :class:`SQLiteConnection` resolves
    its DB path from ``settings.db.research_db`` (ADR-0002). The legacy
    ``stock_notes.NOTES_DB`` module global is no longer consulted by the
    router, so patching it would silently leak notes into the real
    ``data/research_insights.db``.

    Mirrors the settings-based isolation in :func:`temp_project_root`:
    set ``DOGE_RESEARCH_DB`` to the temp file path, reset the settings
    singleton so the next ``get_settings()`` re-reads the env, and clear
    any leftover FastAPI dependency overrides defensively.
    """
    db_path = tmp_path / "test_research_insights.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(NOTES_SCHEMA_SQL)
    conn.commit()
    conn.close()

    monkeypatch.setenv("DOGE_RESEARCH_DB", str(db_path))
    from doge.config import settings as settings_module

    settings_module.reset_settings()
    api_main.app.dependency_overrides = {}

    yield str(db_path)

    # Ensure overrides and the settings override never leak between tests.
    api_main.app.dependency_overrides = {}
    settings_module.reset_settings()
    monkeypatch.delenv("DOGE_RESEARCH_DB", raising=False)


def _make_cn_db(root: Path) -> str:
    """Create a tiny market_data_cn.db with one row for table/kline tests."""
    db_path = root / "data" / "market_data_cn.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE stock_prices (
            ticker TEXT, date TEXT, open REAL, high REAL, low REAL,
            close REAL, volume INTEGER, amount REAL,
            PRIMARY KEY (ticker, date)
        );
        INSERT INTO stock_prices VALUES
            ('000001.SZ', '2026-06-10', 10.0, 10.5, 9.8, 10.2, 1000, 10200.0),
            ('000001.SZ', '2026-06-11', 10.2, 10.6, 10.1, 10.5, 1200, 12600.0);
        """
    )
    conn.commit()
    conn.close()
    return str(db_path)


def _make_research_db(root: Path) -> str:
    """Create a tiny research_insights.db with macro + research report rows."""
    db_path = root / "data" / "research_insights.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE macro_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, timestamp TEXT, tags TEXT, analyst TEXT,
            risk_signal TEXT, volatility TEXT, content TEXT
        );
        CREATE TABLE research_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, timestamp TEXT, tags TEXT, analyst TEXT,
            title TEXT, content TEXT
        );
        INSERT INTO macro_reports (date, timestamp, risk_signal, volatility, content)
            VALUES ('2026-06-11', '2026-06-11 09:00:00', 'risk-on', '0.18', 'macro body');
        INSERT INTO research_reports (date, timestamp, title, content)
            VALUES ('2026-06-11', '2026-06-11 09:00:00', 'industry report', 'research body');
        """
    )
    conn.commit()
    conn.close()
    return str(db_path)


# ===========================================================================
# Top-level helpers (/api/health, /api/stats)
# ===========================================================================
class TestHealthAndStats:
    def test_health_returns_ok(self, client):
        # Act
        r = client.get("/api/health")
        # Assert — success: stable shape
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_health_404_for_unknown_path(self, client):
        # Edge case: a path that does not exist returns 404 (not 500).
        r = client.get("/api/does-not-exist")
        assert r.status_code == 404

    def test_stats_returns_object_when_no_dbs(self, client, temp_project_root):
        # Success case with empty data dir: every DB file is absent -> {}.
        r = client.get("/api/stats")
        assert r.status_code == 200
        assert r.json() == {}

    def test_stats_reports_table_counts_when_db_present(self, client, temp_project_root):
        # Success case: a DB file exists with a table -> counts surface.
        _make_cn_db(temp_project_root)
        r = client.get("/api/stats")
        assert r.status_code == 200
        body = r.json()
        assert "market_data_cn.db" in body
        assert body["market_data_cn.db"]["stock_prices"] == 2


# ===========================================================================
# scan router
# ===========================================================================
class TestScanRouter:
    def test_get_servers_returns_cn_us_lists(self, client):
        # Success
        r = client.get("/api/scan/servers")
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) == {"cn", "us"}
        assert isinstance(body["cn"], list) and isinstance(body["us"], list)
        # Each entry has the documented host/port/latency shape.
        if body["cn"]:
            assert set(body["cn"][0].keys()) == {"host", "port", "latency_ms"}

    def test_get_status_returns_idle_initially(self, client):
        # Success — fresh process: both markets idle.
        r = client.get("/api/scan/status")
        assert r.status_code == 200
        assert r.json() == {"cn": "idle", "us": "idle"}

    def test_servers_test_rejects_invalid_market(self, client):
        # Validation failure: market must be cn|us -> 400.
        r = client.post("/api/scan/servers/test", json={"market": "xx"})
        assert r.status_code == 400

    def test_servers_test_missing_body_is_422(self, client):
        # Validation failure: no JSON body -> pydantic 422.
        r = client.post("/api/scan/servers/test")
        assert r.status_code == 422

    def test_start_scan_rejects_invalid_market(self, client):
        # Validation failure: path market not cn|us -> 400.
        r = client.post("/api/scan/xx", json={})
        assert r.status_code == 400

    def test_start_scan_missing_body_is_422(self, client):
        # Validation failure: no body -> 422 (pydantic needs ScanRequest).
        r = client.post("/api/scan/cn")
        assert r.status_code == 422


# ===========================================================================
# data router
# ===========================================================================
class TestDataRouter:
    def test_list_tables_rejects_invalid_market(self, client, temp_project_root):
        # Validation failure
        r = client.get("/api/data/xx/tables")
        assert r.status_code == 400

    def test_list_tables_empty_when_db_absent(self, client, temp_project_root):
        # Edge case: valid market but no DB file -> 200 with empty list.
        r = client.get("/api/data/cn/tables")
        assert r.status_code == 200
        assert r.json() == {"tables": []}

    def test_list_tables_returns_tables_when_db_present(self, client, temp_project_root):
        # Success
        _make_cn_db(temp_project_root)
        r = client.get("/api/data/cn/tables")
        assert r.status_code == 200
        assert "stock_prices" in r.json()["tables"]

    def test_query_table_invalid_market(self, client, temp_project_root):
        # Validation failure
        r = client.get("/api/data/xx/table/stock_prices")
        assert r.status_code == 400

    def test_query_table_page_below_minimum_is_422(self, client, temp_project_root):
        # Validation failure: page ge=1 enforced by Query() -> 422.
        r = client.get("/api/data/cn/table/stock_prices?page=0")
        assert r.status_code == 422

    def test_query_table_page_size_above_max_is_422(self, client, temp_project_root):
        # Validation failure: page_size le=500 -> 422.
        r = client.get("/api/data/cn/table/stock_prices?page_size=999")
        assert r.status_code == 422

    def test_query_table_404_when_db_absent(self, client, temp_project_root):
        # Edge case: valid market, DB absent -> 404.
        r = client.get("/api/data/cn/table/stock_prices")
        assert r.status_code == 404

    def test_query_table_404_when_table_absent(self, client, temp_project_root):
        # Edge case: DB present, table absent -> 404.
        _make_cn_db(temp_project_root)
        r = client.get("/api/data/cn/table/no_such_table")
        assert r.status_code == 404

    def test_query_table_success_returns_columns_rows_total(self, client, temp_project_root):
        # Success
        _make_cn_db(temp_project_root)
        r = client.get("/api/data/cn/table/stock_prices")
        assert r.status_code == 200
        body = r.json()
        assert "columns" in body and "rows" in body and "total" in body
        assert body["total"] == 2
        assert len(body["rows"]) == 2

    def test_kline_rejects_invalid_market(self, client, temp_project_root):
        # Validation failure
        r = client.get("/api/data/xx/ticker/AAPL/kline")
        assert r.status_code == 400

    def test_kline_days_out_of_range_is_422(self, client, temp_project_root):
        # Validation failure: days le=365 -> 422.
        r = client.get("/api/data/cn/ticker/000001.SZ/kline?days=99999")
        assert r.status_code == 422

    def test_kline_success_returns_data_list(self, client, temp_project_root):
        # Success — the stock repository is replaced via dependency_overrides
        # so the test uses deterministic rows (no live DuckDB / sqlite attach).
        import pandas as pd
        from doge.core.ports.repository import IStockRepository

        fake_df_rows = [
            {"date": "2026-06-10", "open": 10.0, "high": 10.5, "low": 9.8,
             "close": 10.2, "volume": 1000, "ma_5": 10.1, "ma_10": 10.0,
             "ma_20": 9.9, "ma_60": 9.5, "atr_14": 0.3},
        ]
        fake_repo = MagicMock(spec=IStockRepository)
        fake_repo.get_kline.return_value = fake_df_rows
        api_main.app.dependency_overrides[deps.get_stock_repository] = lambda: fake_repo

        r = client.get("/api/data/cn/ticker/000001.SZ/kline?days=10")
        assert r.status_code == 200
        body = r.json()
        assert "data" in body and len(body["data"]) == 1
        assert body["data"][0]["close"] == 10.2
        fake_repo.get_kline.assert_called_once_with(
            ticker="000001.SZ", market="cn", days=10
        )

    def test_ticker_names_rejects_invalid_market(self, client, temp_project_root):
        # Validation failure
        r = client.get("/api/data/xx/ticker-names")
        assert r.status_code == 400

    def test_ticker_names_success_empty_when_no_cache(self, client, temp_project_root, monkeypatch):
        # Success / edge case: no local JSON cache, market='us' has no online
        # fallback in _load_ticker_names, so an empty mapping is returned.
        # Clear the in-process cache so the test is deterministic.
        monkeypatch.setattr(data_router, "_ticker_names_cache", {})
        r = client.get("/api/data/us/ticker-names")
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 0
        assert body["names"] == {}


# ===========================================================================
# notes router
# ===========================================================================
class TestNotesRouter:
    def test_add_note_success_returns_id(self, client, notes_db):
        # Success
        r = client.post(
            "/api/notes",
            json={"ticker": "600000.SH", "content": "bullish breakout"},
        )
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body.get("id"), int) and body["id"] > 0

    def test_add_note_missing_body_is_422(self, client, notes_db):
        # Validation failure
        r = client.post("/api/notes")
        assert r.status_code == 422

    def test_add_note_missing_required_field_is_422(self, client, notes_db):
        # Validation failure: content is required on NoteCreate.
        r = client.post("/api/notes", json={"ticker": "600000.SH"})
        assert r.status_code == 422

    def test_get_ticker_context_success(self, client, notes_db):
        # Arrange — add a note first
        client.post("/api/notes", json={"ticker": "600000.SH", "content": "ctx note"})
        # Act
        r = client.get("/api/notes/ticker/600000.SH")
        # Assert — context returns the documented shape.
        assert r.status_code == 200
        body = r.json()
        assert body["ticker"] == "600000.SH"
        assert body["note_count_total"] == 1
        assert len(body["notes"]) == 1
        assert body["notes"][0]["content"] == "ctx note"

    def test_search_success(self, client, notes_db):
        # Arrange
        client.post("/api/notes", json={"ticker": "600000.SH", "content": "breakout rally"})
        # Act
        r = client.get("/api/notes/search?q=breakout")
        # Assert
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) == 1
        assert results[0]["ticker"] == "600000.SH"

    def test_search_missing_q_is_422(self, client, notes_db):
        # Validation failure: q is required (Query(..., min_length=1)).
        r = client.get("/api/notes/search")
        assert r.status_code == 422

    def test_search_empty_q_is_422(self, client, notes_db):
        # Validation failure: min_length=1 rejects empty string.
        r = client.get("/api/notes/search?q=")
        assert r.status_code == 422

    def test_recent_notes_success(self, client, notes_db):
        # Arrange
        client.post("/api/notes", json={"ticker": "600000.SH", "content": "recent note"})
        # Act
        r = client.get("/api/notes/recent?days=1")
        # Assert
        assert r.status_code == 200
        results = r.json()["results"]
        assert any(n["ticker"] == "600000.SH" for n in results)

    def test_tracked_tickers_success(self, client, notes_db):
        # Arrange
        client.post("/api/notes", json={"ticker": "600000.SH", "content": "t1"})
        # Act
        r = client.get("/api/notes/tracked")
        # Assert
        assert r.status_code == 200
        tickers = r.json()["tickers"]
        assert any(t["ticker"] == "600000.SH" for t in tickers)

    def test_delete_note_success_returns_200(self, client, notes_db):
        # Bug A contract: DELETE on an existing active note returns 200.
        # Arrange
        add_r = client.post("/api/notes", json={"ticker": "600000.SH", "content": "to delete"})
        note_id = add_r.json()["id"]
        # Act
        r = client.delete(f"/api/notes/{note_id}")
        # Assert
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    def test_delete_note_404_when_not_found(self, client, notes_db):
        # Bug A contract: DELETE on a non-existent id returns 404.
        r = client.delete("/api/notes/9999999")
        assert r.status_code == 404

    def test_delete_note_404_after_double_delete(self, client, notes_db):
        # Edge case: soft-deleted note is no longer "active" -> second delete 404.
        add_r = client.post("/api/notes", json={"ticker": "600000.SH", "content": "x"})
        note_id = add_r.json()["id"]
        assert client.delete(f"/api/notes/{note_id}").status_code == 200
        assert client.delete(f"/api/notes/{note_id}").status_code == 404

    def test_deleted_note_hidden_from_search(self, client, notes_db):
        # Edge case: soft-delete hides the note from search/recent/tracked.
        add_r = client.post(
            "/api/notes", json={"ticker": "600000.SH", "content": "unique-token-xyz"}
        )
        note_id = add_r.json()["id"]
        assert client.delete(f"/api/notes/{note_id}").status_code == 200
        # Search no longer finds it.
        assert client.get("/api/notes/search?q=unique-token-xyz").json()["results"] == []
        # Tracked tickers no longer list it.
        tracked = client.get("/api/notes/tracked").json()["tickers"]
        assert not any(t["ticker"] == "600000.SH" for t in tracked)


# ===========================================================================
# macro router
# ===========================================================================
class TestMacroRouter:
    def test_list_reports_empty_when_db_absent(self, client, temp_project_root):
        # Edge case: no research DB -> 200 with empty list (graceful).
        r = client.get("/api/macro/reports")
        assert r.status_code == 200
        assert r.json() == {"reports": []}

    def test_list_reports_success(self, client, temp_project_root):
        # Success
        _make_research_db(temp_project_root)
        r = client.get("/api/macro/reports")
        assert r.status_code == 200
        reports = r.json()["reports"]
        assert len(reports) == 1
        assert reports[0]["risk_signal"] == "risk-on"

    def test_latest_report_404_when_db_absent(self, client, temp_project_root):
        # Edge case: no DB -> 404 "no reports".
        r = client.get("/api/macro/reports/latest")
        assert r.status_code == 404

    def test_latest_report_success(self, client, temp_project_root):
        # Success
        _make_research_db(temp_project_root)
        r = client.get("/api/macro/reports/latest")
        assert r.status_code == 200
        assert r.json()["content"] == "macro body"

    def test_get_report_404_when_not_found(self, client, temp_project_root):
        # Edge case: DB present, id absent -> 404.
        _make_research_db(temp_project_root)
        r = client.get("/api/macro/reports/9999999")
        assert r.status_code == 404

    def test_get_report_success(self, client, temp_project_root):
        # Success — the seeded macro report has id=1.
        _make_research_db(temp_project_root)
        r = client.get("/api/macro/reports/1")
        assert r.status_code == 200
        assert r.json()["id"] == 1

    def test_run_macro_accepts_empty_body(self, client):
        # The /api/macro/run endpoint accepts an empty MacroRunRequest (all
        # fields optional) and returns a 200 SSE stream. We do NOT consume the
        # stream body (it spawns a yfinance + LLM background thread); we only
        # assert the request is accepted and an EventSource response begins.
        # Use stream=True so TestClient does not block on the full SSE body.
        with client.stream("POST", "/api/macro/run", json={}) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")


# ===========================================================================
# analysis router
# ===========================================================================
class TestAnalysisRouter:
    def test_list_reports_empty_when_db_absent(self, client, temp_project_root):
        # Edge case
        r = client.get("/api/analysis/reports")
        assert r.status_code == 200
        assert r.json() == {"reports": []}

    def test_list_reports_success(self, client, temp_project_root):
        # Success
        _make_research_db(temp_project_root)
        r = client.get("/api/analysis/reports")
        assert r.status_code == 200
        reports = r.json()["reports"]
        assert len(reports) == 1
        assert reports[0]["title"] == "industry report"

    def test_get_report_404_when_not_found(self, client, temp_project_root):
        # Edge case: DB present, id absent -> 404.
        _make_research_db(temp_project_root)
        r = client.get("/api/analysis/reports/9999999")
        assert r.status_code == 404

    def test_get_report_success(self, client, temp_project_root):
        # Success — the seeded research report has id=1.
        _make_research_db(temp_project_root)
        r = client.get("/api/analysis/reports/1")
        assert r.status_code == 200
        assert r.json()["id"] == 1


# ===========================================================================
# config router
# ===========================================================================
class TestConfigRouter:
    def test_get_config_empty_when_file_absent(self, client, temp_project_root):
        # Edge case: no models_config.json in the temp root -> {}.
        r = client.get("/api/config")
        assert r.status_code == 200
        assert r.json() == {}

    def test_get_config_success(self, client, temp_project_root):
        # Success — write a models_config.json into the temp root.
        (temp_project_root / "models_config.json").write_text(
            json.dumps({"profiles": []}), encoding="utf-8"
        )
        r = client.get("/api/config")
        assert r.status_code == 200
        assert r.json() == {"profiles": []}

    def test_get_settings_empty_when_file_absent(self, client, temp_project_root):
        # Edge case
        r = client.get("/api/config/settings")
        assert r.status_code == 200
        assert r.json() == {}

    def test_update_settings_success(self, client, temp_project_root):
        # Success — PUT writes user_settings.json in the temp root.
        r = client.put("/api/config/settings", json={"tdx_path": str(temp_project_root)})
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["settings"]["tdx_path"] == str(temp_project_root)
        # The file was actually written.
        written = json.loads(
            (temp_project_root / "user_settings.json").read_text(encoding="utf-8")
        )
        assert written["tdx_path"] == str(temp_project_root)

    def test_update_settings_missing_body_is_422(self, client, temp_project_root):
        # Validation failure
        r = client.put("/api/config/settings")
        assert r.status_code == 422

    def test_validate_tdx_missing_body_is_422(self, client, temp_project_root):
        # Validation failure
        r = client.post("/api/config/validate-tdx")
        assert r.status_code == 422

    def test_validate_tdx_400_when_path_missing(self, client, temp_project_root):
        # Validation failure / edge: tdx_path required -> 400 when absent.
        r = client.post("/api/config/validate-tdx", json={})
        assert r.status_code == 400

    def test_validate_tdx_invalid_path_returns_valid_false(self, client, temp_project_root):
        # Edge case: a path with no vipdoc dir -> 200 valid=False (not an error).
        bogus = temp_project_root / "no-vipdoc-here"
        bogus.mkdir()
        r = client.post("/api/config/validate-tdx", json={"tdx_path": str(bogus)})
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is False
        assert "message" in body

    def test_validate_tdx_valid_path_returns_valid_true(self, client, temp_project_root):
        # Success — create a fake vipdoc dir.
        fake_tdx = temp_project_root / "fake_tdx"
        (fake_tdx / "vipdoc").mkdir(parents=True)
        r = client.post("/api/config/validate-tdx", json={"tdx_path": str(fake_tdx)})
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is True
        assert body["vipdoc_path"].endswith("vipdoc")
