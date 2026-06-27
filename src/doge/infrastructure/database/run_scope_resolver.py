"""SQLite implementation of IRunScopeResolver."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from doge.config import get_settings
from doge.core.ports.run_scope_resolver import IRunScopeResolver
from doge.infrastructure.database.migration_runner import apply_context_migrations
from doge.infrastructure.database.sqlite import SQLiteConnection
from doge.infrastructure.database.tenant_guard import LOCAL_TENANT_ID
from doge.shared.scope import TenantScope


def _schema_path() -> Path:
    return Path(__file__).resolve().parent / "agent_schema.sql"


def _bootstrap_schema(db_path: Path) -> None:
    import sqlite3
    from doge.core.domain.agent_models import utc_now

    db_path.parent.mkdir(parents=True, exist_ok=True)
    sql = _schema_path().read_text(encoding="utf-8")
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(sql)
        apply_context_migrations(conn)
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(name, applied_at) VALUES (?, ?)",
            ("agent_schema_v1", utc_now()),
        )
        conn.commit()


def _row_value(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


class SQLiteRunScopeResolver(IRunScopeResolver):
    """Resolve run scope by reading the run header's tenant metadata directly.

    This lookup intentionally does not take a caller scope: the worker must be
    able to discover a run's tenant before it can issue scoped runtime calls.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        _bootstrap_schema(self._db_path)
        self._connection = SQLiteConnection(self._db_path, use_row_factory=True)

    def resolve_scope(self, run_id: str) -> TenantScope:
        with self._connection.connect() as conn:
            row = conn.execute(
                "SELECT tenant_id, identity_snapshot FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                return TenantScope.local()

            tenant_id = _row_value(row, "tenant_id")
            if tenant_id is None or tenant_id == LOCAL_TENANT_ID:
                return TenantScope.local()

            user_hash: str | None = None
            snapshot_json = _row_value(row, "identity_snapshot")
            if snapshot_json:
                try:
                    snapshot = json.loads(snapshot_json)
                    if isinstance(snapshot, dict):
                        user_hash = snapshot.get("user_hash")
                except (json.JSONDecodeError, TypeError):
                    pass

            return TenantScope.enterprise(str(tenant_id), user_hash)
