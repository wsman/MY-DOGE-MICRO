"""Compatibility aggregator for the focused v1 run routers.

The run surface is split into query (read), action (cancel / resolve approval),
and stream (SSE) routers, backed by the shared authorization / request-scope /
summary-redaction helpers in ``_runs_common``. This module re-aggregates them
under a single router so the existing ``/v1`` mount point keeps working.
"""

from __future__ import annotations

from fastapi import APIRouter

from doge.interfaces.gateway.routers.run_actions import router as run_actions_router
from doge.interfaces.gateway.routers.run_queries import router as run_queries_router
from doge.interfaces.gateway.routers.run_stream import router as run_stream_router

router = APIRouter()
router.include_router(run_queries_router)
router.include_router(run_actions_router)
router.include_router(run_stream_router)
