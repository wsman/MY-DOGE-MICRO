"""v1 session routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, Field

from doge.application.agent.worker import AsyncioWorker
from doge.application.use_cases.session_use_cases import CreateSession, ListSessions, ResumeSession
from doge.core.ports.agent_repository import ISessionRepository
from doge.interfaces.api import deps
from doge.interfaces.api.routers.v1._common import serialize

router = APIRouter(dependencies=[Depends(deps.require_api_token)])


class CreateSessionRequest(BaseModel):
    title: str = "Research session"


class CreateTurnRequest(BaseModel):
    message: str
    market: str = "us"
    language: str = "en"
    document_ids: list[str] = Field(default_factory=list)
    portfolio_id: str | None = "portfolio-demo"
    model_policy: dict[str, Any] = Field(default_factory=dict)


@router.post("/sessions")
async def create_session(
    body: CreateSessionRequest,
    sessions: ISessionRepository = Depends(deps.get_agent_session_repository),
):
    return serialize(CreateSession(sessions).execute(title=body.title))


@router.get("/sessions")
async def list_sessions(
    limit: int = 20,
    sessions: ISessionRepository = Depends(deps.get_agent_session_repository),
):
    return {"sessions": serialize(ListSessions(sessions).execute(limit=limit))}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    sessions: ISessionRepository = Depends(deps.get_agent_session_repository),
):
    session = ResumeSession(sessions).execute(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    return serialize(session)


@router.post("/sessions/{session_id}/turns", status_code=status.HTTP_202_ACCEPTED)
async def create_turn(
    session_id: str,
    body: CreateTurnRequest,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    sessions: ISessionRepository = Depends(deps.get_agent_session_repository),
    worker: AsyncioWorker = Depends(deps.get_daemon_worker),
):
    if sessions.get(session_id) is None:
        raise HTTPException(404, "session not found")
    run_id = await worker.enqueue_run(
        session_id,
        body.message,
        market=body.market,
        language=body.language,
        document_ids=body.document_ids,
        portfolio_id=body.portfolio_id,
        model_policy=body.model_policy,
        idempotency_key=idempotency_key,
    )
    response.status_code = status.HTTP_202_ACCEPTED
    return {"status": "accepted", "run_id": run_id}
