"""Async worker for daemon-managed agent runs."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any
from uuid import uuid4

from doge.core.domain.agent_models import AgentRun, RunStatus
from doge.core.ports.agent_repository import ISessionRepository
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.idempotency_store import IIdempotencyStore
from doge.core.ports.unit_of_work import IAgentUnitOfWork
from doge.core.ports.worker_queue import IRunQueue
from doge.shared.scope import TenantScope


class AsyncioWorker:
    """Small durable-ish worker backed by SQLite queue metadata."""

    def __init__(
        self,
        runtime: IResearchAgentRuntime,
        sessions: ISessionRepository,
        run_queue: IRunQueue,
        idempotency_store: IIdempotencyStore,
        unit_of_work: IAgentUnitOfWork | None = None,
        worker_id: str | None = None,
        lease_seconds: int = 30,
        heartbeat_interval_seconds: float | None = None,
        poll_interval_seconds: float = 1.0,
        auto_start: bool = True,
    ) -> None:
        self._runtime = runtime
        self._sessions = sessions
        self._run_queue = run_queue
        self._idempotency = idempotency_store
        self._unit_of_work = unit_of_work
        self._worker_id = worker_id or f"worker-{uuid4().hex[:12]}"
        self._lease_seconds = lease_seconds
        self._heartbeat_interval_seconds = heartbeat_interval_seconds or max(1.0, lease_seconds / 3)
        self._poll_interval_seconds = max(0.1, poll_interval_seconds)
        self._auto_start = auto_start
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._queued_run_ids: set[str] = set()
        self._active_tasks: dict[str, asyncio.Task[AgentRun]] = {}
        self._task: asyncio.Task | None = None
        self._recovered = False
        self._stopping = False

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._process_loop())
        self.recover()

    @property
    def worker_id(self) -> str:
        return self._worker_id

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def recover(self) -> None:
        if self._recovered:
            return
        self._run_queue.recover_stalled_leases(self._lease_seconds)
        for run_id in self._run_queue.list_pending():
            self._enqueue_local(run_id)
        self._recovered = True

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stopping = True
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._stopping = False
            self._task = None

    async def enqueue_run(
        self,
        session_id: str,
        message: str,
        *,
        market: str = "us",
        language: str = "en",
        document_ids: list[str] | None = None,
        portfolio_id: str | None = "portfolio-demo",
        model_policy: dict[str, Any] | None = None,
        identity_snapshot: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        if self._unit_of_work is None:
            raise RuntimeError("agent unit of work is not configured")
        if self._auto_start:
            self.start()
        run_id = await self._unit_of_work.enqueue_run_and_turn(
            session_id=session_id,
            message=message,
            workflow="investment_research",
            market=market,
            language=language,
            document_ids=document_ids or [],
            portfolio_id=portfolio_id,
            model_policy=model_policy or {"max_tool_rounds": 8},
            identity_snapshot=identity_snapshot,
            idempotency_key=idempotency_key,
        )
        scope = _scope_from_snapshot(identity_snapshot)
        run = self._runtime.get_run(scope, run_id)
        if run is not None and run.status != RunStatus.QUEUED:
            return run_id
        if self._auto_start:
            await self._enqueue_local_async(run_id)
        return run_id

    async def enqueue_continuation(
        self,
        run_id: str,
        *,
        scope: TenantScope | None = None,
        tenant_id: str | None = None,
    ) -> None:
        resolved_scope = scope or TenantScope.from_tenant_id(tenant_id)
        run = self._runtime.get_run(resolved_scope, run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        if run.status != RunStatus.QUEUED:
            await self._runtime.queue_run(resolved_scope, run_id, "worker_continuation")
        self._run_queue.enqueue(run_id)
        if self._auto_start:
            self.start()
            await self._enqueue_local_async(run_id)

    async def resolve_approval(
        self,
        run_id: str,
        approval_id: str,
        approved: bool,
        *,
        scope: TenantScope | None = None,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope = scope or TenantScope.from_tenant_id(tenant_id)
        run = await self._runtime.resolve_approval(resolved_scope, run_id, approval_id, approved)
        if approved and run.status == RunStatus.QUEUED:
            await self.enqueue_continuation(run_id, scope=resolved_scope)
            return self._runtime.get_run(resolved_scope, run_id) or run
        return run

    async def cancel_run(
        self,
        run_id: str,
        *,
        scope: TenantScope | None = None,
        tenant_id: str | None = None,
    ) -> AgentRun:
        run = await self._runtime.cancel_run(scope or TenantScope.from_tenant_id(tenant_id), run_id)
        task = self._active_tasks.get(run_id)
        if task is not None and not task.done():
            task.cancel()
        return run

    async def _process_loop(self) -> None:
        while True:
            if self._stopping:
                return
            has_signal = False
            run_id: str | None = None
            heartbeat_task: asyncio.Task | None = None
            try:
                try:
                    signal_run_id = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=self._poll_interval_seconds,
                    )
                    has_signal = True
                    self._queued_run_ids.discard(signal_run_id)
                except TimeoutError:
                    if self._stopping:
                        return
                    pass
                run_id = self._run_queue.claim_atomic(self._worker_id, self._lease_seconds)
                if run_id is None:
                    continue
                heartbeat_task = asyncio.create_task(self._heartbeat_loop(run_id))
                task = asyncio.create_task(self._runtime.run_to_pause_or_completion(run_id))
                self._active_tasks[run_id] = task
                try:
                    run = await task
                    self._run_queue.release_claim(run_id, self._worker_id, _queue_status_for_run(run))
                except asyncio.CancelledError:
                    if self._stopping:
                        task.cancel()
                        with suppress(asyncio.CancelledError):
                            await task
                        raise
                    run = await self._runtime.finalize_cancelled(self._scope_for_run(run_id), run_id)
                    self._run_queue.release_claim(run_id, self._worker_id, _queue_status_for_run(run))
                finally:
                    self._active_tasks.pop(run_id, None)
                    if heartbeat_task is not None:
                        heartbeat_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await heartbeat_task
            except Exception:
                if run_id is not None:
                    await _record_runtime_failure(self._runtime, run_id, "runtime failure")
                    self._run_queue.release_claim(run_id, self._worker_id, "failed")
            finally:
                if has_signal:
                    self._queue.task_done()

    def is_ready(self) -> bool:
        return self._run_queue.is_ready()

    def _scope_for_run(self, run_id: str) -> TenantScope:
        return _scope_from_run(self._runtime.get_run(run_id))

    def _enqueue_local(self, run_id: str) -> None:
        if run_id in self._queued_run_ids:
            return
        self._queued_run_ids.add(run_id)
        self._queue.put_nowait(run_id)

    async def _enqueue_local_async(self, run_id: str) -> None:
        if run_id in self._queued_run_ids:
            return
        self._queued_run_ids.add(run_id)
        await self._queue.put(run_id)

    async def _heartbeat_loop(self, run_id: str) -> None:
        while True:
            await asyncio.sleep(self._heartbeat_interval_seconds)
            self._run_queue.heartbeat(self._worker_id, run_id, self._lease_seconds)


def _queue_status_for_run(run: AgentRun) -> str:
    if run.status == RunStatus.FAILED:
        return "failed"
    if run.status == RunStatus.CANCELLED:
        return "cancelled"
    return "done"


async def _record_runtime_failure(runtime: IResearchAgentRuntime, run_id: str, message: str) -> None:
    record_failure = getattr(runtime, "record_failure", None)
    if record_failure is None:
        return
    with suppress(Exception):
        await record_failure(_scope_from_run(runtime.get_run(run_id)), run_id, message)


def _scope_from_snapshot(snapshot: dict[str, Any] | None) -> TenantScope:
    if not snapshot:
        return TenantScope.local()
    tenant_id = snapshot.get("tenant_id")
    return TenantScope.from_tenant_id(str(tenant_id) if tenant_id else None)


def _scope_from_run(run: AgentRun | None) -> TenantScope:
    if run is None or run.identity_snapshot is None:
        return TenantScope.local()
    return TenantScope.enterprise(run.identity_snapshot.tenant_id, run.identity_snapshot.user_hash)
