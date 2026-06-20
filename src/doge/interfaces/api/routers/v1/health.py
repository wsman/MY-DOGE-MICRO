"""v1 daemon health routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from doge.core.ports.agent_repository import ISessionRepository
from doge.interfaces.api import deps

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(sessions: ISessionRepository = Depends(deps.get_agent_session_repository)):
    try:
        sessions.list_recent(limit=1)
    except Exception:
        raise HTTPException(503, "not ready")
    return {"status": "ready"}
