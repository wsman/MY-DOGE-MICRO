"""Round-trip CRUD tests for the stock_notes research insight store.

Reverse-documents the canonical note workflow via
``doge.application.use_cases.manage_notes``. These tests isolate the research
DB by setting ``DOGE_RESEARCH_DB`` and resetting the settings singleton, so no
live DB and no network are touched.
"""
import sqlite3

import pytest

from doge.application.composition import build_manage_notes_use_case
from doge.application.contracts.request import ManageNoteRequest


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
    """A temp SQLite file with a fresh stock_notes table; settings redirected.

    Mirrors the settings-based isolation pattern used in ``tests/test_api_routers.py``.
    """
    db_path = tmp_path / "test_research_insights.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()

    monkeypatch.setenv("DOGE_RESEARCH_DB", str(db_path))
    from doge.config import settings as settings_module
    settings_module.reset_settings()

    yield str(db_path)

    settings_module.reset_settings()
    monkeypatch.delenv("DOGE_RESEARCH_DB", raising=False)


def _uc():
    return build_manage_notes_use_case()


# ---------------------------------------------------------------------------
# Round-trip CRUD
# ---------------------------------------------------------------------------
class TestNotesRoundTrip:
    def test_add_get_search_recent_delete_round_trip(self, notes_db):
        # Arrange — add a note
        resp = _uc().execute(
            ManageNoteRequest(
                operation="add",
                ticker="600000.SH",
                note_text="Bullish breakout above MA60",
                market="cn",
                title="MA60 cross",
                tags="ta",
            )
        )
        note_id = resp.note_id
        assert isinstance(note_id, int) and note_id > 0

        # Act — per-ticker get
        got = _uc().execute(
            ManageNoteRequest(operation="get_notes", ticker="600000.SH")
        ).notes
        # Assert
        assert len(got) == 1
        assert got[0]["id"] == note_id
        assert got[0]["content"] == "Bullish breakout above MA60"
        assert got[0]["deleted_at"] is None

        # Act — keyword search hits it
        hits = _uc().execute(
            ManageNoteRequest(operation="search", keyword="breakout")
        ).notes
        assert len(hits) == 1
        assert hits[0]["ticker"] == "600000.SH"

        # Act — recent notes include it
        recent = _uc().execute(
            ManageNoteRequest(operation="recent", days=1)
        ).notes
        assert any(r["ticker"] == "600000.SH" for r in recent)

        # Act — tracked ticker list shows it with count=1
        tracked = _uc().execute(
            ManageNoteRequest(operation="tracked")
        ).notes
        assert any(t["ticker"] == "600000.SH" and t["n"] == 1 for t in tracked)

        # Act — soft delete
        deleted = _uc().execute(
            ManageNoteRequest(operation="delete", note_id=note_id)
        ).success
        # Assert — exactly one row affected
        assert deleted is True

        # Act — re-query after delete: hidden everywhere
        assert _uc().execute(
            ManageNoteRequest(operation="get_notes", ticker="600000.SH")
        ).notes == []
        assert _uc().execute(
            ManageNoteRequest(operation="search", keyword="breakout")
        ).notes == []
        recent_after = _uc().execute(
            ManageNoteRequest(operation="recent", days=1)
        ).notes
        assert not any(r["ticker"] == "600000.SH" for r in recent_after)
        tracked_after = _uc().execute(
            ManageNoteRequest(operation="tracked")
        ).notes
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
        # BUG A regression: delete_note MUST be callable via use case.
        resp = _uc().execute(ManageNoteRequest(operation="delete", note_id=1))
        assert resp.success is False

    def test_delete_missing_id_returns_false(self, notes_db):
        # Edge case: deleting an id that never existed.
        resp = _uc().execute(
            ManageNoteRequest(operation="delete", note_id=999999)
        )
        assert resp.success is False

    def test_delete_double_delete_second_returns_false(self, notes_db):
        # Edge case: double delete — second call finds no *active* row.
        note_id = _uc().execute(
            ManageNoteRequest(
                operation="add", ticker="000001.SZ", note_text="first note"
            )
        ).note_id
        assert _uc().execute(
            ManageNoteRequest(operation="delete", note_id=note_id)
        ).success is True
        assert _uc().execute(
            ManageNoteRequest(operation="delete", note_id=note_id)
        ).success is False

    def test_delete_one_note_keeps_others_visible(self, notes_db):
        # Edge case: deleting one note does not hide siblings for same ticker.
        nid_a = _uc().execute(
            ManageNoteRequest(
                operation="add", ticker="600000.SH", note_text="note A"
            )
        ).note_id
        nid_b = _uc().execute(
            ManageNoteRequest(
                operation="add", ticker="600000.SH", note_text="note B"
            )
        ).note_id
        assert _uc().execute(
            ManageNoteRequest(operation="delete", note_id=nid_a)
        ).success is True
        remaining = _uc().execute(
            ManageNoteRequest(operation="get_notes", ticker="600000.SH")
        ).notes
        assert len(remaining) == 1
        assert remaining[0]["id"] == nid_b

    def test_get_ticker_with_context_hides_deleted_notes(self, notes_db):
        # Cross-check the context query path also filters soft-deleted rows.
        nid = _uc().execute(
            ManageNoteRequest(
                operation="add", ticker="600000.SH", note_text="context note"
            )
        ).note_id
        ctx_before = _uc().execute(
            ManageNoteRequest(
                operation="get_context", ticker="600000.SH", market="cn"
            )
        ).context
        assert ctx_before["note_count_total"] == 1
        assert len(ctx_before["notes"]) == 1

        assert _uc().execute(
            ManageNoteRequest(operation="delete", note_id=nid)
        ).success is True
        ctx_after = _uc().execute(
            ManageNoteRequest(
                operation="get_context", ticker="600000.SH", market="cn"
            )
        ).context
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

        monkeypatch.setenv("DOGE_RESEARCH_DB", str(db_path))
        from doge.config import settings as settings_module
        settings_module.reset_settings()

        # Act — add_note triggers the read-path migration; delete_note adds it again
        note_id = _uc().execute(
            ManageNoteRequest(
                operation="add", ticker="600000.SH", note_text="legacy note"
            )
        ).note_id
        # First delete triggers _ensure_deleted_at_column (idempotent, no error)
        assert _uc().execute(
            ManageNoteRequest(operation="delete", note_id=note_id)
        ).success is True

        # Assert — column now present, repeated calls do not error
        conn = sqlite3.connect(str(db_path))
        cols = {r[1] for r in conn.execute("PRAGMA table_info(stock_notes)")}
        conn.close()
        assert "deleted_at" in cols

        # Act — second delete_note on the (now deleted) row runs the migration
        # again against a schema that already has the column; must not raise.
        assert _uc().execute(
            ManageNoteRequest(operation="delete", note_id=note_id)
        ).success is False

        settings_module.reset_settings()
        monkeypatch.delenv("DOGE_RESEARCH_DB", raising=False)
