"""API error envelope registration."""

from __future__ import annotations

import logging

from fastapi import HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger("doge.api")

# Stable string-enum error codes so UI consumers can branch on error.error.code
# instead of brittle numeric strings.
_HTTP_STATUS_CODE = {
    400: "bad_request",
    404: "not_found",
    409: "conflict",
    422: "unprocessable",
    500: "internal_error",
}


async def _http_exception_handler(request, exc: HTTPException):
    """Reshape operator-safe HTTPException detail into the stable envelope."""

    code = _HTTP_STATUS_CODE.get(exc.status_code, f"http_{exc.status_code}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": exc.detail}},
    )


async def _unhandled_exception_handler(request, exc: Exception):
    """Return a fixed operator-safe response for otherwise-unhandled errors."""

    logger.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "internal server error"}},
    )


def register_exception_handlers(app) -> None:
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
