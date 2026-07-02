"""API authentication provider construction and startup gates."""

from __future__ import annotations

from doge.interfaces.api import deps


def _build_api_auth_provider(settings, secret_provider_factory=None):
    """Build API enterprise auth using the configured secret-provider boundary."""

    return deps.build_api_auth_provider(settings, secret_provider_factory=secret_provider_factory)


def _has_oidc_config(auth_config) -> bool:
    return deps.has_oidc_config(auth_config)


def _validate_api_auth_startup(settings, auth_provider) -> None:
    """Fail startup when enterprise mode has no usable bearer provider."""

    if settings.auth.mode != "enterprise":
        return
    if auth_provider is None or deps.is_deny_all_enterprise_auth_provider(auth_provider):
        reason = getattr(auth_provider, "reason", "enterprise authentication provider is not configured")
        raise RuntimeError(f"enterprise auth startup failed: {reason}")
