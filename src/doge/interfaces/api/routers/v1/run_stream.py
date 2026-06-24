"""v1 run SSE streaming route."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, Request
from sse_starlette.sse import EventSourceResponse

from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.event_subscriber import IEventSubscriber
from doge.interfaces.api import deps
from doge.interfaces.api.routers.v1._common import serialize
from doge.interfaces.api.routers.v1._runs_common import (
    STREAM_CLOSE_EVENTS,
    STREAM_CLOSE_STATUSES,
    authorized_run,
    max_event_sequence_after,
    request_scope,
)

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


@router.get("/runs/{run_id}/stream")
async def stream_run(
    request: Request,
    run_id: str,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    subscriber: IEventSubscriber = Depends(deps.get_event_subscriber),
):
    scope = request_scope(request)
    authorized = authorized_run(request, runtime, run_id)
    try:
        after_sequence = int(last_event_id or "0")
    except ValueError:
        after_sequence = 0

    async def generator():
        run = runtime.get_run(scope, run_id) or authorized
        terminal_at_start = run.status in STREAM_CLOSE_STATUSES
        initial_max_sequence = max_event_sequence_after(
            runtime,
            run_id,
            after_sequence,
            scope=scope,
        )
        if terminal_at_start and initial_max_sequence <= after_sequence:
            return
        async for event in subscriber.subscribe(run_id, after_sequence=after_sequence):
            yield {
                "id": str(event.sequence),
                "event": event.event_type.value,
                "data": json.dumps(serialize(event), ensure_ascii=False),
            }
            run = runtime.get_run(scope, run_id)
            if run and run.status in STREAM_CLOSE_STATUSES:
                if terminal_at_start and event.sequence >= initial_max_sequence:
                    return
                if not terminal_at_start and event.event_type.value in STREAM_CLOSE_EVENTS:
                    return

    return EventSourceResponse(generator())
