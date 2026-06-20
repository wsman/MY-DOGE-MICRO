import pytest

from doge.application.agent.worker import AsyncioWorker
from doge.core.domain.agent_models import RunStatus


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
    def __init__(self):
        self.runs = {}

    def get_run(self, run_id: str):
        return self.runs.get(run_id)


class FakeSessions:
    pass


class FakeUnitOfWork:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.calls = []

    async def enqueue_run_and_turn(self, **kwargs):
        self.calls.append(kwargs)
        return self.run_id


def test_worker_recover_pending_enqueues_stranded_runs():
    queue = FakeRunQueue()
    queue.pending = ["run-a", "run-b"]
    worker = AsyncioWorker(FakeRuntime(), FakeSessions(), queue, FakeIdempotencyStore())

    worker.recover()
    worker.recover()

    assert worker._queue.qsize() == 2


@pytest.mark.asyncio
async def test_worker_delegates_enqueue_to_unit_of_work():
    runtime = FakeRuntime()
    runtime.runs["run-existing"] = type("Run", (), {"status": RunStatus.COMPLETED})()
    unit_of_work = FakeUnitOfWork("run-existing")
    worker = AsyncioWorker(
        runtime,
        FakeSessions(),
        FakeRunQueue(),
        FakeIdempotencyStore(),
        unit_of_work,
    )

    run_id = await worker.enqueue_run("ses-1", "Analyze", idempotency_key="key-1")

    assert run_id == "run-existing"
    assert unit_of_work.calls[0]["session_id"] == "ses-1"
    assert unit_of_work.calls[0]["message"] == "Analyze"
    assert unit_of_work.calls[0]["idempotency_key"] == "key-1"
    await worker.stop()
