"""Unit tests for SQLiteNoteRepository (S004-001).

Tests the INoteRepository port implementation backed by SQLiteConnection.
All tests use a temp-file SQLite database — no external network calls.
Soft-delete behavior mirrors the legacy ``src/ai_analysis/stock_notes.py``
contract.
"""
import os
import tempfile

import pytest

from doge.core.ports.repository import INoteRepository
from doge.infrastructure.database.repositories import SQLiteNoteRepository
from doge.infrastructure.database.sqlite import SQLiteConnection


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def repo():
    """Return a SQLiteNoteRepository with a temp-file DB and schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = SQLiteConnection(db_path, use_row_factory=True)
    with conn.connect() as raw_conn:
        raw_conn.execute(
            """CREATE TABLE stock_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                market TEXT NOT NULL DEFAULT 'cn',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                note_type TEXT,
                title TEXT,
                content TEXT,
                tags TEXT,
                price_at_note REAL,
                source TEXT,
                sentiment TEXT,
                deleted_at TIMESTAMP
            )"""
        )
        raw_conn.commit()
    yield SQLiteNoteRepository(conn=conn)
    os.unlink(db_path)


@pytest.fixture
def repo_with_stock_names():
    """Return a repo with both stock_notes and stock_names tables."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = SQLiteConnection(db_path, use_row_factory=True)
    with conn.connect() as raw_conn:
        raw_conn.execute(
            """CREATE TABLE stock_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                market TEXT NOT NULL DEFAULT 'cn',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                note_type TEXT,
                title TEXT,
                content TEXT,
                tags TEXT,
                price_at_note REAL,
                source TEXT,
                sentiment TEXT,
                deleted_at TIMESTAMP
            )"""
        )
        raw_conn.execute(
            """CREATE TABLE stock_names (
                ticker TEXT PRIMARY KEY,
                name_cn TEXT,
                name_en TEXT,
                sector TEXT,
                industry TEXT
            )"""
        )
        raw_conn.execute(
            "INSERT INTO stock_names VALUES (?, ?, ?, ?, ?)",
            ("000001.SZ", "平安银行", "Ping An Bank", "金融", "银行业"),
        )
        raw_conn.commit()
    yield SQLiteNoteRepository(conn=conn)
    os.unlink(db_path)


# ---------------------------------------------------------------------------
# Port-contract tests
# ---------------------------------------------------------------------------
def test_sqlite_note_repository_implements_port():
    """SQLiteNoteRepository is a concrete INoteRepository."""
    assert issubclass(SQLiteNoteRepository, INoteRepository)


# ---------------------------------------------------------------------------
# add_note
# ---------------------------------------------------------------------------
def test_add_note_returns_positive_id(repo):
    """add_note persists a row and returns a positive integer id."""
    note_id = repo.add_note("000001.SZ", "Bullish on earnings")
    assert isinstance(note_id, int)
    assert note_id > 0


def test_add_note_stores_all_fields(repo):
    """add_note stores ticker, content, tags, source, sentiment, market, note_type, title, price_at_note."""
    repo.add_note(
        ticker="AAPL",
        note_text="Strong Q3 guidance",
        tags="earnings,tech",
        source="manual",
        sentiment="bullish",
        market="us",
        note_type="research",
        title="Q3 Report",
        price_at_note=150.0,
    )
    rows = repo.get_notes(ticker="AAPL")
    assert len(rows) == 1
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["content"] == "Strong Q3 guidance"
    assert rows[0]["tags"] == "earnings,tech"
    assert rows[0]["source"] == "manual"
    assert rows[0]["sentiment"] == "bullish"
    assert rows[0]["market"] == "us"
    assert rows[0]["note_type"] == "research"
    assert rows[0]["title"] == "Q3 Report"
    assert rows[0]["price_at_note"] == 150.0


# ---------------------------------------------------------------------------
# get_notes
# ---------------------------------------------------------------------------
def test_get_notes_all_tickers(repo):
    """get_notes without ticker returns notes for all tickers."""
    repo.add_note("T1", "note 1")
    repo.add_note("T2", "note 2")
    rows = repo.get_notes()
    assert len(rows) == 2
    assert {r["ticker"] for r in rows} == {"T1", "T2"}


def test_get_notes_filtered_by_ticker(repo):
    """get_notes(ticker=...) restricts to that ticker."""
    repo.add_note("T1", "note 1")
    repo.add_note("T2", "note 2")
    rows = repo.get_notes(ticker="T1")
    assert len(rows) == 1
    assert rows[0]["ticker"] == "T1"


def test_get_notes_orders_newest_first(repo):
    """get_notes returns rows ordered by created_at DESC."""
    repo.add_note("T", "older")
    repo.add_note("T", "newer")
    rows = repo.get_notes(ticker="T")
    assert len(rows) == 2
    assert rows[0]["content"] == "newer"
    assert rows[1]["content"] == "older"


# ---------------------------------------------------------------------------
# delete_note (soft delete)
# ---------------------------------------------------------------------------
def test_delete_note_returns_true_when_row_exists(repo):
    """delete_note returns True when the note exists and is active."""
    nid = repo.add_note("T", "to delete")
    assert repo.delete_note(nid) is True


def test_delete_note_returns_false_when_no_row(repo):
    """delete_note returns False when note_id does not exist."""
    assert repo.delete_note(99999) is False


def test_delete_note_hides_from_get_notes(repo):
    """Soft-deleted notes are excluded from get_notes."""
    nid = repo.add_note("T", "to delete")
    repo.delete_note(nid)
    rows = repo.get_notes(ticker="T")
    assert len(rows) == 0


def test_delete_note_idempotent_second_call_returns_false(repo):
    """Deleting an already-deleted note returns False."""
    nid = repo.add_note("T", "to delete")
    assert repo.delete_note(nid) is True
    assert repo.delete_note(nid) is False


def test_get_notes_include_deleted_shows_soft_deleted(repo):
    """get_notes(include_deleted=True) reveals soft-deleted rows."""
    nid = repo.add_note("T", "to delete")
    repo.delete_note(nid)
    rows = repo.get_notes(ticker="T", include_deleted=True)
    assert len(rows) == 1
    assert rows[0]["deleted_at"] is not None


# ---------------------------------------------------------------------------
# search_notes
# ---------------------------------------------------------------------------
def test_search_notes_matches_content(repo):
    """search_notes finds notes by content substring."""
    repo.add_note("T", "alpha beta gamma")
    repo.add_note("T", "delta epsilon")
    rows = repo.search_notes("beta")
    assert len(rows) == 1
    assert rows[0]["content"] == "alpha beta gamma"


def test_search_notes_excludes_deleted(repo):
    """search_notes does not match soft-deleted notes."""
    nid = repo.add_note("T", "alpha beta gamma")
    repo.delete_note(nid)
    rows = repo.search_notes("beta")
    assert len(rows) == 0


def test_search_notes_matches_title(repo):
    """search_notes finds notes by title substring."""
    # The schema has a title column; we insert via raw SQL to set it
    with repo._conn.connect() as conn:
        conn.execute(
            "INSERT INTO stock_notes (ticker, title, content) VALUES (?, ?, ?)",
            ("T", "Quarterly Report", "content body"),
        )
        conn.commit()
    rows = repo.search_notes("Quarterly")
    assert len(rows) == 1
    assert rows[0]["title"] == "Quarterly Report"


def test_search_notes_respects_limit(repo):
    """search_notes respects the limit parameter."""
    for i in range(5):
        repo.add_note("T", f"note {i}")
    rows = repo.search_notes("note", limit=3)
    assert len(rows) == 3


# ---------------------------------------------------------------------------
# get_recent_notes
# ---------------------------------------------------------------------------
def test_get_recent_notes_limits_results(repo):
    """get_recent_notes respects the limit parameter."""
    for i in range(5):
        repo.add_note("T", f"note {i}")
    rows = repo.get_recent_notes(days=1, limit=3)
    assert len(rows) == 3


def test_get_recent_notes_orders_newest_first(repo):
    """get_recent_notes returns newest notes first."""
    repo.add_note("T", "first")
    repo.add_note("T", "second")
    rows = repo.get_recent_notes(days=1, limit=2)
    assert rows[0]["content"] == "second"
    assert rows[1]["content"] == "first"


def test_get_recent_notes_excludes_deleted(repo):
    """get_recent_notes excludes soft-deleted notes."""
    nid = repo.add_note("T", "to delete")
    repo.delete_note(nid)
    rows = repo.get_recent_notes(days=1, limit=10)
    assert len(rows) == 0


# ---------------------------------------------------------------------------
# list_tracked_tickers
# ---------------------------------------------------------------------------
def test_list_tracked_tickers_returns_distinct_tickers(repo):
    """list_tracked_tickers returns each ticker with active notes once."""
    repo.add_note("A", "note A")
    repo.add_note("A", "note A2")
    repo.add_note("B", "note B")
    tickers = repo.list_tracked_tickers()
    assert len(tickers) == 2
    assert all(isinstance(t, dict) for t in tickers)
    assert any(t["ticker"] == "A" and t["n"] == 2 for t in tickers)
    assert any(t["ticker"] == "B" and t["n"] == 1 for t in tickers)


def test_list_tracked_tickers_excludes_deleted_notes(repo):
    """Tickers with only soft-deleted notes are omitted."""
    nid = repo.add_note("A", "note A")
    repo.delete_note(nid)
    tickers = repo.list_tracked_tickers()
    assert tickers == []


# ---------------------------------------------------------------------------
# get_ticker_with_context
# ---------------------------------------------------------------------------
def test_get_ticker_with_context_returns_basic_shape(repo):
    """get_ticker_with_context returns the expected key set."""
    repo.add_note("T", "note 1")
    ctx = repo.get_ticker_with_context("T", market="cn")
    assert ctx["ticker"] == "T"
    assert ctx["market"] == "cn"
    assert ctx["note_count_total"] == 1
    assert len(ctx["notes"]) == 1


def test_get_ticker_with_context_no_notes(repo):
    """get_ticker_with_context handles a ticker with no notes."""
    ctx = repo.get_ticker_with_context("UNKNOWN", market="us")
    assert ctx["ticker"] == "UNKNOWN"
    assert ctx["market"] == "us"
    assert ctx["note_count_total"] == 0
    assert ctx["notes"] == []


def test_get_ticker_with_context_includes_name_and_sector(repo_with_stock_names):
    """get_ticker_with_context populates name/sector from stock_names."""
    repo_with_stock_names.add_note("000001.SZ", "note")
    ctx = repo_with_stock_names.get_ticker_with_context("000001.SZ", market="cn")
    assert ctx["name_cn"] == "平安银行"
    assert ctx["name_en"] == "Ping An Bank"
    assert ctx["sector"] == "金融"
    assert ctx["industry"] == "银行业"
    assert ctx["note_count_total"] == 1


def test_get_ticker_with_context_excludes_deleted_notes(repo):
    """Soft-deleted notes do not count toward note_count_total or notes list."""
    nid = repo.add_note("T", "to delete")
    repo.add_note("T", "keep")
    repo.delete_note(nid)
    ctx = repo.get_ticker_with_context("T", market="cn")
    assert ctx["note_count_total"] == 1
    assert len(ctx["notes"]) == 1
    assert ctx["notes"][0]["content"] == "keep"


# ---------------------------------------------------------------------------
# No raw sqlite3 usage in the adapter
# ---------------------------------------------------------------------------
def test_repository_source_contains_no_raw_connect():
    """The adapter file must not contain raw ``sqlite3.connect`` calls."""
    import inspect
    from pathlib import Path

    mod = __import__("doge.infrastructure.database.repositories", fromlist=[""])
    source = Path(inspect.getfile(mod)).read_text(encoding="utf-8")
    # The SQLiteNoteRepository class itself should not use raw connect
    # (the SQLiteConnection adapter is the only sqlite3.connect site).
    class_start = source.find("class SQLiteNoteRepository")
    class_end = source.find("class SQLiteSchemaBrowser")
    if class_end == -1:
        class_end = len(source)
    class_body = source[class_start:class_end]
    assert "sqlite3.connect" not in class_body, (
        "SQLiteNoteRepository must not use raw sqlite3.connect; "
        "route all DB access through SQLiteConnection."
    )
