"""
MY-DOGE-MICRO FastAPI Backend
Tauri sidecar — runs on localhost:8901
"""

import logging
import os
from contextlib import asynccontextmanager

# S002-009 / TR-011: project root sourced from get_settings() (ADR-0001
# forbidden pattern ``_PROJECT_ROOT`` dirname-walk). The module-global name is
# KEPT so the contract test (tests/test_api_routers.py:153) can still
# monkeypatch it to a temp dir; only the *derivation* changed (settings vs
# os.path.dirname walk).

# ── OpenBLAS 安全设置 ────────────────────────────────
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from doge.config import get_settings
from doge.core.ports.repository import ISchemaBrowser
from doge.interfaces.api import deps
from doge.interfaces.api.middleware.tenant_context import TenantContextMiddleware
from doge.interfaces.api.routers import scan, data, notes, macro, analysis, config, agent, documents
from doge.interfaces.api.routers.v1 import documents as v1_documents
from doge.interfaces.api.routers.v1 import health as v1_health
from doge.interfaces.api.routers.v1 import runs as v1_runs
from doge.interfaces.api.routers.v1 import sessions as v1_sessions
from doge.interfaces.api.routers.v1 import tools as v1_tools

logger = logging.getLogger("doge.api")

# Module-global project root — derived from Settings, monkeypatchable in tests.
_PROJECT_ROOT = str(get_settings().project_root)


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = deps.get_daemon_worker()
    worker.start()
    try:
        yield
    finally:
        await worker.stop()


app = FastAPI(title="MY-DOGE API", version="0.1.0", lifespan=lifespan)

app.add_middleware(TenantContextMiddleware, local_demo=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # 仅 localhost, 无安全风险
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 全局异常处理 (ADR-0007 Decision 3, S002-009) ─────
# Stable string-enum error codes so UI consumers (and the S002-010 SSE client)
# can branch on error.error.code instead of brittle numeric strings.
_HTTP_STATUS_CODE = {
    400: "bad_request",
    404: "not_found",
    409: "conflict",
    422: "unprocessable",
    500: "internal_error",
}


@app.exception_handler(HTTPException)
async def _http_exception_handler(request, exc: HTTPException):
    """Reshape operator-safe HTTPException(4xx/5xx, detail) into the stable
    ``{"error": {"code", "message"}}`` envelope.

    ``exc.detail`` is operator-authored fixed text (e.g. "note not found"), so
    it passes through unchanged as the ``message`` field.
    """
    code = _HTTP_STATUS_CODE.get(exc.status_code, f"http_{exc.status_code}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": exc.detail}},
    )


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request, exc: Exception):
    """Catch-all for any otherwise-unhandled exception.

    The raw exception (type, message, traceback) is logged server-side for
    operator diagnosis; it is NEVER returned to the client — the response body
    is a fixed operator-safe string so no internal path, SQL fragment, or stack
    trace leaks over HTTP.
    """
    logger.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error",
                           "message": "internal server error"}},
    )

# NOTE: FastAPI's default 422 RequestValidationError handler is intentionally
# left AS-IS (it emits {"detail": [...]}). Enveloping pydantic validation
# errors is out of scope for S002-009; existing tests assert 422 status only.
# S002-011 owns any follow-on ADR-0007 promotion-gate decisions.


# ── 注册路由 ─────────────────────────────────────────
app.include_router(scan.router,   prefix="/api/scan",     tags=["scan"])
app.include_router(data.router,   prefix="/api/data",     tags=["data"])
app.include_router(notes.router,  prefix="/api/notes",    tags=["notes"])
app.include_router(macro.router,  prefix="/api/macro",    tags=["macro"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(config.router, prefix="/api/config",   tags=["config"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(v1_sessions.router, prefix="/v1", tags=["v1-sessions"])
app.include_router(v1_runs.router, prefix="/v1", tags=["v1-runs"])
app.include_router(v1_documents.router, prefix="/v1", tags=["v1-documents"])
app.include_router(v1_tools.router, prefix="/v1", tags=["v1-tools"])
app.include_router(v1_health.router, tags=["health"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/stats")
async def stats(
    browser: ISchemaBrowser = Depends(deps.get_schema_browser),
):
    """数据库概览统计"""
    return browser.database_stats()


# ── ADR-0007 strengthened-loopback-guarantee (S004-005) ──
# ``allow_origins=["*"]`` (line 37) is safe ONLY because the API binds to
# loopback. ``_resolve_bind_host`` makes that guarantee explicit and fail-closed
# rather than implicit on the hardcoded default: a non-loopback bind (via
# ``DOGE_BIND_HOST``) is rejected — CORS allow-list hardening + auth are required
# first (see ADR-0007 Promotion gate).
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _resolve_bind_host() -> str:
    """Resolve the API bind host, enforcing the ADR-0007 loopback guarantee.

    Returns the loopback host (``DOGE_BIND_HOST`` env, default ``127.0.0.1``).
    Raises ``AssertionError`` for any non-loopback host so the permissive CORS
    posture is never exposed off-loopback without hardening + auth.
    """
    host = os.environ.get("DOGE_BIND_HOST", "127.0.0.1")
    assert host in _LOOPBACK_HOSTS, (
        "ADR-0007 loopback guarantee: non-loopback bind requires CORS allow-list "
        "hardening + auth first (see ADR-0007 Promotion gate)."
    )
    return host


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=_resolve_bind_host(), port=8901)
