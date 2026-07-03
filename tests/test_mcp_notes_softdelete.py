"""Regression tests for the MCP stock_overview soft-delete consistency fix.

Guards the Phase-2 consistency fix (CDD module #7 §3.3 / #8) on the live MCP
``stock_overview`` path. Since Sprint 020 the six MCP data tools dispatch
through the shared ``ToolRegistry`` (``doge.application.tools``); the tool bodies
live in ``src/doge/interfaces/mcp/server.py``. Notes are an MCP presentation
enrichment read via the ``INoteRepository`` port (``get_ticker_with_context``),
which is where the soft-delete filtering now lives.

History: ``stock_overview`` previously read ``stock_notes`` with a raw
``SELECT ... WHERE ticker=?`` that did NOT filter ``deleted_at IS NULL``.
Module #7 (research-insight-knowledge-base) soft-deletes notes by setting a
nullable ``deleted_at`` timestamp and hiding such rows from every read path.
The repository port now applies dynamic ``PRAGMA table_info`` detection + the
``AND deleted_at IS NULL`` predicate.

These tests pin the fixed behaviour:
  * soft-deleted notes are excluded from the ``stock_overview`` note count/list
  * the count and list stay correct when ``deleted_at`` is absent (legacy DB)
  * the empty marker is shown when there are no notes

Isolation: every test redirects ``get_settings().db.research_db`` at a throwaway
temp SQLite file (via ``DOGE_RESEARCH_DB`` env + ``reset_settings()``) and stubs
``srv._execute_data_tool`` so the registry overview returns an empty payload (no
DuckDB market data, no network). The notes block reads the temp SQLite DB
through the note repository, so only the soft-delete behaviour is exercised.
"""
import os
import sqlite3
from pathlib import Path

import pytest

from doge.config.settings import get_settings, reset_settings
from doge.interfaces.mcp import server as srv


# Live schema minus deleted_at (the pre-Phase-2 legacy shape).
# stock_names is included (empty) because the note repository reads name/sector
# and notes; a missing stock_names would raise OperationalError and swallow the
# notes read with it.
SCHEMA_NO_SOFTDELETE = """
CREATE TABLE stock_names (
    ticker TEXT PRIMARY KEY,
    name_cn TEXT,
    sector TEXT
);
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
    source TEXT DEFAULT 'user'
);
"""

# Live schema with the Phase-2 soft-delete column (post-migration shape).
SCHEMA_WITH_SOFTDELETE = """
CREATE TABLE stock_names (
    ticker TEXT PRIMARY KEY,
    name_cn TEXT,
    sector TEXT
);
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


def _seed_two_notes(db_path: str, *, with_softdelete: bool) -> None:
    """Insert one active and one soft-deleted note for ticker 600000.SH."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO stock_notes (ticker, market, created_at, content, source) "
        "VALUES (?, 'cn', '2026-06-10 09:30:00', ?, 'user')",
        ("600000.SH", "ACTIVE note visible to the operator"),
    )
    if with_softdelete:
        conn.execute(
            "INSERT INTO stock_notes (ticker, market, created_at, content, source, deleted_at) "
            "VALUES (?, 'cn', '2026-06-09 09:30:00', ?, 'user', '2026-06-09 18:00:00')",
            ("600000.SH", "RETRACTED note the operator deleted"),
        )
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def _isolate_settings():
    """Reset the settings singleton around every test."""
    yield
    os.environ.pop("DOGE_RESEARCH_DB", None)
    reset_settings()


@pytest.fixture
def stub_overview(monkeypatch):
    """Neutralise the registry overview so only the notes block is exercised.

    The converged ``stock_overview`` fetches its overview payload through the
    shared ToolRegistry; in this isolated test there is no market DB. Stub
    ``srv._execute_data_tool`` so the overview is empty (no prices rendered)
    while the notes block (the asserted surface) still reads the temp DB.
    """

    class _FakeResult:
        ok = True
        data = {}

    async def _fake(name, arguments):
        return _FakeResult()

    monkeypatch.setattr(srv, "_execute_data_tool", _fake)


# ---------------------------------------------------------------------------
# Soft-delete leak fix — the load-bearing regression (live MCP path)
# ---------------------------------------------------------------------------
class TestStockOverviewSoftDeleteLeak:
    @pytest.mark.asyncio
    async def test_soft_deleted_note_excluded_from_count_and_list(
        self, tmp_path, monkeypatch, stub_overview
    ):
        # Arrange — temp research DB with the soft-delete column, one active +
        # one soft-deleted note for the same ticker.
        db_path = tmp_path / "research_insights.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_WITH_SOFTDELETE)
        conn.commit()
        conn.close()
        _seed_two_notes(str(db_path), with_softdelete=True)
        monkeypatch.setenv("DOGE_RESEARCH_DB", str(db_path))
        reset_settings()
        assert get_settings().db.research_db == Path(str(db_path))

        # Act — live MCP stock_overview (registry-backed, notes via the port).
        result = await srv.stock_overview("600000", "cn")

        # Assert — count reflects only the active note; the retracted note is
        # invisible to the MCP consumer.
        assert "ACTIVE note visible to the operator" in result
        assert "RETRACTED note the operator deleted" not in result
        assert "笔记 (1 条)" in result
        assert "笔记 (2 条)" not in result

    @pytest.mark.asyncio
    async def test_legacy_schema_without_deleted_at_still_works(
        self, tmp_path, monkeypatch, stub_overview
    ):
        # Arrange — pre-Phase-2 legacy schema has no deleted_at column. The fix
        # must detect its absence and skip the predicate (no OperationalError).
        db_path = tmp_path / "research_insights_legacy.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_NO_SOFTDELETE)
        conn.commit()
        conn.close()
        _seed_two_notes(str(db_path), with_softdelete=False)
        monkeypatch.setenv("DOGE_RESEARCH_DB", str(db_path))
        reset_settings()
        assert get_settings().db.research_db == Path(str(db_path))

        # Act — must not raise OperationalError on the missing column.
        result = await srv.stock_overview("600000", "cn")

        # Assert — the single legacy note is surfaced, count is 1.
        assert "ACTIVE note visible to the operator" in result
        assert "笔记 (1 条)" in result

    @pytest.mark.asyncio
    async def test_no_notes_shows_empty_marker(
        self, tmp_path, monkeypatch, stub_overview
    ):
        # Arrange — soft-delete schema, zero rows for the ticker.
        db_path = tmp_path / "research_insights_empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_WITH_SOFTDELETE)
        conn.commit()
        conn.close()
        monkeypatch.setenv("DOGE_RESEARCH_DB", str(db_path))
        reset_settings()
        assert get_settings().db.research_db == Path(str(db_path))

        # Act
        result = await srv.stock_overview("999999.SH", "cn")

        # Assert — the documented empty marker is shown.
        assert "暂无笔记" in result
