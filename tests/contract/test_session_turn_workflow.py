"""Contract test: the session-turn ``workflow`` field threads end-to-end (ADR-0028).

Pins that an optional ``workflow`` slug on ``POST /v1/sessions/{id}/turns``
reaches the persisted ``AgentRun`` via
CreateTurnRequest -> SubmitSessionTurnCommand -> SubmitSessionTurnHandler ->
AsyncioWorker.enqueue_run -> IAgentUnitOfWork.enqueue_run_and_turn, and that
``ExecuteRun.execute`` threads it into ``runtime.create_run``. The default
``investment_research`` is preserved when the field is absent (byte-for-byte
current behavior); a non-default slug is forwarded unchanged.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from doge.application.use_cases.run_use_cases import ExecuteRun
from doge.interfaces.api.handlers.sessions import (
    SubmitSessionTurnCommand,
    SubmitSessionTurnHandler,
)


def test_openapi_create_turn_request_exposes_workflow_field() -> None:
    from doge.interfaces.api.main import app

    props = app.openapi()["components"]["schemas"]["CreateTurnRequest"]["properties"]
    assert "workflow" in props
    # Default preserves the legacy behavior.
    assert props["workflow"]["default"] == "investment_research"


# ── Handler layer: command.workflow -> worker.enqueue_run(workflow=...) ──


class _FakeSessions:
    def get(self, session_id, _scope):
        return {"session_id": session_id}


class _FakeWorker:
    def __init__(self) -> None:
        self.captured: dict[str, Any] = {}

    async def enqueue_run(self, session_id, message, **kwargs):
        self.captured = {"session_id": session_id, "message": message, **kwargs}
        return "run-1"


def test_handler_threads_default_workflow_to_worker() -> None:
    worker = _FakeWorker()
    handler = SubmitSessionTurnHandler(sessions=_FakeSessions(), worker=worker)
    asyncio.run(handler.handle(SubmitSessionTurnCommand(session_id="ses-1", message="hi")))
    assert worker.captured["workflow"] == "investment_research"


def test_handler_threads_non_default_workflow_to_worker() -> None:
    worker = _FakeWorker()
    handler = SubmitSessionTurnHandler(sessions=_FakeSessions(), worker=worker)
    asyncio.run(
        handler.handle(
            SubmitSessionTurnCommand(
                session_id="ses-1", message="hi", workflow="portfolio_risk_review"
            )
        )
    )
    assert worker.captured["workflow"] == "portfolio_risk_review"


# ── Worker layer: enqueue_run(workflow=...) -> unit_of_work.enqueue_run_and_turn ──


class _FakeUnitOfWork:
    def __init__(self) -> None:
        self.captured: dict[str, Any] = {}

    async def enqueue_run_and_turn(self, **kwargs):
        self.captured = kwargs
        return "run-2"


class _FakeWorkerRuntime:
    def get_run(self, _scope, _run_id):
        return None


def _worker_with_fake_uow() -> tuple:
    from doge.application.agent.worker import AsyncioWorker

    uow = _FakeUnitOfWork()
    worker = AsyncioWorker(
        runtime=_FakeWorkerRuntime(),
        sessions=object(),
        run_queue=object(),
        idempotency_store=object(),
        unit_of_work=uow,
        auto_start=False,
    )
    return worker, uow


def test_worker_threads_workflow_to_unit_of_work() -> None:
    worker, uow = _worker_with_fake_uow()
    run_id = asyncio.run(worker.enqueue_run("ses-1", "hi", workflow="earnings_review"))
    assert run_id == "run-2"
    assert uow.captured["workflow"] == "earnings_review"


def test_worker_default_workflow_is_investment_research() -> None:
    worker, uow = _worker_with_fake_uow()
    asyncio.run(worker.enqueue_run("ses-1", "hi"))
    assert uow.captured["workflow"] == "investment_research"


# ── ExecuteRun layer: execute(workflow=...) -> runtime.create_run payload ──


class _FakeExecuteRuntime:
    def __init__(self) -> None:
        self.create_payload: dict[str, Any] | None = None

    async def create_run(self, _scope, payload):
        self.create_payload = payload
        return SimpleNamespace(run_id="run-x")

    async def run_to_pause_or_completion(self, _scope, run_id):
        return SimpleNamespace(run_id=run_id)


def test_execute_run_threads_workflow_into_create_run_payload() -> None:
    runtime = _FakeExecuteRuntime()
    asyncio.run(ExecuteRun(runtime).execute("question?", workflow="daily_market_brief"))
    assert runtime.create_payload is not None
    assert runtime.create_payload["workflow"] == "daily_market_brief"


def test_execute_run_default_workflow_is_investment_research() -> None:
    runtime = _FakeExecuteRuntime()
    asyncio.run(ExecuteRun(runtime).execute("question?"))
    assert runtime.create_payload is not None
    assert runtime.create_payload["workflow"] == "investment_research"
