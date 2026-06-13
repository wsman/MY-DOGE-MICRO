"""ADR-0007 strengthened-loopback-guarantee (S004-005).

The FastAPI CORS posture (``allow_origins=["*"]`` in ``src/api/main.py``) is
safe ONLY under a loopback bind. ``_resolve_bind_host`` enforces this: a
non-loopback ``DOGE_BIND_HOST`` fails closed rather than exposing the API with
permissive CORS and no auth. This is the ADR-0007 promotion path (1b) — the
loopback guarantee replaces CORS hardening for the local-first, single-operator
deployment model.
"""
import sys
from pathlib import Path

import pytest

# Project-root sys.path setup (mirrors tests/test_api_routers.py) — strips
# sibling-project paths and inserts this repo root so ``src.api`` resolves.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path[:] = [
    p for p in sys.path
    if p and "MY-DOGE-PRO" not in p and "opendoge" not in p
]
sys.path.insert(0, str(_PROJECT_ROOT))

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
