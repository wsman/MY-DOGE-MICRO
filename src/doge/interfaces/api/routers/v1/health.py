"""v1 daemon health routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from doge.application.agent.worker import AsyncioWorker
from doge.interfaces.api import deps

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(worker: AsyncioWorker = Depends(deps.get_daemon_worker)):
    if not worker.is_ready():
        raise HTTPException(503, "not ready")
    return {"status": "ready"}
