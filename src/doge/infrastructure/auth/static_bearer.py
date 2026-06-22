"""Local static bearer adapter for enterprise-auth middleware tests and demos.

This is deliberately not an OIDC implementation. It lets local operators prove
the FastAPI authentication boundary without adding a vendor IdP. Production
enterprise mode still requires the OIDC/JWKS story from S017.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from doge.config.settings import AuthConfig
from doge.core.ports.enterprise_auth import (
    AuthenticatedPrincipal,
    EnterpriseAuthError,
    IEnterpriseAuthProvider,
)
from doge.core.ports.secrets import ISecretProvider
from doge.infrastructure.auth.jwt_provider import JwtEnterpriseAuthProvider
from doge.infrastructure.secrets import EnvSecretProvider


@dataclass(frozen=True)
class StaticBearerAuthProvider(IEnterpriseAuthProvider):
    """Accept exactly one configured bearer token and emit one principal."""

    token: str
    principal: AuthenticatedPrincipal

    def authenticate_bearer(self, token: str) -> AuthenticatedPrincipal:
        if not secrets.compare_digest(token, self.token):
            raise EnterpriseAuthError("invalid bearer token")
        return self.principal


@dataclass(frozen=True)
class DenyAllEnterpriseAuthProvider(IEnterpriseAuthProvider):
    """Fail closed when enterprise mode lacks a configured provider."""

    reason: str = "enterprise authentication provider is not configured"

    def authenticate_bearer(self, token: str) -> AuthenticatedPrincipal:
        raise EnterpriseAuthError(self.reason)


def build_enterprise_auth_provider(
    config: AuthConfig,
    *,
    secret_provider: ISecretProvider | None = None,
) -> IEnterpriseAuthProvider | None:
    """Build the API auth provider for the configured auth mode."""

    if config.mode == "local_demo":
        return None
    if config.mode != "enterprise":
        return DenyAllEnterpriseAuthProvider(f"unsupported auth mode: {config.mode}")
    if config.oidc_issuer and config.oidc_audience and config.oidc_jwks_url:
        return JwtEnterpriseAuthProvider(config)
    secrets = secret_provider or EnvSecretProvider()
    static_bearer_token = config.static_bearer_token or secrets.get_secret("auth.static_bearer_token")
    if not static_bearer_token:
        return DenyAllEnterpriseAuthProvider()
    return StaticBearerAuthProvider(
        token=static_bearer_token,
        principal=AuthenticatedPrincipal(
            subject_hash=_hash_identifier(config.static_subject),
            tenant_id=config.static_tenant_id,
            roles=config.static_roles,
            entitlements=config.static_entitlements,
            document_acl=config.static_document_acl,
            portfolio_permission=config.static_portfolio_permission,
            approval_authority=config.static_approval_authority,
            data_classification=config.static_data_classification,
            project_id=config.static_project_id,
            issuer=config.oidc_issuer,
            audience=config.oidc_audience,
            token_id_hash=_hash_identifier(static_bearer_token),
        ),
    )


def _hash_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
