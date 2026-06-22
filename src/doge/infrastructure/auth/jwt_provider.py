"""OIDC/JWKS bearer validation for enterprise API mode."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from doge.config.settings import AuthConfig
from doge.core.ports.enterprise_auth import (
    AuthenticatedPrincipal,
    EnterpriseAuthError,
    IEnterpriseAuthProvider,
)


@dataclass(frozen=True)
class JwtEnterpriseAuthProvider(IEnterpriseAuthProvider):
    """Validate bearer JWTs with configured issuer, audience, algorithms, and JWKS."""

    config: AuthConfig
    jwk_client: Any | None = None

    def __post_init__(self) -> None:
        missing = [
            name
            for name, value in (
                ("DOGE_AUTH_OIDC_ISSUER", self.config.oidc_issuer),
                ("DOGE_AUTH_OIDC_AUDIENCE", self.config.oidc_audience),
                ("DOGE_AUTH_OIDC_JWKS_URL", self.config.oidc_jwks_url),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"missing OIDC configuration: {', '.join(missing)}")
        if self.jwk_client is None:
            object.__setattr__(self, "jwk_client", PyJWKClient(self.config.oidc_jwks_url or ""))

    def authenticate_bearer(self, token: str) -> AuthenticatedPrincipal:
        try:
            signing_key = self.jwk_client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=list(self.config.oidc_algorithms),
                issuer=self.config.oidc_issuer,
                audience=self.config.oidc_audience,
                leeway=self.config.clock_skew_seconds,
                options={"require": ["exp", "iat", self.config.subject_claim, self.config.tenant_claim]},
            )
        except (PyJWTError, AttributeError, ValueError) as exc:
            raise EnterpriseAuthError("invalid bearer token") from exc

        subject = _required_claim(claims, self.config.subject_claim)
        tenant = _required_claim(claims, self.config.tenant_claim)
        return AuthenticatedPrincipal(
            subject_hash=_hash_identifier(subject),
            tenant_id=tenant,
            roles=_claim_tuple(claims.get(self.config.roles_claim)) or ("analyst",),
            entitlements=_claim_tuple(claims.get(self.config.entitlements_claim)),
            document_acl=_claim_tuple(claims.get("document_acl")),
            portfolio_permission=_claim_tuple(claims.get("portfolio_permission")),
            approval_authority=_claim_tuple(claims.get(self.config.approval_authority_claim)),
            data_classification=_string_claim(claims.get("data_classification"), "internal"),
            project_id=_string_claim(claims.get(self.config.project_claim), "doge-dev"),
            issuer=self.config.oidc_issuer,
            audience=self.config.oidc_audience,
            token_id_hash=_hash_identifier(_string_claim(claims.get("jti"), token)),
        )


def _required_claim(claims: dict[str, Any], name: str) -> str:
    value = claims.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing required claim: {name}")
    return value


def _claim_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(item.strip() for item in value.split(",") if item.strip())
    if isinstance(value, Iterable):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def _string_claim(value: Any, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value
    return default


def _hash_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
