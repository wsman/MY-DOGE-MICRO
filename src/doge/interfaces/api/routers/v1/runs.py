"""v1 run routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from doge.application.agent.worker import AsyncioWorker
from doge.application.agent.event_bus import EventBus
from doge.core.domain.agent_models import RunStatus
from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.interfaces.api import deps
from doge.interfaces.api.routers.v1._common import serialize

router = APIRouter(dependencies=[Depends(deps.require_api_token)])
_STREAM_CLOSE_STATUSES = {
    RunStatus.AWAITING_APPROVAL,
    RunStatus.COMPLETED,
    RunStatus.FAILED,
    RunStatus.CANCELLED,
}


class ApprovalRequest(BaseModel):
    approved: bool = True


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    run = runtime.get_run(run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    return serialize(run)


@router.post("/runs/{run_id}/cancel")
async def cancel_run(
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    try:
        return serialize(await runtime.cancel_run(run_id))
    except KeyError:
        raise HTTPException(404, "run not found")


@router.get("/runs/{run_id}/events")
async def get_events(
    run_id: str,
    after_sequence: int = 0,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    if runtime.get_run(run_id) is None:
        raise HTTPException(404, "run not found")
    events = [event for event in runtime.list_events(run_id) if event.sequence > after_sequence]
    return {"events": serialize(events)}


@router.get("/runs/{run_id}/stream")
async def stream_run(
    run_id: str,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    bus: EventBus = Depends(deps.get_event_bus),
):
    if runtime.get_run(run_id) is None:
        raise HTTPException(404, "run not found")
    try:
        after_sequence = int(last_event_id or "0")
    except ValueError:
        after_sequence = 0

    async def generator():
        for event in runtime.list_events(run_id):
            if event.sequence <= after_sequence:
                continue
            yield {
                "id": str(event.sequence),
                "event": event.event_type.value,
                "data": json.dumps(serialize(event), ensure_ascii=False),
            }
        run = runtime.get_run(run_id)
        if run and run.status in _STREAM_CLOSE_STATUSES:
            return
        async for event in bus.subscribe(run_id):
            yield {
                "id": str(event.sequence),
                "event": event.event_type.value,
                "data": json.dumps(serialize(event), ensure_ascii=False),
            }
            run = runtime.get_run(run_id)
            if run and run.status in _STREAM_CLOSE_STATUSES:
                return

    return EventSourceResponse(generator())


@router.get("/runs/{run_id}/artifacts")
async def get_artifacts(
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    if runtime.get_run(run_id) is None:
        raise HTTPException(404, "run not found")
    return {"artifacts": serialize(runtime.list_artifacts(run_id))}


@router.get("/runs/{run_id}/approvals")
async def get_approvals(
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
):
    run = runtime.get_run(run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    return {"approvals": serialize(run.approvals)}


@router.post("/runs/{run_id}/approvals/{approval_id}")
async def resolve_approval(
    run_id: str,
    approval_id: str,
    body: ApprovalRequest,
    worker: AsyncioWorker = Depends(deps.get_daemon_worker),
):
    try:
        return serialize(await worker.resolve_approval(run_id, approval_id, body.approved))
    except KeyError as exc:
        raise HTTPException(404, str(exc))
