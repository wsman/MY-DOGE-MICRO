"""SQLite repository for Slot Platform signing-key revocations."""

from __future__ import annotations

from pathlib import Path

from doge.config import get_settings
from doge.core.ports.slot_signing_repository import (
    ISlotSigningRepository,
    SlotSignerRevocation,
)
from doge.infrastructure.database.agent_repositories import bootstrap_agent_schema
from doge.infrastructure.database.sqlite import SQLiteConnection


class SQLiteSlotSigningRepository(ISlotSigningRepository):
    """Persist revoked slot publisher keys in the local agent database."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)
        self._connection = SQLiteConnection(self._db_path, use_row_factory=True)

    def _connect(self):
        return self._connection.connect()

    def is_revoked(self, key_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM slot_signer_revocations WHERE key_id = ?",
                (key_id,),
            ).fetchone()
        return row is not None

    def revoke(
        self,
        key_id: str,
        *,
        reason: str | None = None,
        actor_hash: str | None = None,
    ) -> SlotSignerRevocation:
        key_id = key_id.strip()
        if not key_id:
            raise ValueError("key_id is required")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO slot_signer_revocations(key_id, reason, actor_hash)
                VALUES (?, ?, ?)
                ON CONFLICT(key_id) DO UPDATE SET
                    reason = excluded.reason,
                    actor_hash = excluded.actor_hash
                """,
                (key_id, reason, actor_hash),
            )
            conn.commit()
            row = conn.execute(
                """
                SELECT key_id, revoked_at, reason, actor_hash
                FROM slot_signer_revocations
                WHERE key_id = ?
                """,
                (key_id,),
            ).fetchone()
        return _revocation_from_row(row)

    def list_revoked(self) -> tuple[SlotSignerRevocation, ...]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT key_id, revoked_at, reason, actor_hash
                FROM slot_signer_revocations
                ORDER BY key_id
                """
            ).fetchall()
        return tuple(_revocation_from_row(row) for row in rows)


def _revocation_from_row(row) -> SlotSignerRevocation:
    return SlotSignerRevocation(
        key_id=row["key_id"],
        revoked_at=row["revoked_at"],
        reason=row["reason"],
        actor_hash=row["actor_hash"],
    )
