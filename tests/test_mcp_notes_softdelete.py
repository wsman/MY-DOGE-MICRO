"""Regression tests for the MCP stock_overview soft-delete consistency fix.

Guards the Phase-2 consistency fix (CDD module #7 §3.3 / #8) on the **MODULAR
stock_overview** — the live MCP path
(``src/doge/interfaces/mcp/tools/query_stock.py``), reached via the composition
root ``build_stock_service`` + ``get_settings().db.research_db``. Batch-6
deleted the legacy monolith, so this regression guard protects the path
operators actually hit.

History: ``stock_overview`` previously read ``stock_notes`` with a raw
``SELECT ... WHERE ticker=?`` that did NOT filter ``deleted_at IS NULL``.
Module #7 (research-insight-knowledge-base) soft-deletes notes by setting a
nullable ``deleted_at`` timestamp and hiding such rows from every read path.
The MCP tool was the one consumer that leaked soft-deleted notes. The modular
tool replicates the fix (dynamic ``PRAGMA table_info`` detection + the
``AND deleted_at IS NULL`` predicate).

These tests pin the fixed behaviour:
  * soft-deleted notes are excluded from the ``stock_overview`` note count and list
  * the count and list stay correct when the ``deleted_at`` column is absent
    (pre-migration legacy DB) — the fix must not break the legacy schema path.

Isolation: every test redirects ``get_settings().db.research_db`` at a throwaway
temp SQLite file (via ``DOGE_RESEARCH_DB`` env + ``reset_settings()``) and
replaces the DuckDB price path (``build_stock_service``) with a stub returning
``{'prices': []}`` so no live market DB and no network are touched. Fully
deterministic.
"""
import os
import sqlite3
import sys
from pathlib import Path

import pytest

# The editable install resolves ``doge`` as a top-level package, so no sys.path
# shim is needed (Batch-1 removed them). ``pythonpath=["src"]`` in pyproject is
# sufficient for collection.
from doge.config.settings import get_settings, reset_settings  # noqa: E402

# Explicitly load the modular tool SUBMODULE. The package ``__init__``
# re-exports the ``query_stock``/``stock_overview`` FUNCTION names, which shadow
# the submodule attribute on the parent package, so a plain
# ``import ... as qs`` would bind the function, not the module. ``monkeypatch``
# needs the real module object to patch ``build_stock_service`` on it, so we
# trigger the import then pull the module back out of ``sys.modules``.
import doge.interfaces.mcp.tools.query_stock  # noqa: E402, F401
qs_module = sys.modules["doge.interfaces.mcp.tools.query_stock"]


# Live schema minus deleted_at (the pre-Phase-2 legacy shape).
# stock_names is included (empty) because the modular stock_overview reads
# name/sector and notes in ONE connection — a missing stock_names would raise
# OperationalError and swallow the notes read with it.
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
    """Reset the settings singleton around every test.

    Each test sets ``DOGE_RESEARCH_DB`` to point at its temp SQLite file and
    then calls ``reset_settings()`` so ``get_settings().db.research_db`` resolves
    to that file. This teardown clears any leftover env + singleton state so no
    test leaks the temp path into neighbours or the live process.
    """
    yield
    # Drop the override (if set) and reseal the singleton so the next test (or
    # the live process afterwards) re-reads real defaults.
    monkeypatch_env = os.environ.pop("DOGE_RESEARCH_DB", None)
    reset_settings()


@pytest.fixture
def stub_price_service(monkeypatch):
    """Neutralise the DuckDB price block so only the notes block is exercised.

    The modular ``stock_overview`` builds a ``StockService`` via the composition
    root (``build_stock_service``) for recent prices; in this isolated test
    there is no market DB. We stub ``build_stock_service`` on the modular tool
    module to return a fake service whose ``.overview(t, m)`` returns
    ``{'prices': []}``, so the price block renders nothing and the notes block
    (the asserted surface) still runs.
    """

    class _FakeStockService:
        def overview(self, ticker, market):
            return {"prices": []}

        def query(self, ticker, market, days):
            return []

    monkeypatch.setattr(qs_module, "build_stock_service", _FakeStockService)


# ---------------------------------------------------------------------------
# Soft-delete leak fix — the load-bearing regression (MODULAR live path)
# ---------------------------------------------------------------------------
class TestStockOverviewSoftDeleteLeak:
    @pytest.mark.asyncio
    async def test_soft_deleted_note_excluded_from_count_and_list(
        self, tmp_path, monkeypatch, stub_price_service
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

        # Act — modular stock_overview (the live MCP path).
        result = await qs_module.stock_overview("600000", "cn")

        # Assert — count reflects only the active note; the retracted note is
        # invisible to the MCP consumer.
        assert "ACTIVE note visible to the operator" in result
        assert "RETRACTED note the operator deleted" not in result
        # The "(N 条)" count line must show exactly 1, not 2.
        assert "笔记 (1 条)" in result
        assert "笔记 (2 条)" not in result

    @pytest.mark.asyncio
    async def test_legacy_schema_without_deleted_at_still_works(
        self, tmp_path, monkeypatch, stub_price_service
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
        result = await qs_module.stock_overview("600000", "cn")

        # Assert — the single legacy note is surfaced, count is 1.
        assert "ACTIVE note visible to the operator" in result
        assert "笔记 (1 条)" in result

    @pytest.mark.asyncio
    async def test_no_notes_shows_empty_marker(
        self, tmp_path, monkeypatch, stub_price_service
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
        result = await qs_module.stock_overview("999999.SH", "cn")

        # Assert — the documented empty marker is shown.
        assert "暂无笔记" in result
