from __future__ import annotations

import sqlite3

from doge.infrastructure.database.slot_signing_repository import SQLiteSlotSigningRepository


def test_slot_signing_repository_records_revocations(tmp_path) -> None:
    repo = SQLiteSlotSigningRepository(tmp_path / "agent_state.db")

    assert repo.is_revoked("ops-key") is False

    revoked = repo.revoke("ops-key", reason="compromised", actor_hash="actor-a")

    assert revoked.key_id == "ops-key"
    assert revoked.reason == "compromised"
    assert revoked.actor_hash == "actor-a"
    assert revoked.revoked_at
    assert repo.is_revoked("ops-key") is True
    assert repo.list_revoked() == (revoked,)


def test_slot_signing_repository_revoke_is_idempotent(tmp_path) -> None:
    db = tmp_path / "agent_state.db"
    repo = SQLiteSlotSigningRepository(db)

    first = repo.revoke("ops-key", reason="first", actor_hash="actor-a")
    second = repo.revoke("ops-key", reason="second", actor_hash="actor-b")

    assert second.key_id == first.key_id
    assert second.revoked_at == first.revoked_at
    assert second.reason == "second"
    assert second.actor_hash == "actor-b"

    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT key_id, reason, actor_hash FROM slot_signer_revocations"
        ).fetchall()
    assert rows == [("ops-key", "second", "actor-b")]
