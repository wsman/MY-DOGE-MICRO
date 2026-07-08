from __future__ import annotations

import sqlite3

from doge.infrastructure.database.slot_activation_repository import SQLiteSlotActivationRepository


def test_slot_activation_repository_round_trips_singleton_state(tmp_path) -> None:
    repo = SQLiteSlotActivationRepository(tmp_path / "agent_state.db")

    assert repo.get_active().active is False

    activated = repo.set_active("bundle.local_analyst", "actor-a")

    assert activated.active is True
    assert activated.bundle_id == "bundle.local_analyst"
    assert activated.actor_hash == "actor-a"
    assert activated.activated_at
    assert repo.get_active() == activated


def test_slot_activation_repository_overwrites_and_clears_idempotently(tmp_path) -> None:
    db = tmp_path / "agent_state.db"
    repo = SQLiteSlotActivationRepository(db)

    repo.set_active("bundle.local_analyst", "actor-a")
    repo.set_active("bundle.daemon_operator", "actor-b")

    active = repo.get_active()
    assert active.bundle_id == "bundle.daemon_operator"
    assert active.actor_hash == "actor-b"

    assert repo.clear().active is False
    assert repo.clear().active is False
    assert repo.get_active().active is False

    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT id, bundle_id FROM slot_activation_state").fetchall()
    assert rows == [(1, None)]
