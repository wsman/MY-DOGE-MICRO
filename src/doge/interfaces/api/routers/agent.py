"""Research Agent API routes."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.interfaces.api import deps

router = APIRouter()


class AgentRunRequest(BaseModel):
    workflow: str = "investment_research"
    question: str
    document_ids: list[str] = Field(default_factory=list)
    portfolio_id: Optional[str] = "portfolio-demo"
    market: str = "us"
    language: str = "en"
    model_policy: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    approved: bool = True


def _serialize(obj):
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    return obj


@router.post("/runs")
async def create_run(
    body: AgentRunRequest,
    runtime: IResearchAgentRuntime = Depends(deps.get_research_agent_runtime),
):
    run = await runtime.create_run(body.model_dump())
    run = await runtime.run_to_pause_or_completion(run.run_id)
    return _serialize(run)


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_research_agent_runtime),
):
    run = runtime.get_run(run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    return _serialize(run)


@router.get("/runs/{run_id}/events")
async def get_events(
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_research_agent_runtime),
):
    try:
        return {"events": _serialize(runtime.list_events(run_id))}
    except KeyError:
        raise HTTPException(404, "run not found")


@router.get("/runs/{run_id}/stream")
async def stream_events(
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_research_agent_runtime),
):
    async def event_generator():
        try:
            async for event in runtime.stream_events(run_id):
                yield {
                    "event": "agent_event",
                    "data": json.dumps(_serialize(event), ensure_ascii=False),
                }
        except KeyError:
            yield {
                "event": "error",
                "data": json.dumps({"error": {"code": "not_found", "message": "run not found"}}),
            }

    return EventSourceResponse(event_generator())


@router.get("/runs/{run_id}/artifacts")
async def get_artifacts(
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_research_agent_runtime),
):
    run = runtime.get_run(run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    return {"artifacts": _serialize(run.artifacts)}


@router.get("/runs/{run_id}/approvals")
async def get_approvals(
    run_id: str,
    runtime: IResearchAgentRuntime = Depends(deps.get_research_agent_runtime),
):
    run = runtime.get_run(run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    return {"approvals": _serialize(run.approvals)}


@router.post("/runs/{run_id}/approvals/{approval_id}")
async def resolve_approval(
    run_id: str,
    approval_id: str,
    _body: ApprovalRequest,
    runtime: IResearchAgentRuntime = Depends(deps.get_research_agent_runtime),
):
    if runtime.get_run(run_id) is None:
        raise HTTPException(404, "run not found")
    raise HTTPException(
        409,
        "legacy approval continuation is unsupported; use the /v1 daemon API",
    )
