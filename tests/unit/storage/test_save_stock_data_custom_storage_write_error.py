"""Unit tests for the StorageWriteError error-surfacing half of TR-006.

Covers ``src/micro/database.py::save_stock_data_custom``:
- success path appends rows (no exception)
- PK violation surfaces as StorageWriteError (regression for the bug at
  market-data-storage.md:220 ``except Exception: pass swallows it``)
- missing/unwritable db surfaces as StorageWriteError (not silently passed)
- the original cause is chained via ``__cause__``
- the function body contains no bare ``except Exception: pass`` (TR-006 grep gate)
- a failure emits an ERROR-level log record naming the ticker and cause
"""
import ast
import logging
import sqlite3
import textwrap
from pathlib import Path

import pandas as pd
import pytest

from doge.core.ports.repository import StorageWriteError

# src/micro/database.py imports sibling modules (tdx_loader, database, ...)
# via plain ``from database import ...`` and ``sys.path`` manipulation.
# Add src/micro to sys.path so the import resolves in the test process.
MICRO_DIR = Path(__file__).resolve().parents[3] / "src" / "micro"
import sys

if str(MICRO_DIR) not in sys.path:
    sys.path.insert(0, str(MICRO_DIR))

from database import save_stock_data_custom  # noqa: E402  (sys.path setup above)


# ── Utility ───────────────────────────────────────────────────────────────

def inspect_getsource(func):
    """Return source text of ``func`` (wrapper around inspect.getsource)."""
    import inspect

    return inspect.getsource(func)


# ── Helpers / fixtures ────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS stock_prices (
    ticker TEXT,
    date TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    amount REAL,
    PRIMARY KEY (ticker, date)
)
"""


def _make_frame(ticker: str = "000001.SZ", rows: int = 3) -> pd.DataFrame:
    """Build a small OHLCV frame with the expected columns."""
    return pd.DataFrame(
        {
            "ticker": [ticker] * rows,
            "date": [f"2026-01-0{i}" for i in range(1, rows + 1)],
            "open": [10.0 + i for i in range(rows)],
            "high": [11.0 + i for i in range(rows)],
            "low": [9.0 + i for i in range(rows)],
            "close": [10.5 + i for i in range(rows)],
            "volume": [1000 * (i + 1) for i in range(rows)],
            "amount": [10000.0 * (i + 1) for i in range(rows)],
        }
    )


def _init_db(db_path: Path) -> None:
    """Create the stock_prices table in a fresh sqlite file."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _count_rows(db_path: Path, ticker: str) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute(
            "SELECT COUNT(*) FROM stock_prices WHERE ticker = ?", (ticker,)
        )
        return int(cur.fetchone()[0])
    finally:
        conn.close()


# ── Tests ─────────────────────────────────────────────────────────────────

class TestWriteSuccessAppendsRows:
    def test_write_success_appends_rows(self, tmp_path):
        # Arrange
        db_path = tmp_path / "market.db"
        _init_db(db_path)
        frame = _make_frame(rows=3)

        # Act — must not raise
        save_stock_data_custom(frame, str(db_path), retention_days=730)

        # Assert
        assert _count_rows(db_path, "000001.SZ") == 3


class TestWritePkViolationRaisesStorageWriteError:
    def test_write_pk_violation_raises_storage_write_error(self, tmp_path):
        """Regression for market-data-storage.md:220 — IntegrityError surfaces.

        The legacy incremental path filters rows with ``date > MAX(date)``, so
        to force a genuine PK violation through ``to_sql`` we write a frame
        that ITSELF contains two rows with the same (ticker, date) against a
        fresh DB (no max_existing → append path hits the duplicate).
        """
        # Arrange — fresh DB (no existing rows → takes the else/append branch).
        db_path = tmp_path / "market.db"
        _init_db(db_path)

        # Frame with a duplicate (ticker, date) — to_sql append violates the PK.
        frame = pd.DataFrame(
            {
                "ticker": ["000001.SZ", "000001.SZ"],
                "date": ["2026-01-01", "2026-01-01"],  # duplicate PK
                "open": [10.0, 10.0],
                "high": [11.0, 11.0],
                "low": [9.0, 9.0],
                "close": [10.5, 10.5],
                "volume": [1000, 1000],
                "amount": [10000.0, 10000.0],
            }
        )

        # Act + Assert — the legacy IntegrityError must now surface as StorageWriteError
        with pytest.raises(StorageWriteError):
            save_stock_data_custom(frame, str(db_path), retention_days=730)


class TestWriteToMissingDbDirRaisesStorageWriteError:
    def test_write_to_missing_db_dir_raises_storage_write_error(self, tmp_path, monkeypatch):
        # Arrange — point db_path at a directory that does not exist and force
        # get_db_connection to raise (simulates an unwritable location).
        bad_path = str(tmp_path / "no_such_dir" / "market.db")

        import database as db_module

        def _boom(_path=None):
            raise OSError("simulated unwritable path")

        monkeypatch.setattr(db_module, "get_db_connection", _boom)

        # Act + Assert
        with pytest.raises(StorageWriteError):
            save_stock_data_custom(
                _make_frame(), bad_path, retention_days=730
            )


class TestStorageWriteErrorPreservesCause:
    def test_storage_write_error_preserves_cause(self, tmp_path, monkeypatch):
        # Arrange — force a known underlying exception and confirm chaining.
        import database as db_module

        sentinel = sqlite3.OperationalError("simulated underlying failure")

        def _boom(_path=None):
            raise sentinel

        monkeypatch.setattr(db_module, "get_db_connection", _boom)

        # Act
        with pytest.raises(StorageWriteError) as exc_info:
            save_stock_data_custom(
                _make_frame(), str(tmp_path / "market.db"), retention_days=730
            )

        # Assert — __cause__ is the original exception (raise ... from e)
        assert exc_info.value.__cause__ is sentinel


class TestNoBareExceptPassInSaveStockDataCustom:
    def test_no_bare_except_pass_in_save_stock_data_custom(self):
        """TR-006 grep gate: the function body must not swallow exceptions.

        Walks the AST of save_stock_data_custom and asserts that no
        ``except`` handler has a body consisting solely of a ``pass`` (the
        legacy swallowed pattern).
        """
        # Arrange — load the function source and parse it.
        src = textwrap.dedent(inspect_getsource(save_stock_data_custom))
        tree = ast.parse(src)

        swallows = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                body = node.body
                # A bare `except: pass` or `except X: pass` is a single Pass node
                if len(body) == 1 and isinstance(body[0], ast.Pass):
                    swallows.append(node)

        # Assert
        assert swallows == [], (
            f"save_stock_data_custom contains bare 'except: pass' handler(s): {swallows}"
        )


class TestStorageWriteErrorIsLogged:
    def test_storage_write_error_is_logged(self, tmp_path, caplog, monkeypatch):
        # Arrange — force a write failure and capture log records.
        import database as db_module

        def _boom(_path=None):
            raise sqlite3.OperationalError("logged-cause-marker")

        monkeypatch.setattr(db_module, "get_db_connection", _boom)

        # Act
        with caplog.at_level(logging.ERROR, logger="database"):
            with pytest.raises(StorageWriteError):
                save_stock_data_custom(
                    _make_frame(ticker="LOGME.SZ"),
                    str(tmp_path / "market.db"),
                    retention_days=730,
                )

        # Assert — at least one ERROR record naming the ticker and the cause.
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert error_records, "expected at least one ERROR log record on write failure"
        joined = " ".join(r.getMessage() for r in error_records)
        assert "LOGME.SZ" in joined, f"ERROR log must name the ticker; got: {joined}"
        assert "logged-cause-marker" in joined, (
            f"ERROR log must include the underlying cause text; got: {joined}"
        )
