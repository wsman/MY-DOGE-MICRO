"""Async worker for daemon-managed agent runs."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from typing import Any

from doge.config import get_settings
from doge.core.domain.agent_models import AgentRun, AgentTurn, RunStatus, utc_now
from doge.core.ports.agent_repository import ISessionRepository
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.infrastructure.database.agent_repositories import bootstrap_agent_schema


class AsyncioWorker:
    """Small durable-ish worker backed by SQLite queue metadata."""

    def __init__(
        self,
        runtime: IResearchAgentRuntime,
        sessions: ISessionRepository,
        *,
        db_path: Path | str | None = None,
    ) -> None:
        self._runtime = runtime
        self._sessions = sessions
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self._recovered = False
        self._db_path = Path(db_path) if db_path is not None else get_settings().db.agent_db
        bootstrap_agent_schema(self._db_path)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._process_loop())
        if not self._recovered:
            self._recover_pending()
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
            existing = self._get_idempotent_run(idempotency_key, session_id)
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
        self._record_queue(run.run_id, "queued")
        if idempotency_key:
            self._record_idempotency(idempotency_key, session_id, run.run_id)
        await self._queue.put(run.run_id)
        return run.run_id

    async def enqueue_continuation(self, run_id: str) -> None:
        self._record_queue(run_id, "queued")
        self.start()
        await self._queue.put(run_id)

    async def resolve_approval(self, run_id: str, approval_id: str, approved: bool) -> AgentRun:
        return await self._runtime.resolve_approval(run_id, approval_id, approved)

    async def _process_loop(self) -> None:
        while True:
            run_id = await self._queue.get()
            try:
                self._record_queue(run_id, "running")
                await self._runtime.run_to_pause_or_completion(run_id)
                self._record_queue(run_id, "done")
            except Exception:
                self._record_queue(run_id, "failed")
            finally:
                self._queue.task_done()

    def _append_turn(self, session_id: str, message: str, run_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        session.turns.append(AgentTurn.create(session_id=session_id, user_message=message, run_id=run_id))
        session.updated_at = utc_now()
        self._sessions.save(session)

    def _record_queue(self, run_id: str, status: str) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """
                INSERT INTO run_queue(run_id, status, created_at, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (run_id, status),
            )
            conn.commit()

    def is_ready(self) -> bool:
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute("SELECT 1 FROM run_queue LIMIT 1")
            return True
        except Exception:
            return False

    def _recover_pending(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            rows = conn.execute(
                """
                SELECT q.run_id, q.status
                FROM run_queue q
                JOIN (
                    SELECT run_id, MAX(queue_id) AS max_queue_id
                    FROM run_queue
                    GROUP BY run_id
                ) latest
                ON q.run_id = latest.run_id AND q.queue_id = latest.max_queue_id
                WHERE q.status IN ('queued', 'running')
                """
            ).fetchall()
        for run_id, _status in rows:
            self._queue.put_nowait(run_id)

    def _get_idempotent_run(self, key: str, scope: str) -> str | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute(
                "SELECT run_id FROM idempotency_keys WHERE key = ? AND scope = ?",
                (key, scope),
            ).fetchone()
            return row[0] if row else None

    def _record_idempotency(self, key: str, scope: str, run_id: str) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO idempotency_keys(key, scope, run_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (key, scope, run_id, utc_now()),
            )
            conn.commit()
