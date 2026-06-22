"""ADR-0007 strengthened-loopback-guarantee compatibility check (S004-005).

This test intentionally imports the deprecated ``src.api`` shim to prove the
backwards-compatible entrypoint still exposes the canonical loopback guard.
"""
import sys
from pathlib import Path

import pytest

from doge.config.settings import APIConfig, AuthConfig, Settings
from doge.infrastructure.auth import build_enterprise_auth_provider

# Project-root sys.path setup (mirrors tests/test_api_routers.py) — strips
# sibling-project paths and inserts this repo root so the shim resolves here.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path[:] = [
    p for p in sys.path
    if p and "MY-DOGE-PRO" not in p and "opendoge" not in p
]

from src.api import main as api_main  # noqa: E402


def test_default_host_is_loopback(monkeypatch):
    """With no DOGE_BIND_HOST, the default 127.0.0.1 is returned."""
    monkeypatch.delenv("DOGE_BIND_HOST", raising=False)
    assert api_main._resolve_bind_host() == "127.0.0.1"


@pytest.mark.parametrize("host", sorted(api_main._LOOPBACK_HOSTS))
def test_loopback_hosts_accepted(monkeypatch, host):
    """Every documented loopback host is accepted."""
    monkeypatch.setenv("DOGE_BIND_HOST", host)
    assert api_main._resolve_bind_host() == host


def test_non_loopback_host_fails_closed(monkeypatch):
    """A non-loopback bind (e.g. 0.0.0.0) raises — CORS hardening + auth first."""
    monkeypatch.setenv("DOGE_BIND_HOST", "0.0.0.0")
    with pytest.raises(AssertionError, match="ADR-0007 loopback guarantee"):
        api_main._resolve_bind_host()


def test_non_loopback_hostname_fails_closed(monkeypatch):
    """A non-loopback hostname also fails closed (not just IPs)."""
    monkeypatch.setenv("DOGE_BIND_HOST", "example.com")
    with pytest.raises(AssertionError, match="ADR-0007 loopback guarantee"):
        api_main._resolve_bind_host()


def test_non_loopback_host_can_pass_only_through_enterprise_promotion_gate(monkeypatch):
    """Remote bind promotion requires enterprise auth, strict CORS, and TLS ack."""
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

    monkeypatch.setenv("DOGE_BIND_HOST", "0.0.0.0")
    assert api_main._resolve_bind_host(settings=settings, auth_provider=provider) == "0.0.0.0"
