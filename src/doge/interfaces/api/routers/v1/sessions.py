"""v1 session routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from doge.application.agent.worker import AsyncioWorker
from doge.application.use_cases.session_use_cases import CreateSession, ListSessions, ResumeSession
from doge.core.ports.agent_repository import ISessionRepository
from doge.core.ports.enterprise_governance import IEnterpriseGovernanceRepository
from doge.interfaces.api import deps
from doge.interfaces.api.enterprise_access import (
    append_audit,
    ensure_resource_access,
    enterprise_context,
    is_enterprise_request,
    trusted_model_policy,
)
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
    request: Request,
    body: CreateSessionRequest,
    sessions: ISessionRepository = Depends(deps.get_agent_session_repository),
):
    tenant_id = _tenant_id_for_request(request)
    return serialize(CreateSession(sessions).execute(title=body.title, tenant_id=tenant_id))


@router.get("/sessions")
async def list_sessions(
    request: Request,
    limit: int = 20,
    sessions: ISessionRepository = Depends(deps.get_agent_session_repository),
):
    return {"sessions": serialize(ListSessions(sessions).execute(limit=limit, tenant_id=_tenant_id_for_request(request)))}


@router.get("/sessions/{session_id}")
async def get_session(
    request: Request,
    session_id: str,
    sessions: ISessionRepository = Depends(deps.get_agent_session_repository),
):
    session = ResumeSession(sessions).execute(session_id, tenant_id=_tenant_id_for_request(request))
    if session is None:
        raise HTTPException(404, "session not found")
    return serialize(session)


@router.post("/sessions/{session_id}/turns", status_code=status.HTTP_202_ACCEPTED)
async def create_turn(
    request: Request,
    session_id: str,
    body: CreateTurnRequest,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    sessions: ISessionRepository = Depends(deps.get_agent_session_repository),
    worker: AsyncioWorker = Depends(deps.get_daemon_worker),
    governance: IEnterpriseGovernanceRepository = Depends(deps.get_enterprise_governance_repository),
):
    if sessions.get(session_id, tenant_id=_tenant_id_for_request(request)) is None:
        raise HTTPException(404, "session not found")
    for document_id in body.document_ids:
        ensure_resource_access(request, governance, "document", document_id, "read")
    if body.portfolio_id is not None:
        ensure_resource_access(request, governance, "portfolio", body.portfolio_id, "read")
    run_id = await worker.enqueue_run(
        session_id,
        body.message,
        market=body.market,
        language=body.language,
        document_ids=body.document_ids,
        portfolio_id=body.portfolio_id,
        model_policy=trusted_model_policy(request, governance, body.model_policy),
        idempotency_key=idempotency_key,
    )
    append_audit(
        request,
        governance,
        "run_create",
        "run",
        run_id,
        metadata={"session_id": session_id, "document_ids": body.document_ids, "portfolio_id": body.portfolio_id},
    )
    response.status_code = status.HTTP_202_ACCEPTED
    return {"status": "accepted", "run_id": run_id}


def _tenant_id_for_request(request: Request) -> str | None:
    return enterprise_context(request).tenant_id if is_enterprise_request(request) else None
