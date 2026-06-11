"""
MY-DOGE-MICRO FastAPI Backend
Tauri sidecar — runs on localhost:8901
"""

import logging
import os

# S002-009 / TR-011: project root sourced from get_settings() (ADR-0001
# forbidden pattern ``_PROJECT_ROOT`` dirname-walk). The module-global name is
# KEPT so the contract test (tests/test_api_routers.py:153) can still
# monkeypatch it to a temp dir; only the *derivation* changed (settings vs
# os.path.dirname walk).

# ── OpenBLAS 安全设置 ────────────────────────────────
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from doge.config import get_settings
from src.api.routers import scan, data, notes, macro, analysis, config

logger = logging.getLogger("doge.api")

# Module-global project root — derived from Settings, monkeypatchable in tests.
_PROJECT_ROOT = str(get_settings().project_root)

app = FastAPI(title="MY-DOGE API", version="0.1.0")

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


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/stats")
async def stats():
    """数据库概览统计"""
    import sqlite3
    result = {}
    # S002-009: the project root is the module-global (Settings-derived, and
    # monkeypatchable by tests). DB paths derive from it so the test's
    # temp-root redirect remains effective; no os.path.dirname walk here.
    data_dir = os.path.join(_PROJECT_ROOT, "data")
    for db_name in ["market_data_cn.db", "market_data_us.db", "research_insights.db"]:
        db_path = os.path.join(data_dir, db_name)
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
            db_stats = {}
            for t in tables:
                cur.execute(f"SELECT COUNT(*) FROM [{t}]")
                db_stats[t] = cur.fetchone()[0]
            conn.close()
            result[db_name] = db_stats
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8901)
