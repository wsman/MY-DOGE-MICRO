import pytest

from doge.config.settings import AuthConfig
from doge.core.ports.enterprise_auth import EnterpriseAuthError
from doge.infrastructure.auth import (
    DenyAllEnterpriseAuthProvider,
    StaticBearerAuthProvider,
    build_enterprise_auth_provider,
)


class _SecretProvider:
    def __init__(self, values):
        self.values = values

    def get_secret(self, name: str):
        return self.values.get(name)


def test_build_enterprise_auth_provider_returns_none_for_local_demo():
    provider = build_enterprise_auth_provider(AuthConfig(mode="local_demo"))

    assert provider is None


def test_build_enterprise_auth_provider_fails_closed_without_token():
    provider = build_enterprise_auth_provider(AuthConfig(mode="enterprise"))

    assert isinstance(provider, DenyAllEnterpriseAuthProvider)
    with pytest.raises(EnterpriseAuthError):
        provider.authenticate_bearer("any-token")


def test_static_bearer_provider_maps_config_to_hashed_principal():
    provider = build_enterprise_auth_provider(
        AuthConfig(
            mode="enterprise",
            oidc_issuer="https://idp.example.test",
            oidc_audience="doge-api",
            static_bearer_token="secret-token",
            static_subject="analyst@example.test",
            static_tenant_id="tenant-a",
            static_roles=("portfolio_manager",),
            static_entitlements=("risk", "evidence"),
            static_document_acl=("doc-1",),
            static_portfolio_permission=("portfolio-1",),
            static_approval_authority=("publish-memo",),
            static_data_classification="confidential",
            static_project_id="project-alpha",
        )
    )

    assert isinstance(provider, StaticBearerAuthProvider)
    principal = provider.authenticate_bearer("secret-token")

    assert principal.subject_hash != "analyst@example.test"
    assert len(principal.subject_hash) == 32
    assert principal.tenant_id == "tenant-a"
    assert principal.roles == ("portfolio_manager",)
    assert principal.entitlements == ("risk", "evidence")
    assert principal.document_acl == ("doc-1",)
    assert principal.portfolio_permission == ("portfolio-1",)
    assert principal.approval_authority == ("publish-memo",)
    assert principal.issuer == "https://idp.example.test"
    assert principal.audience == "doge-api"
    assert principal.token_id_hash != "secret-token"


def test_static_bearer_provider_rejects_wrong_token():
    provider = build_enterprise_auth_provider(
        AuthConfig(mode="enterprise", static_bearer_token="secret-token")
    )

    assert isinstance(provider, StaticBearerAuthProvider)
    with pytest.raises(EnterpriseAuthError):
        provider.authenticate_bearer("wrong-token")


def test_static_bearer_provider_reads_token_from_secret_provider():
    provider = build_enterprise_auth_provider(
        AuthConfig(mode="enterprise", static_subject="analyst@example.test", static_tenant_id="tenant-a"),
        secret_provider=_SecretProvider({"auth.static_bearer_token": "secret-token"}),
    )

    assert isinstance(provider, StaticBearerAuthProvider)
    principal = provider.authenticate_bearer("secret-token")

    assert principal.tenant_id == "tenant-a"
    assert principal.subject_hash != "analyst@example.test"
    assert principal.token_id_hash != "secret-token"
