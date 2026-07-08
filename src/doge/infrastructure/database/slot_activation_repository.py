"""SQLite repository for persisted Slot Platform bundle activation."""

from __future__ import annotations

from pathlib import Path

from doge.config import get_settings
from doge.core.domain.agent_models import utc_now
from doge.core.ports.slot_activation_repository import (
    ISlotActivationRepository,
    SlotActivationRecord,
)
from doge.infrastructure.database.agent_repositories import bootstrap_agent_schema
from doge.infrastructure.database.sqlite import SQLiteConnection


class SQLiteSlotActivationRepository(ISlotActivationRepository):
    """Persist a single active bundle pointer in the local agent database."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)
        self._connection = SQLiteConnection(self._db_path, use_row_factory=True)

    def _connect(self):
        return self._connection.connect()

    def get_active(self) -> SlotActivationRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT bundle_id, activated_at, actor_hash
                FROM slot_activation_state
                WHERE id = 1
                """
            ).fetchone()
        if row is None or row["bundle_id"] is None:
            return SlotActivationRecord()
        return SlotActivationRecord(
            bundle_id=row["bundle_id"],
            activated_at=row["activated_at"],
            actor_hash=row["actor_hash"],
        )

    def set_active(self, bundle_id: str, actor_hash: str) -> SlotActivationRecord:
        activated_at = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO slot_activation_state(id, bundle_id, activated_at, actor_hash)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    bundle_id = excluded.bundle_id,
                    activated_at = excluded.activated_at,
                    actor_hash = excluded.actor_hash
                """,
                (bundle_id, activated_at, actor_hash),
            )
            conn.commit()
        return SlotActivationRecord(
            bundle_id=bundle_id,
            activated_at=activated_at,
            actor_hash=actor_hash,
        )

    def clear(self) -> SlotActivationRecord:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO slot_activation_state(id, bundle_id, activated_at, actor_hash)
                VALUES (1, NULL, NULL, NULL)
                ON CONFLICT(id) DO UPDATE SET
                    bundle_id = NULL,
                    activated_at = NULL,
                    actor_hash = NULL
                """
            )
            conn.commit()
        return SlotActivationRecord()
