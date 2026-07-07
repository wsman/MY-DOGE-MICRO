"""FastAPI route registration for the API app."""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI

from doge.core.ports.repository import ISchemaBrowser
from doge.interfaces.api import deps
from doge.interfaces.api.startup_gates import _LOOPBACK_HOSTS, _configured_bind_host
from doge.interfaces.api_legacy.routers import agent, analysis, config, data, documents, macro, notes, scan
from doge.interfaces.gateway.routers import audit as v1_audit
from doge.interfaces.gateway.routers import documents as v1_documents
from doge.interfaces.gateway.routers import enterprise as v1_enterprise
from doge.interfaces.gateway.routers import health as v1_health
from doge.interfaces.gateway.routers import platform as v1_platform
from doge.interfaces.gateway.routers import portfolios as v1_portfolios
from doge.interfaces.gateway.routers import runs as v1_runs
from doge.interfaces.gateway.routers import sessions as v1_sessions
from doge.interfaces.gateway.routers import slots as v1_slots
from doge.interfaces.gateway.routers import tools as v1_tools

logger = logging.getLogger("doge.api")


async def health():
    return {"status": "ok"}


async def stats(
    browser: ISchemaBrowser = Depends(deps.get_schema_browser),
):
    """Return database overview statistics."""

    return browser.database_stats()


def _should_mount_legacy_api(settings, host: str | None = None) -> bool:
    """Return whether local-demo legacy ``/api/*`` routers should be mounted."""

    host = host or _configured_bind_host(settings)
    if settings.auth.mode == "enterprise":
        if not settings.api.enterprise_disable_legacy:
            logger.warning("DOGE_API_ENTERPRISE_DISABLE_LEGACY=0 ignored in enterprise mode")
        return False
    if host not in _LOOPBACK_HOSTS:
        return False
    return True


def _register_legacy_api_routes(target_app: FastAPI, settings) -> None:
    """Mount legacy local-demo routers only when the deployment is loopback local."""

    if not _should_mount_legacy_api(settings):
        logger.info("legacy /api routers disabled for auth_mode=%s", settings.auth.mode)
        return
    target_app.include_router(scan.router, prefix="/api/scan", tags=["scan"])
    target_app.include_router(data.router, prefix="/api/data", tags=["data"])
    target_app.include_router(notes.router, prefix="/api/notes", tags=["notes"])
    target_app.include_router(macro.router, prefix="/api/macro", tags=["macro"])
    target_app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
    target_app.include_router(config.router, prefix="/api/config", tags=["config"])
    target_app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
    target_app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
    target_app.add_api_route("/api/stats", stats, methods=["GET"])


def _register_v1_routes(target_app: FastAPI, settings=None) -> None:
    target_app.include_router(v1_sessions.router, prefix="/v1", tags=["v1-sessions"])
    target_app.include_router(v1_runs.router, prefix="/v1", tags=["v1-runs"])
    target_app.include_router(v1_documents.router, prefix="/v1", tags=["v1-documents"])
    target_app.include_router(v1_portfolios.router, prefix="/v1", tags=["v1-portfolios"])
    target_app.include_router(v1_platform.router, prefix="/v1", tags=["v1-platform"])
    mounted_gateway_routes: tuple[str, ...] = ()
    if settings is not None and settings.features.slot_platform:
        from doge.bootstrap.runtime_factories.slots import build_slot_aware_gateway_routes

        mounted_gateway_routes = build_slot_aware_gateway_routes(
            target_app,
            settings=settings,
        )
    if "gateway.slots" not in mounted_gateway_routes:
        target_app.include_router(v1_slots.router, prefix="/v1", tags=["v1-slots"])
    target_app.include_router(v1_tools.router, prefix="/v1", tags=["v1-tools"])
    target_app.include_router(v1_audit.router, prefix="/v1", tags=["v1-audit"])
    target_app.include_router(v1_enterprise.router, prefix="/v1", tags=["v1-enterprise"])
    target_app.include_router(v1_health.router, tags=["health"])


def register_routes(app: FastAPI, settings) -> None:
    app.add_api_route("/api/health", health, methods=["GET"])
    _register_legacy_api_routes(app, settings)
    _register_v1_routes(app, settings)
