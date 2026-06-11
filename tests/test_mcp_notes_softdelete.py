"""Regression tests for the MCP stock_overview soft-delete consistency fix.

Guards the Phase-2 consistency fix documented in CDD module #8:
``mcp_server.py`` previously read ``stock_notes`` with a raw
``SELECT ... WHERE ticker=?`` that did NOT filter ``deleted_at IS NULL``.
Module #7 (research-insight-knowledge-base) soft-deletes notes by setting a
nullable ``deleted_at`` timestamp and hiding such rows from every read path.
The MCP tool was the one consumer that leaked soft-deleted notes.

These tests pin the fixed behaviour:
  * soft-deleted notes are excluded from the ``stock_overview`` note count and list
  * the count and list stay correct when the ``deleted_at`` column is absent
    (pre-migration legacy DB) — the fix must not break the legacy schema path.

Isolation: every test redirects ``mcp_server.RESEARCH_DB`` at a throwaway temp
SQLite file and replaces the DuckDB price path with a stub so no live market DB
and no network are touched. Fully deterministic.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import mcp_server as srv  # noqa: E402


# Live schema minus deleted_at (the pre-Phase-2 legacy shape).
SCHEMA_NO_SOFTDELETE = """
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


@pytest.fixture
def stub_price_path(monkeypatch):
    """Neutralise the DuckDB price block so only the notes block is exercised.

    ``stock_overview`` opens a DuckDB read for recent prices; in this isolated
    test there is no market DB. We stub ``get_duckdb_connection`` to raise, which
    the handler swallows into a benign ``价格查询失败`` line — the notes block
    still runs and is what we assert on.
    """

    class _Boom:
        def __enter__(self):
            raise RuntimeError("price path stubbed for unit test")

        def __exit__(self, *a):
            return False

    def _boom(*a, **kw):
        return _Boom()

    monkeypatch.setattr(srv, "get_duckdb_connection", _boom)


# ---------------------------------------------------------------------------
# Soft-delete leak fix — the load-bearing regression
# ---------------------------------------------------------------------------
class TestStockOverviewSoftDeleteLeak:
    @pytest.mark.asyncio
    async def test_soft_deleted_note_excluded_from_count_and_list(
        self, tmp_path, monkeypatch, stub_price_path
    ):
        # Arrange — temp research DB with the soft-delete column, one active +
        # one soft-deleted note for the same ticker.
        db_path = tmp_path / "research_insights.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_WITH_SOFTDELETE)
        conn.commit()
        conn.close()
        _seed_two_notes(str(db_path), with_softdelete=True)
        monkeypatch.setattr(srv, "RESEARCH_DB", db_path)

        # Act
        result = await srv.stock_overview("600000", "cn")

        # Assert — count reflects only the active note; the retracted note is
        # invisible to the MCP consumer.
        assert "ACTIVE note visible to the operator" in result
        assert "RETRACTED note the operator deleted" not in result
        # The "(N 条)" count line must show exactly 1, not 2.
        assert "笔记 (1 条)" in result
        assert "笔记 (2 条)" not in result

    @pytest.mark.asyncio
    async def test_legacy_schema_without_deleted_at_still_works(
        self, tmp_path, monkeypatch, stub_price_path
    ):
        # Arrange — pre-Phase-2 legacy schema has no deleted_at column. The fix
        # must detect its absence and skip the predicate (no OperationalError).
        db_path = tmp_path / "research_insights_legacy.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_NO_SOFTDELETE)
        conn.commit()
        conn.close()
        _seed_two_notes(str(db_path), with_softdelete=False)
        monkeypatch.setattr(srv, "RESEARCH_DB", db_path)

        # Act — must not raise OperationalError on the missing column.
        result = await srv.stock_overview("600000", "cn")

        # Assert — the single legacy note is surfaced, count is 1.
        assert "ACTIVE note visible to the operator" in result
        assert "笔记 (1 条)" in result

    @pytest.mark.asyncio
    async def test_no_notes_shows_empty_marker(
        self, tmp_path, monkeypatch, stub_price_path
    ):
        # Arrange — soft-delete schema, zero rows for the ticker.
        db_path = tmp_path / "research_insights_empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_WITH_SOFTDELETE)
        conn.commit()
        conn.close()
        monkeypatch.setattr(srv, "RESEARCH_DB", db_path)

        # Act
        result = await srv.stock_overview("999999.SH", "cn")

        # Assert — the documented empty marker is shown.
        assert "暂无笔记" in result
