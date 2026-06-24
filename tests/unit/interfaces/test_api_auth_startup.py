import pytest

from doge.config.settings import APIConfig, AuthConfig, Settings
from doge.infrastructure.auth import (
    DenyAllEnterpriseAuthProvider,
    StaticBearerAuthProvider,
    build_enterprise_auth_provider,
)
from doge.interfaces.api import main as api_main


def test_api_auth_startup_allows_local_demo_without_provider():
    settings = Settings(auth=AuthConfig(mode="local_demo"))

    api_main._validate_api_auth_startup(settings, None)


def test_api_auth_startup_rejects_enterprise_without_configured_provider():
    settings = Settings(auth=AuthConfig(mode="enterprise"))
    provider = DenyAllEnterpriseAuthProvider("missing enterprise provider")

    with pytest.raises(RuntimeError, match="enterprise auth startup failed"):
        api_main._validate_api_auth_startup(settings, provider)


def test_api_auth_startup_allows_configured_enterprise_provider():
    settings = Settings(auth=AuthConfig(mode="enterprise", static_bearer_token="secret-token"))
    provider = build_enterprise_auth_provider(settings.auth)

    assert isinstance(provider, StaticBearerAuthProvider)
    api_main._validate_api_auth_startup(settings, provider)


def test_api_auth_provider_uses_configured_secret_provider_factory():
    settings = Settings(auth=AuthConfig(mode="enterprise", static_tenant_id="tenant-secret"))

    provider = api_main._build_api_auth_provider(
        settings,
        secret_provider_factory=lambda: _SecretProvider({"auth.static_bearer_token": "process-token"}),
    )

    assert isinstance(provider, StaticBearerAuthProvider)
    assert provider.authenticate_bearer("process-token").tenant_id == "tenant-secret"


def test_remote_bind_rejects_local_demo_even_when_requested():
    settings = Settings(
        api=APIConfig(
            bind_host="0.0.0.0",
            allow_remote_bind=True,
            cors_allow_origins=("http://localhost:5173",),
            tls_termination_required=True,
        ),
        auth=AuthConfig(mode="local_demo"),
    )

    with pytest.raises(AssertionError, match="DOGE_AUTH_MODE=enterprise"):
        api_main._validate_api_remote_bind_startup(settings, None, "0.0.0.0")


def test_remote_bind_rejects_unconfigured_enterprise_auth():
    settings = Settings(
        api=APIConfig(
            bind_host="0.0.0.0",
            allow_remote_bind=True,
            cors_allow_origins=("http://localhost:5173",),
            tls_termination_required=True,
        ),
        auth=AuthConfig(mode="enterprise"),
    )
    provider = build_enterprise_auth_provider(settings.auth)

    with pytest.raises(AssertionError, match="configured enterprise auth provider"):
        api_main._validate_api_remote_bind_startup(settings, provider, "0.0.0.0")


def test_remote_bind_rejects_wildcard_cors():
    settings = Settings(
        api=APIConfig(
            bind_host="0.0.0.0",
            allow_remote_bind=True,
            cors_allow_origins=("*",),
            tls_termination_required=True,
        ),
        auth=AuthConfig(mode="enterprise", static_bearer_token="secret-token"),
    )
    provider = build_enterprise_auth_provider(settings.auth)

    with pytest.raises(AssertionError, match="explicit CORS allow-list"):
        api_main._validate_api_remote_bind_startup(settings, provider, "0.0.0.0")


def test_remote_bind_rejects_without_tls_acknowledgement():
    settings = Settings(
        api=APIConfig(
            bind_host="0.0.0.0",
            allow_remote_bind=True,
            cors_allow_origins=("http://localhost:5173",),
            tls_termination_required=False,
        ),
        auth=AuthConfig(mode="enterprise", static_bearer_token="secret-token"),
    )
    provider = build_enterprise_auth_provider(settings.auth)

    with pytest.raises(AssertionError, match="TLS termination"):
        api_main._validate_api_remote_bind_startup(settings, provider, "0.0.0.0")


def test_remote_bind_allows_enterprise_strict_cors_and_tls_acknowledgement():
    settings = Settings(
        api=APIConfig(
            bind_host="0.0.0.0",
            allow_remote_bind=True,
            cors_allow_origins=("https://research.example.internal",),
            tls_termination_required=True,
        ),
        auth=AuthConfig(mode="enterprise", static_bearer_token="secret-token"),
    )
    provider = build_enterprise_auth_provider(settings.auth)

    api_main._validate_api_remote_bind_startup(settings, provider, "0.0.0.0")


def test_legacy_api_mounts_only_for_local_loopback():
    local = Settings(auth=AuthConfig(mode="local_demo"), api=APIConfig(bind_host="127.0.0.1"))
    enterprise = Settings(
        auth=AuthConfig(mode="enterprise", static_bearer_token="secret-token"),
        api=APIConfig(bind_host="127.0.0.1"),
    )
    remote_local = Settings(auth=AuthConfig(mode="local_demo"), api=APIConfig(bind_host="0.0.0.0"))

    assert api_main._should_mount_legacy_api(local) is True
    assert api_main._should_mount_legacy_api(enterprise) is False
    assert api_main._should_mount_legacy_api(remote_local) is False


class _SecretProvider:
    def __init__(self, values):
        self._values = values

    def get_secret(self, name: str):
        return self._values.get(name)
