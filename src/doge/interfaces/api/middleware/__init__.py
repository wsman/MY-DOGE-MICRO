"""API middleware registration helpers."""

from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from doge.interfaces.api.middleware.tenant_context import TenantContextMiddleware

_LEGACY_API_DEPRECATION_DOC = (
    "https://github.com/wsman/MY-DOGE-MICRO/blob/main/"
    "docs/architecture/adr-0024-single-stack-runtime-direction.md"
)
_LEGACY_API_SUNSET = "Wed, 30 Sep 2026 00:00:00 GMT"


async def _legacy_api_deprecation_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Deprecation", "true")
        response.headers.setdefault("Sunset", _LEGACY_API_SUNSET)
        response.headers.setdefault("Link", f'<{_LEGACY_API_DEPRECATION_DOC}>; rel="deprecation"')
        response.headers.setdefault("X-DOGE-Compatibility-Surface", "legacy-api")
    return response


def register_middleware(app, settings, auth_provider) -> None:
    app.add_middleware(
        TenantContextMiddleware,
        local_demo=settings.auth.mode == "local_demo",
        auth_provider=auth_provider,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.api.cors_allow_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(BaseHTTPMiddleware, dispatch=_legacy_api_deprecation_headers)
