"""Tenant context middleware for local demos and enterprise deployments."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from doge.core.domain.enterprise_context import EnterpriseContext


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Attach a sanitized EnterpriseContext to ``request.state``."""

    def __init__(self, app, *, local_demo: bool = True) -> None:
        super().__init__(app)
        self._local_demo = local_demo

    async def dispatch(self, request: Request, call_next):
        if not self._local_demo and not _is_authenticated(request):
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "unauthorized", "message": "authentication required"}},
            )
        request.state.enterprise_context = enterprise_context_from_headers(request.headers)
        return await call_next(request)


def enterprise_context_from_headers(headers) -> EnterpriseContext:
    """Build context from demo headers without preserving raw user identifiers."""

    raw_user = headers.get("x-doge-user-id") or headers.get("x-user-id") or "anonymous"
    return EnterpriseContext(
        tenant_id=_safe_token(headers.get("x-doge-tenant-id"), "local"),
        user_hash=_hash_identifier(raw_user),
        role=_safe_token(headers.get("x-doge-role"), "analyst"),
        document_acl=frozenset(_csv(headers.get("x-doge-document-acl"))),
        tool_entitlement=frozenset(_csv(headers.get("x-doge-tool-entitlement"))),
        portfolio_permission=frozenset(_csv(headers.get("x-doge-portfolio-permission"))),
        data_classification=_safe_token(headers.get("x-doge-data-classification"), "internal"),
        approval_authority=frozenset(_csv(headers.get("x-doge-approval-authority"))),
        project_id=_safe_token(headers.get("x-doge-project-id"), "doge-dev"),
    )


def _is_authenticated(request: Request) -> bool:
    return bool(getattr(request.state, "authenticated_user", None) or request.scope.get("user"))


def _hash_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def _safe_token(value: str | None, default: str) -> str:
    if not value:
        return default
    token = "".join(ch for ch in value if ch.isalnum() or ch in {"-", "_", "."})
    return token or default


def _csv(value: str | None) -> Iterable[str]:
    if not value:
        return ()
    return tuple(_safe_token(item.strip(), "") for item in value.split(",") if item.strip())
