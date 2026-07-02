"""FastAPI lifespan management for daemon side effects."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from doge.config import get_settings
from doge.interfaces.api import deps


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    process_role = settings.daemon.process_role
    worker = None
    outbox_publisher = None
    if process_role in {"all", "worker"}:
        worker = deps.get_daemon_worker()
        if settings.features.runtime_outbox_publisher:
            outbox_publisher = deps.get_runtime_outbox_publisher()
            outbox_publisher.start()
        worker.start()
    try:
        yield
    finally:
        if worker is not None:
            await worker.stop()
        if outbox_publisher is not None:
            await outbox_publisher.stop()
