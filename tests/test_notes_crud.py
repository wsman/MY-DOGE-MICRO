"""Round-trip CRUD tests for the stock_notes research insight store.

Reverse-documents the live module ``src/ai_analysis/stock_notes.py`` and
guards BUG A: the DELETE route previously imported a non-existent
``delete_note`` (ImportError on first call). These tests pin the soft-delete
contract added in that fix.

Isolation: each test points ``stock_notes.NOTES_DB`` at a throwaway temp
SQLite file containing a freshly-created ``stock_notes`` table (with the
``deleted_at`` soft-delete column), so no live DB and no network are touched.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

# Make src/ importable without depending on package install state.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_analysis import stock_notes  # noqa: E402


# Live schema as observed in data/research_insights.db (see CDD §4.1).
SCHEMA_SQL = """
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


@pytest.fixture
def notes_db(tmp_path, monkeypatch):
    """A temp SQLite file with a fresh stock_notes table; module global redirected.

    Mirrors the temp-DB fixture pattern used across the test suite
    (see tests/test_database.py, tests/test_yfinance_adapter.py): no live DB,
    no network, fully deterministic.
    """
    db_path = tmp_path / "test_research_insights.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()

    # Redirect the module-level constant used by _notes_conn().
    monkeypatch.setattr(stock_notes, "NOTES_DB", str(db_path))
    return str(db_path)


# ---------------------------------------------------------------------------
# Round-trip CRUD
# ---------------------------------------------------------------------------
class TestNotesRoundTrip:
    def test_add_get_search_recent_delete_round_trip(self, notes_db):
        # Arrange — add a note
        note_id = stock_notes.add_note(
            "600000.SH", "Bullish breakout above MA60",
            market="cn", title="MA60 cross", tags="ta",
        )
        assert isinstance(note_id, int) and note_id > 0

        # Act — per-ticker get
        got = stock_notes.get_notes("600000.SH")
        # Assert
        assert len(got) == 1
        assert got[0]["id"] == note_id
        assert got[0]["content"] == "Bullish breakout above MA60"
        assert got[0]["deleted_at"] is None

        # Act — keyword search hits it
        hits = stock_notes.search_notes("breakout")
        assert len(hits) == 1
        assert hits[0]["ticker"] == "600000.SH"

        # Act — recent notes include it
        recent = stock_notes.get_recent_notes(days=1)
        assert any(r["ticker"] == "600000.SH" for r in recent)

        # Act — tracked ticker list shows it with count=1
        tracked = stock_notes.list_tracked_tickers()
        assert any(t["ticker"] == "600000.SH" and t["n"] == 1 for t in tracked)

        # Act — soft delete
        deleted = stock_notes.delete_note(note_id)
        # Assert — exactly one row affected
        assert deleted is True

        # Act — re-query after delete: hidden everywhere
        assert stock_notes.get_notes("600000.SH") == []
        assert stock_notes.search_notes("breakout") == []
        recent_after = stock_notes.get_recent_notes(days=1)
        assert not any(r["ticker"] == "600000.SH" for r in recent_after)
        tracked_after = stock_notes.list_tracked_tickers()
        assert not any(t["ticker"] == "600000.SH" for t in tracked_after)

        # Assert — row still physically present (soft delete)
        conn = sqlite3.connect(notes_db)
        row = conn.execute(
            "SELECT deleted_at FROM stock_notes WHERE id = ?", (note_id,)
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] is not None  # deleted_at timestamp was set


# ---------------------------------------------------------------------------
# BUG A regression — delete_note exists and soft-delete contract holds
# ---------------------------------------------------------------------------
class TestDeleteNoteContract:
    def test_delete_note_exists_and_is_callable(self, notes_db):
        # BUG A regression: delete_note MUST be importable & callable.
        # The old router raised ImportError on first call.
        assert callable(stock_notes.delete_note)

    def test_delete_missing_id_returns_false(self, notes_db):
        # Edge case: deleting an id that never existed.
        deleted = stock_notes.delete_note(999999)
        assert deleted is False

    def test_delete_double_delete_second_returns_false(self, notes_db):
        # Edge case: double delete — second call finds no *active* row.
        note_id = stock_notes.add_note("000001.SZ", "first note")
        assert stock_notes.delete_note(note_id) is True
        assert stock_notes.delete_note(note_id) is False

    def test_delete_one_note_keeps_others_visible(self, notes_db):
        # Edge case: deleting one note does not hide siblings for same ticker.
        nid_a = stock_notes.add_note("600000.SH", "note A")
        nid_b = stock_notes.add_note("600000.SH", "note B")
        assert stock_notes.delete_note(nid_a) is True
        remaining = stock_notes.get_notes("600000.SH")
        assert len(remaining) == 1
        assert remaining[0]["id"] == nid_b

    def test_get_ticker_with_context_hides_deleted_notes(self, notes_db):
        # Cross-check the context query path also filters soft-deleted rows.
        nid = stock_notes.add_note("600000.SH", "context note")
        ctx_before = stock_notes.get_ticker_with_context("600000.SH", "cn")
        assert ctx_before["note_count_total"] == 1
        assert len(ctx_before["notes"]) == 1

        assert stock_notes.delete_note(nid) is True
        ctx_after = stock_notes.get_ticker_with_context("600000.SH", "cn")
        assert ctx_after["note_count_total"] == 0
        assert ctx_after["notes"] == []


# ---------------------------------------------------------------------------
# Migration idempotency
# ---------------------------------------------------------------------------
class TestDeletedAtMigration:
    def test_ensure_deleted_at_column_is_idempotent(self, tmp_path, monkeypatch):
        # Arrange — a DB where the table exists WITHOUT the deleted_at column
        # (simulates the pre-fix live schema).
        db_path = tmp_path / "legacy_research_insights.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript("""
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
        """)
        conn.commit()
        conn.close()

        monkeypatch.setattr(stock_notes, "NOTES_DB", str(db_path))

        # Act — add_note triggers the read-path migration; delete_note adds it again
        note_id = stock_notes.add_note("600000.SH", "legacy note")
        # First delete triggers _ensure_deleted_at_column (idempotent, no error)
        assert stock_notes.delete_note(note_id) is True

        # Assert — column now present, repeated calls do not error
        conn = sqlite3.connect(str(db_path))
        cols = {r[1] for r in conn.execute("PRAGMA table_info(stock_notes)")}
        conn.close()
        assert "deleted_at" in cols

        # Act — second delete_note on the (now deleted) row runs the migration
        # again against a schema that already has the column; must not raise.
        assert stock_notes.delete_note(note_id) is False
