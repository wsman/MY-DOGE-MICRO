"""v1 daemon health routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from doge.core.ports.agent_repository import ISessionRepository
from doge.config import Settings
from doge.interfaces.api import deps

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(
    sessions: ISessionRepository = Depends(deps.get_agent_session_repository),
    settings: Settings = Depends(deps.get_settings_dep),
    readiness_probe=Depends(deps.get_daemon_readiness_probe),
):
    try:
        sessions.list_recent(limit=1)
    except Exception:
        raise HTTPException(503, "not ready")
    snapshot = readiness_probe.snapshot(
        process_role=settings.daemon.process_role,
        worker=deps.get_existing_daemon_worker(),
    )
    if snapshot["status"] != "ready":
        raise HTTPException(status_code=503, detail=snapshot)
    return snapshot
