import asyncio

import pytest

from doge.application.agent.worker import AsyncioWorker
from doge.core.domain.agent_models import RunStatus


from doge.shared.scope import TenantScope


class FakeScopeResolver:
    def __init__(self, scopes=None):
        self.scopes = scopes or {}

    def resolve_scope(self, run_id: str):
        return self.scopes.get(run_id, TenantScope.local())


class FakeRunQueue:
    def __init__(self):
        self.pending = []
        self.statuses = []

    def enqueue(self, run_id: str) -> None:
        self.statuses.append((run_id, "queued"))

    def dequeue(self):
        return self.pending.pop(0) if self.pending else None

    def claim_atomic(self, worker_id: str, lease_seconds: int):
        return self.pending.pop(0) if self.pending else None

    def heartbeat(self, worker_id: str, run_id: str, lease_seconds: int) -> None:
        self.statuses.append((run_id, "heartbeat"))

    def release_claim(self, run_id: str, worker_id: str, final_status: str) -> None:
        self.statuses.append((run_id, final_status))

    def recover_stalled_leases(self, lease_timeout_seconds: int):
        return []

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

    def get_run(self, scope, run_id: str | None = None):
        if run_id is None:
            run_id = scope
        return self.runs.get(run_id)


class ProcessingRuntime(FakeRuntime):
    def __init__(self):
        super().__init__()
        self.processed = []
        self.processed_scopes = []

    async def run_to_pause_or_completion(self, scope, run_id: str | None = None):
        if run_id is None:
            run_id = scope
        self.processed.append(run_id)
        self.processed_scopes.append(scope)
        return type("Run", (), {"status": RunStatus.COMPLETED})()


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


def test_worker_polls_durable_queue_without_local_signal():
    asyncio.run(_exercise_worker_polling_without_local_signal())


async def _exercise_worker_polling_without_local_signal() -> None:
    queue = FakeRunQueue()
    runtime = ProcessingRuntime()
    worker = AsyncioWorker(
        runtime,
        FakeSessions(),
        queue,
        FakeIdempotencyStore(),
        poll_interval_seconds=0.01,
    )
    worker.start()
    queue.pending.append("run-external")

    try:
        await asyncio.wait_for(_wait_until_processed(runtime), timeout=1.0)
    finally:
        await asyncio.wait_for(worker.stop(), timeout=2.0)

    assert runtime.processed == ["run-external"]
    assert ("run-external", "done") in queue.statuses


@pytest.mark.asyncio
async def test_api_mode_enqueue_does_not_auto_start_worker_loop():
    runtime = FakeRuntime()
    runtime.runs["run-queued"] = type("Run", (), {"status": RunStatus.QUEUED})()
    unit_of_work = FakeUnitOfWork("run-queued")
    worker = AsyncioWorker(
        runtime,
        FakeSessions(),
        FakeRunQueue(),
        FakeIdempotencyStore(),
        unit_of_work,
        auto_start=False,
    )

    run_id = await worker.enqueue_run("ses-1", "Analyze")

    assert run_id == "run-queued"
    assert worker.is_running() is False
    assert worker._queue.qsize() == 0


async def _wait_until_processed(runtime: ProcessingRuntime) -> None:
    while not runtime.processed:
        await asyncio.sleep(0.01)


def test_worker_uses_enterprise_scope_for_enterprise_run():
    asyncio.run(_exercise_worker_enterprise_scope())


async def _exercise_worker_enterprise_scope() -> None:
    queue = FakeRunQueue()
    runtime = ProcessingRuntime()
    enterprise_scope = TenantScope.enterprise("tenant-a", "user-hash-a")
    resolver = FakeScopeResolver({"run-enterprise": enterprise_scope})
    worker = AsyncioWorker(
        runtime,
        FakeSessions(),
        queue,
        FakeIdempotencyStore(),
        scope_resolver=resolver,
        poll_interval_seconds=0.01,
    )
    worker.start()
    queue.pending.append("run-enterprise")

    try:
        await asyncio.wait_for(_wait_until_processed(runtime), timeout=1.0)
    finally:
        await asyncio.wait_for(worker.stop(), timeout=2.0)

    assert runtime.processed == ["run-enterprise"]
    assert len(runtime.processed_scopes) == 1
    scope = runtime.processed_scopes[0]
    assert scope.tenant_id == "tenant-a"
    assert scope.subject_hash == "user-hash-a"
    assert scope.tenant_id != "local"
