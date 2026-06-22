"""Enterprise authentication boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Trusted identity and entitlement claims after bearer validation."""

    subject_hash: str
    tenant_id: str
    roles: tuple[str, ...] = ("analyst",)
    entitlements: tuple[str, ...] = field(default_factory=tuple)
    document_acl: tuple[str, ...] = field(default_factory=tuple)
    portfolio_permission: tuple[str, ...] = field(default_factory=tuple)
    approval_authority: tuple[str, ...] = field(default_factory=tuple)
    data_classification: str = "internal"
    project_id: str = "doge-dev"
    issuer: str | None = None
    audience: str | None = None
    token_id_hash: str | None = None


class EnterpriseAuthError(Exception):
    """Raised when bearer authentication fails."""


class IEnterpriseAuthProvider(Protocol):
    """Validate a bearer token and return a trusted principal."""

    def authenticate_bearer(self, token: str) -> AuthenticatedPrincipal:
        """Authenticate ``token`` and return provider-normalized claims."""
