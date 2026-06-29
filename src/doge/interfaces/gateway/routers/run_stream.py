"""v1 run SSE streaming route.

This route uses ``RunStreamHandler`` which combines historical replay via
``runtime.list_events`` with live events via ``IEventSubscriber.subscribe``.
This is the canonical live SSE implementation.

Streaming semantics (per ADR-0025):
- ``list_events`` = synchronous persisted query (historical replay)
- ``stream_events`` = replay-only async iterator (not used here)
- ``RunStreamHandler`` + ``IEventSubscriber.subscribe`` = live cross-process SSE

New clients should use this ``/v1/runs/{run_id}/stream`` endpoint.
The legacy ``/api/runs/{run_id}/stream`` is replay-only and deprecated.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.core.ports.event_subscriber import IEventSubscriber
from doge.interfaces.api import deps
from doge.interfaces.api.handlers import RunNotFound, RunStreamHandler
from doge.interfaces.gateway.routers._common import serialize
from doge.interfaces.gateway.routers._runs_common import request_run_access

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


@router.get("/runs/{run_id}/stream")
async def stream_run(
    request: Request,
    run_id: str,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    runtime: IResearchAgentRuntime = Depends(deps.get_persisted_research_agent_runtime),
    subscriber: IEventSubscriber = Depends(deps.get_event_subscriber),
):
    try:
        after_sequence = int(last_event_id or "0")
    except ValueError:
        after_sequence = 0
    try:
        event_stream = RunStreamHandler(runtime=runtime, subscriber=subscriber).open(
            run_id=run_id,
            access=request_run_access(request),
            after_sequence=after_sequence,
        )
    except RunNotFound:
        raise HTTPException(404, "run not found")

    async def generator():
        async for event in event_stream:
            yield {
                "id": str(event.sequence),
                "event": event.event_type.value,
                "data": json.dumps(serialize(event), ensure_ascii=False),
            }

    return EventSourceResponse(generator())
