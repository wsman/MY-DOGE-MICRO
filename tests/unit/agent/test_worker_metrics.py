import asyncio

import pytest

from doge.application.agent.worker import AsyncioWorker
from doge.core.domain.agent_models import RunStatus


class FakeRunQueue:
    def __init__(self):
        self.pending = []
        self.statuses = []

    def enqueue(self, run_id: str) -> None:
        self.pending.append(run_id)

    def claim_atomic(self, worker_id: str, lease_seconds: int):
        if self.pending:
            self.statuses.append((self.pending[0], "running"))
            return self.pending.pop(0)
        return None

    def heartbeat(self, worker_id: str, run_id: str, lease_seconds: int) -> None:
        self.statuses.append((run_id, "heartbeat"))

    def release_claim(self, run_id: str, worker_id: str, final_status: str) -> None:
        self.statuses.append((run_id, final_status))

    def recover_stalled_leases(self, lease_timeout_seconds: int):
        return []

    def list_pending(self):
        return list(self.pending)

    def is_ready(self):
        return True


class FakeRuntime:
    def __init__(self, status=RunStatus.COMPLETED, delay: float = 0.0, fail: bool = False):
        self.status = status
        self.delay = delay
        self.fail = fail
        self.failures = []

    def get_run(self, scope, run_id: str | None = None):
        return type("Run", (), {"status": RunStatus.QUEUED, "identity_snapshot": None})()

    async def run_to_pause_or_completion(self, scope, run_id: str | None = None):
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("boom")
        return type("Run", (), {"status": self.status})()

    async def record_failure(self, scope, run_id, message):
        self.failures.append((scope, run_id, message))


class FakeSessions:
    pass


class FakeIdempotencyStore:
    pass


def _worker(runtime, queue, *, poll_interval_seconds: float = 0.01):
    return AsyncioWorker(
        runtime,
        FakeSessions(),
        queue,
        FakeIdempotencyStore(),
        poll_interval_seconds=poll_interval_seconds,
        heartbeat_interval_seconds=0.01,
    )


def test_worker_metrics_initial_state():
    worker = _worker(FakeRuntime(), FakeRunQueue())

    assert worker.metrics() == {
        "runs_processed": 0,
        "runs_failed": 0,
        "runs_cancelled": 0,
        "avg_processing_latency_ms": 0,
        "last_heartbeat_at": None,
        "active_run_count": 0,
    }


@pytest.mark.asyncio
async def test_worker_metrics_records_successful_run():
    queue = FakeRunQueue()
    queue.pending.append("run-ok")
    worker = _worker(FakeRuntime(), queue)
    worker.start()

    try:
        await asyncio.wait_for(_wait_for_processed(worker, 1), timeout=1)
    finally:
        await worker.stop()

    metrics = worker.metrics()
    assert metrics["runs_processed"] == 1
    assert metrics["runs_failed"] == 0
    assert metrics["runs_cancelled"] == 0
    assert metrics["avg_processing_latency_ms"] >= 0


@pytest.mark.asyncio
async def test_worker_metrics_records_failed_run():
    queue = FakeRunQueue()
    queue.pending.append("run-fail")
    runtime = FakeRuntime(fail=True)
    worker = _worker(runtime, queue)
    worker.start()

    try:
        await asyncio.wait_for(_wait_for_processed(worker, 1), timeout=1)
    finally:
        await worker.stop()

    metrics = worker.metrics()
    assert metrics["runs_processed"] == 1
    assert metrics["runs_failed"] == 1
    assert runtime.failures[0][1] == "run-fail"


@pytest.mark.asyncio
async def test_worker_metrics_records_cancelled_run_status():
    queue = FakeRunQueue()
    queue.pending.append("run-cancelled")
    worker = _worker(FakeRuntime(status=RunStatus.CANCELLED), queue)
    worker.start()

    try:
        await asyncio.wait_for(_wait_for_processed(worker, 1), timeout=1)
    finally:
        await worker.stop()

    assert worker.metrics()["runs_cancelled"] == 1


@pytest.mark.asyncio
async def test_worker_metrics_reports_active_run_count():
    queue = FakeRunQueue()
    queue.pending.append("run-slow")
    worker = _worker(FakeRuntime(delay=0.1), queue)
    worker.start()

    try:
        await asyncio.wait_for(_wait_for_active(worker), timeout=1)
        assert worker.metrics()["active_run_count"] == 1
        await asyncio.wait_for(_wait_for_processed(worker, 1), timeout=1)
    finally:
        await worker.stop()


@pytest.mark.asyncio
async def test_worker_metrics_records_heartbeat_timestamp():
    queue = FakeRunQueue()
    queue.pending.append("run-heartbeat")
    worker = _worker(FakeRuntime(delay=0.05), queue)
    worker.start()

    try:
        await asyncio.wait_for(_wait_for_heartbeat(worker), timeout=1)
    finally:
        await worker.stop()

    assert worker.metrics()["last_heartbeat_at"] is not None


async def _wait_for_processed(worker: AsyncioWorker, count: int) -> None:
    while worker.metrics()["runs_processed"] < count:
        await asyncio.sleep(0.01)


async def _wait_for_active(worker: AsyncioWorker) -> None:
    while worker.metrics()["active_run_count"] == 0:
        await asyncio.sleep(0.01)


async def _wait_for_heartbeat(worker: AsyncioWorker) -> None:
    while worker.metrics()["last_heartbeat_at"] is None:
        await asyncio.sleep(0.01)
