"""Async worker for daemon-managed agent runs."""

from __future__ import annotations

import asyncio
from typing import Any

from doge.core.domain.agent_models import AgentRun, AgentTurn, utc_now
from doge.core.ports.agent_repository import ISessionRepository
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.idempotency_store import IIdempotencyStore
from doge.core.ports.worker_queue import IRunQueue


class AsyncioWorker:
    """Small durable-ish worker backed by SQLite queue metadata."""

    def __init__(
        self,
        runtime: IResearchAgentRuntime,
        sessions: ISessionRepository,
        run_queue: IRunQueue,
        idempotency_store: IIdempotencyStore,
    ) -> None:
        self._runtime = runtime
        self._sessions = sessions
        self._run_queue = run_queue
        self._idempotency = idempotency_store
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._queued_run_ids: set[str] = set()
        self._task: asyncio.Task | None = None
        self._recovered = False

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
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass

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
        if idempotency_key:
            existing = self._idempotency.get(idempotency_key, session_id)
            if existing:
                return existing
        self.start()
        run = await self._runtime.create_run({
            "workflow": "investment_research",
            "question": message,
            "session_id": session_id,
            "market": market,
            "language": language,
            "document_ids": document_ids or [],
            "portfolio_id": portfolio_id,
            "model_policy": model_policy or {"max_tool_rounds": 8},
        })
        self._append_turn(session_id, message, run.run_id)
        self._run_queue.enqueue(run.run_id)
        if idempotency_key:
            self._idempotency.set(idempotency_key, session_id, run.run_id)
        await self._enqueue_local_async(run.run_id)
        return run.run_id

    async def enqueue_continuation(self, run_id: str) -> None:
        self._run_queue.enqueue(run_id)
        self.start()
        await self._enqueue_local_async(run_id)

    async def resolve_approval(self, run_id: str, approval_id: str, approved: bool) -> AgentRun:
        return await self._runtime.resolve_approval(run_id, approval_id, approved)

    async def _process_loop(self) -> None:
        while True:
            run_id = await self._queue.get()
            try:
                self._queued_run_ids.discard(run_id)
                self._run_queue.append_status(run_id, "running")
                await self._runtime.run_to_pause_or_completion(run_id)
                self._run_queue.append_status(run_id, "done")
            except Exception:
                self._run_queue.append_status(run_id, "failed")
            finally:
                self._queue.task_done()

    def _append_turn(self, session_id: str, message: str, run_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        session.turns.append(AgentTurn.create(session_id=session_id, user_message=message, run_id=run_id))
        session.updated_at = utc_now()
        self._sessions.save(session)

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
