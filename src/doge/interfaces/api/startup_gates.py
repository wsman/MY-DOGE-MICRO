"""API startup and bind-host promotion gates."""

from __future__ import annotations

import os

from doge.config import get_settings
from doge.interfaces.api import deps

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _configured_bind_host(settings) -> str:
    return os.environ.get("DOGE_BIND_HOST") or settings.api.bind_host


def _validate_api_remote_bind_startup(settings, auth_provider, host: str) -> None:
    """Validate the promotion gate for non-loopback API binds."""

    if host in _LOOPBACK_HOSTS:
        return
    assert settings.api.allow_remote_bind, (
        "ADR-0007 remote-bind promotion: set DOGE_ALLOW_REMOTE_BIND=1 before "
        "binding the API outside loopback."
    )
    assert settings.auth.mode == "enterprise", (
        "ADR-0015 remote-bind promotion: non-loopback bind requires "
        "DOGE_AUTH_MODE=enterprise."
    )
    assert auth_provider is not None and not deps.is_deny_all_enterprise_auth_provider(auth_provider), (
        "ADR-0015 remote-bind promotion: non-loopback bind requires a configured "
        "enterprise auth provider."
    )
    assert settings.api.cors_allow_origins and "*" not in settings.api.cors_allow_origins, (
        "ADR-0007 remote-bind promotion: non-loopback bind requires an explicit "
        "CORS allow-list."
    )
    assert settings.api.tls_termination_required, (
        "ADR-0015 remote-bind promotion: non-loopback bind requires TLS "
        "termination acknowledgement."
    )


def _resolve_bind_host(settings=None, auth_provider=None) -> str:
    """Resolve the API bind host, enforcing the ADR-0007 loopback guarantee."""

    settings = settings or get_settings()
    auth_provider = deps.build_api_auth_provider(settings) if auth_provider is None else auth_provider
    host = _configured_bind_host(settings)
    if host in _LOOPBACK_HOSTS:
        return host
    try:
        _validate_api_remote_bind_startup(settings, auth_provider, host)
    except AssertionError as exc:
        raise AssertionError(
            "ADR-0007 loopback guarantee: non-loopback bind requires CORS allow-list "
            "hardening + auth first (see ADR-0007 Promotion gate). "
            f"{exc}"
        ) from exc
    return host
