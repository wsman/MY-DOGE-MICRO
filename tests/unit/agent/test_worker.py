import pytest

from doge.application.agent.worker import AsyncioWorker


class FakeRunQueue:
    def __init__(self):
        self.pending = []
        self.statuses = []

    def enqueue(self, run_id: str) -> None:
        self.statuses.append((run_id, "queued"))

    def dequeue(self):
        return self.pending.pop(0) if self.pending else None

    def list_pending(self):
        return list(self.pending)

    def append_status(self, run_id: str, status: str) -> None:
        self.statuses.append((run_id, status))

    def is_ready(self):
        return True


class FakeIdempotencyStore:
    def __init__(self):
        self.values = {}

    def get(self, key: str, scope: str):
        return self.values.get((key, scope))

    def set(self, key: str, scope: str, run_id: str) -> None:
        self.values[(key, scope)] = run_id


class FakeRuntime:
    pass


class FakeSessions:
    pass


def test_worker_recover_pending_enqueues_stranded_runs():
    queue = FakeRunQueue()
    queue.pending = ["run-a", "run-b"]
    worker = AsyncioWorker(FakeRuntime(), FakeSessions(), queue, FakeIdempotencyStore())

    worker.recover()
    worker.recover()

    assert worker._queue.qsize() == 2


@pytest.mark.asyncio
async def test_worker_idempotency_returns_existing_run_id():
    idempotency = FakeIdempotencyStore()
    idempotency.set("key-1", "ses-1", "run-existing")
    worker = AsyncioWorker(FakeRuntime(), FakeSessions(), FakeRunQueue(), idempotency)

    run_id = await worker.enqueue_run("ses-1", "Analyze", idempotency_key="key-1")

    assert run_id == "run-existing"
