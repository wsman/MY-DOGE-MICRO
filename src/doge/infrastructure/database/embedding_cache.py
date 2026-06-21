"""SQLite-backed embedding cache."""

from __future__ import annotations

import json
from pathlib import Path

from doge.config import get_settings
from doge.core.ports.embedding import IEmbeddingCache
from doge.infrastructure.database.agent_repositories import bootstrap_agent_schema
from doge.infrastructure.database.sqlite import SQLiteConnection


class SQLiteEmbeddingCache(IEmbeddingCache):
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)
        self._connection = SQLiteConnection(self._db_path, use_row_factory=True)

    def _connect(self):
        return self._connection.connect()

    def get(self, key: str) -> list[float] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT vector FROM embedding_cache WHERE key = ?", (key,)).fetchone()
            return json.loads(row["vector"]) if row else None

    def set(self, key: str, vector: list[float]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO embedding_cache(key, vector, created_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET vector = excluded.vector
                """,
                (key, json.dumps(vector)),
            )
            conn.commit()
