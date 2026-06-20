"""Async worker for daemon-managed agent runs."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any

from doge.core.domain.agent_models import AgentRun, RunStatus
from doge.core.ports.agent_repository import ISessionRepository
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.idempotency_store import IIdempotencyStore
from doge.core.ports.unit_of_work import IAgentUnitOfWork
from doge.core.ports.worker_queue import IRunQueue


class AsyncioWorker:
    """Small durable-ish worker backed by SQLite queue metadata."""

    def __init__(
        self,
        runtime: IResearchAgentRuntime,
        sessions: ISessionRepository,
        run_queue: IRunQueue,
        idempotency_store: IIdempotencyStore,
        unit_of_work: IAgentUnitOfWork | None = None,
    ) -> None:
        self._runtime = runtime
        self._sessions = sessions
        self._run_queue = run_queue
        self._idempotency = idempotency_store
        self._unit_of_work = unit_of_work
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

    def recover(self) -> None:
        if self._recovered:
            return
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
        idempotency_key: str | None = None,
    ) -> str:
        if self._unit_of_work is None:
            raise RuntimeError("agent unit of work is not configured")
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
            idempotency_key=idempotency_key,
        )
        run = self._runtime.get_run(run_id)
        if run is not None and run.status != RunStatus.QUEUED:
            return run_id
        await self._enqueue_local_async(run_id)
        return run_id

    async def enqueue_continuation(self, run_id: str) -> None:
        run = self._runtime.get_run(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        if run.status != RunStatus.QUEUED:
            await self._runtime.queue_run(run_id, "worker_continuation")
        self._run_queue.enqueue(run_id)
        self.start()
        await self._enqueue_local_async(run_id)

    async def resolve_approval(self, run_id: str, approval_id: str, approved: bool) -> AgentRun:
        run = await self._runtime.resolve_approval(run_id, approval_id, approved)
        if approved and run.status == RunStatus.QUEUED:
            await self.enqueue_continuation(run_id)
            return self._runtime.get_run(run_id) or run
        return run

    async def cancel_run(self, run_id: str) -> AgentRun:
        run = await self._runtime.cancel_run(run_id)
        task = self._active_tasks.get(run_id)
        if task is not None and not task.done():
            task.cancel()
        return run

    async def _process_loop(self) -> None:
        while True:
            run_id = await self._queue.get()
            try:
                self._queued_run_ids.discard(run_id)
                self._run_queue.append_status(run_id, "running")
                task = asyncio.create_task(self._runtime.run_to_pause_or_completion(run_id))
                self._active_tasks[run_id] = task
                try:
                    run = await task
                    self._run_queue.append_status(run_id, _queue_status_for_run(run))
                except asyncio.CancelledError:
                    if self._stopping:
                        task.cancel()
                        with suppress(asyncio.CancelledError):
                            await task
                        raise
                    run = await self._runtime.finalize_cancelled(run_id)
                    self._run_queue.append_status(run_id, _queue_status_for_run(run))
                finally:
                    self._active_tasks.pop(run_id, None)
            except Exception:
                self._run_queue.append_status(run_id, "failed")
            finally:
                self._queue.task_done()

    def is_ready(self) -> bool:
        return self._run_queue.is_ready()

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


def _queue_status_for_run(run: AgentRun) -> str:
    if run.status == RunStatus.FAILED:
        return "failed"
    if run.status == RunStatus.CANCELLED:
        return "cancelled"
    return "done"
