from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from doge.config.settings import AuthConfig
from doge.core.ports.enterprise_auth import EnterpriseAuthError
from doge.infrastructure.auth import JwtEnterpriseAuthProvider, build_enterprise_auth_provider


class _FakeJwkClient:
    def __init__(self, public_key) -> None:
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token: str):
        return SimpleNamespace(key=self._public_key)


@pytest.fixture()
def rsa_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def test_jwt_provider_validates_token_and_maps_principal(rsa_keys):
    private_key, public_key = rsa_keys
    config = _auth_config()
    token = _token(
        private_key,
        {
            "sub": "analyst@example.test",
            "tenant_id": "tenant-a",
            "roles": ["portfolio_manager"],
            "entitlements": "risk,evidence",
            "approval_authority": ["publish-memo"],
            "document_acl": ["doc-1"],
            "portfolio_permission": ["portfolio-1"],
            "data_classification": "confidential",
            "project_id": "project-alpha",
            "jti": "token-1",
        },
        config=config,
    )
    provider = JwtEnterpriseAuthProvider(config, jwk_client=_FakeJwkClient(public_key))

    principal = provider.authenticate_bearer(token)

    assert principal.subject_hash != "analyst@example.test"
    assert len(principal.subject_hash) == 32
    assert principal.tenant_id == "tenant-a"
    assert principal.roles == ("portfolio_manager",)
    assert principal.entitlements == ("risk", "evidence")
    assert principal.document_acl == ("doc-1",)
    assert principal.portfolio_permission == ("portfolio-1",)
    assert principal.approval_authority == ("publish-memo",)
    assert principal.data_classification == "confidential"
    assert principal.project_id == "project-alpha"
    assert principal.issuer == config.oidc_issuer
    assert principal.audience == config.oidc_audience
    assert principal.token_id_hash != "token-1"


def test_build_enterprise_auth_provider_prefers_oidc_jwks_config():
    provider = build_enterprise_auth_provider(_auth_config())

    assert isinstance(provider, JwtEnterpriseAuthProvider)


@pytest.mark.parametrize(
    ("case", "config_override"),
    [
        ("expired", {"clock_skew_seconds": 0}),
        ("wrong_issuer", {}),
        ("wrong_audience", {}),
        ("missing_tenant", {}),
    ],
)
def test_jwt_provider_rejects_invalid_claims(rsa_keys, case, config_override):
    private_key, public_key = rsa_keys
    config = _auth_config(**config_override)
    claims = {"sub": "analyst", "tenant_id": "tenant-a"}
    if case == "expired":
        claims["exp"] = _now() - timedelta(seconds=1)
    elif case == "wrong_issuer":
        claims["iss"] = "https://wrong-idp.example.test"
    elif case == "wrong_audience":
        claims["aud"] = "wrong-audience"
    elif case == "missing_tenant":
        claims["tenant_id"] = None
    token = _token(private_key, {"sub": "analyst", "tenant_id": "tenant-a", **claims}, config=config)
    provider = JwtEnterpriseAuthProvider(config, jwk_client=_FakeJwkClient(public_key))

    with pytest.raises(EnterpriseAuthError):
        provider.authenticate_bearer(token)


def test_jwt_provider_rejects_wrong_algorithm(rsa_keys):
    _, public_key = rsa_keys
    config = _auth_config()
    token = jwt.encode(
        _claims({"sub": "analyst", "tenant_id": "tenant-a"}, config=config),
        "shared-secret-with-at-least-32-bytes",
        algorithm="HS256",
    )
    provider = JwtEnterpriseAuthProvider(config, jwk_client=_FakeJwkClient(public_key))

    with pytest.raises(EnterpriseAuthError):
        provider.authenticate_bearer(token)


def test_jwt_provider_rejects_invalid_signature(rsa_keys):
    _, public_key = rsa_keys
    wrong_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    config = _auth_config()
    token = _token(wrong_private_key, {"sub": "analyst", "tenant_id": "tenant-a"}, config=config)
    provider = JwtEnterpriseAuthProvider(config, jwk_client=_FakeJwkClient(public_key))

    with pytest.raises(EnterpriseAuthError):
        provider.authenticate_bearer(token)


def test_jwt_provider_rejects_malformed_token(rsa_keys):
    _, public_key = rsa_keys
    provider = JwtEnterpriseAuthProvider(_auth_config(), jwk_client=_FakeJwkClient(public_key))

    with pytest.raises(EnterpriseAuthError):
        provider.authenticate_bearer("not-a-jwt")


def _auth_config(**overrides) -> AuthConfig:
    values = {
        "mode": "enterprise",
        "oidc_issuer": "https://idp.example.test",
        "oidc_audience": "doge-api",
        "oidc_jwks_url": "https://idp.example.test/.well-known/jwks.json",
        "oidc_algorithms": ("RS256",),
        "clock_skew_seconds": 0,
    }
    values.update(overrides)
    return AuthConfig(**values)


def _token(private_key, extra_claims: dict, *, config: AuthConfig) -> str:
    return jwt.encode(_claims(extra_claims, config=config), private_key, algorithm="RS256")


def _claims(extra_claims: dict, *, config: AuthConfig) -> dict:
    claims = {
        "iss": config.oidc_issuer,
        "aud": config.oidc_audience,
        "iat": _now(),
        "exp": _now() + timedelta(minutes=5),
    }
    claims.update(extra_claims)
    return claims


def _now() -> datetime:
    return datetime.now(timezone.utc)
