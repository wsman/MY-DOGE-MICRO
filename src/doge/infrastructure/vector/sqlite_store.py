"""SQLite vector store for local-first RAG retrieval."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from doge.config import get_settings
from doge.core.ports.vector_store import IVectorStore, VectorRecord, VectorSearchResult
from doge.infrastructure.database.agent_repositories import bootstrap_agent_schema
from doge.infrastructure.database.sqlite import SQLiteConnection


class SQLiteVectorStore(IVectorStore):
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)
        self._connection = SQLiteConnection(self._db_path, use_row_factory=True)

    def _connect(self):
        return self._connection.connect()

    def upsert(self, records: list[VectorRecord]) -> None:
        with self._connect() as conn:
            for record in records:
                conn.execute(
                    """
                    INSERT INTO vector_entries(record_id, vector, text, metadata, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(record_id) DO UPDATE SET
                        vector = excluded.vector,
                        text = excluded.text,
                        metadata = excluded.metadata,
                        updated_at = excluded.updated_at
                    """,
                    (
                        record.record_id,
                        json.dumps(record.vector),
                        record.text,
                        json.dumps(record.metadata, ensure_ascii=False),
                    ),
                )
            conn.commit()

    def search(
        self,
        vector: list[float],
        *,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM vector_entries").fetchall()
        results: list[VectorSearchResult] = []
        for row in rows:
            metadata = json.loads(row["metadata"] or "{}")
            if metadata_filter and not _matches_filter(metadata, metadata_filter):
                continue
            record = VectorRecord(
                record_id=row["record_id"],
                vector=json.loads(row["vector"]),
                text=row["text"],
                metadata=metadata,
            )
            results.append(VectorSearchResult(record=record, score=_cosine(vector, record.vector)))
        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]


def _matches_filter(metadata: dict[str, Any], metadata_filter: dict[str, Any]) -> bool:
    return all(metadata.get(key) == value for key, value in metadata_filter.items())


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
