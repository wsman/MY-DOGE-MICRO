import sqlite3
from concurrent.futures import ThreadPoolExecutor

from doge.infrastructure.database.agent_repositories import SQLiteRunQueue


def _latest_queue_row(db, run_id: str):
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM run_queue WHERE run_id = ? ORDER BY queue_id DESC LIMIT 1",
            (run_id,),
        ).fetchone()


def test_run_queue_claim_atomic_allows_only_one_worker(tmp_path):
    db = tmp_path / "agent_state.db"
    SQLiteRunQueue(db).enqueue("run-1")

    def claim(worker_id):
        return SQLiteRunQueue(db).claim_atomic(worker_id, lease_seconds=30)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(claim, ["worker-a", "worker-b"]))

    assert sorted(item for item in results if item is not None) == ["run-1"]
    assert results.count(None) == 1
    latest = _latest_queue_row(db, "run-1")
    assert latest["status"] == "running"
    assert latest["worker_id"] in {"worker-a", "worker-b"}
    assert latest["attempt_count"] == 1


def test_run_queue_release_claim_records_final_status(tmp_path):
    db = tmp_path / "agent_state.db"
    queue = SQLiteRunQueue(db)
    queue.enqueue("run-1")
    assert queue.claim_atomic("worker-a", lease_seconds=30) == "run-1"

    queue.release_claim("run-1", "worker-a", "done")

    latest = _latest_queue_row(db, "run-1")
    assert latest["status"] == "done"
    assert latest["worker_id"] == "worker-a"
    assert queue.list_pending() == []


def test_run_queue_recovers_expired_leases(tmp_path):
    db = tmp_path / "agent_state.db"
    queue = SQLiteRunQueue(db)
    queue.enqueue("run-1")
    assert queue.claim_atomic("worker-a", lease_seconds=-1) == "run-1"

    recovered = queue.recover_stalled_leases(lease_timeout_seconds=0)

    assert recovered == ["run-1"]
    assert queue.list_pending() == ["run-1"]
    latest = _latest_queue_row(db, "run-1")
    assert latest["status"] == "queued"


def test_run_queue_heartbeat_extends_active_lease(tmp_path):
    db = tmp_path / "agent_state.db"
    queue = SQLiteRunQueue(db)
    queue.enqueue("run-1")
    assert queue.claim_atomic("worker-a", lease_seconds=1) == "run-1"
    before = _latest_queue_row(db, "run-1")["lease_expires_at"]

    queue.heartbeat("worker-a", "run-1", lease_seconds=30)

    after = _latest_queue_row(db, "run-1")["lease_expires_at"]
    assert after > before


def test_run_queue_moves_exhausted_stalled_claim_to_dead_letter(tmp_path):
    db = tmp_path / "agent_state.db"
    queue = SQLiteRunQueue(db)
    queue.enqueue("run-1")
    assert queue.claim_atomic("worker-a", lease_seconds=-1, max_attempts=2) == "run-1"
    assert queue.recover_stalled_leases(lease_timeout_seconds=0, max_attempts=2) == ["run-1"]
    assert queue.claim_atomic("worker-b", lease_seconds=-1, max_attempts=2) == "run-1"

    recovered = queue.recover_stalled_leases(lease_timeout_seconds=0, max_attempts=2)

    latest = _latest_queue_row(db, "run-1")
    assert recovered == []
    assert latest["status"] == "dead_letter"
    assert latest["attempt_count"] == 2
    assert queue.list_pending() == []
