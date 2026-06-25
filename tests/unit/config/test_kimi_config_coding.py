"""KimiConfig coding-mode precedence (ADR-0023 / Kimi For Coding endpoint)."""

from __future__ import annotations

import pytest

from doge.config import get_settings
from doge.config.settings import reset_settings

# Env vars exercised by these tests.
_CODING_ENV = (
    "KIMI_BASE_URL",
    "KIMI_CODING_MODE",
    "KIMI_CODING_BASE_URL",
    "KIMI_CODING_USER_AGENT",
    "KIMI_CLIENT_USER_AGENT",
    "KIMI_EXTRA_HEADERS",
    "DOGE_TEXT_LLM_PROVIDER",
)


@pytest.fixture(autouse=True)
def _clean_kimi_env(monkeypatch):
    for name in _CODING_ENV:
        monkeypatch.delenv(name, raising=False)
    reset_settings()
    yield
    reset_settings()


def test_kimi_config_coding_mode_off_defaults():
    settings = get_settings().kimi

    assert settings.coding_mode is False
    assert settings.effective_base_url() == "https://api.moonshot.ai/v1"
    assert settings.default_http_headers() == {}


def test_kimi_config_coding_mode_on_applies_coding_defaults(monkeypatch):
    monkeypatch.setenv("KIMI_CODING_MODE", "1")
    reset_settings()
    settings = get_settings().kimi

    assert settings.coding_mode is True
    assert settings.effective_base_url() == "https://api.kimi.com/coding/v1"
    headers = settings.default_http_headers()
    assert headers["User-Agent"] == "claude-code/0.1.0"


def test_kimi_config_provider_kimi_coding_implies_coding_mode(monkeypatch):
    monkeypatch.setenv("DOGE_TEXT_LLM_PROVIDER", "kimi-coding")
    reset_settings()
    settings = get_settings().kimi

    assert settings.coding_mode is True
    assert settings.effective_base_url() == "https://api.kimi.com/coding/v1"


def test_kimi_config_explicit_base_url_wins_over_coding_mode(monkeypatch):
    monkeypatch.setenv("KIMI_CODING_MODE", "1")
    monkeypatch.setenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
    reset_settings()
    settings = get_settings().kimi

    assert settings.coding_mode is True
    assert settings.effective_base_url() == "https://api.moonshot.cn/v1"


def test_kimi_config_client_user_agent_override_wins(monkeypatch):
    monkeypatch.setenv("KIMI_CODING_MODE", "1")
    monkeypatch.setenv("KIMI_CLIENT_USER_AGENT", "roo-code/1.2.3")
    reset_settings()
    settings = get_settings().kimi

    assert settings.default_http_headers()["User-Agent"] == "roo-code/1.2.3"


def test_kimi_config_coding_base_url_and_user_agent_overridable(monkeypatch):
    monkeypatch.setenv("KIMI_CODING_MODE", "1")
    monkeypatch.setenv("KIMI_CODING_BASE_URL", "https://proxy.example/coding")
    monkeypatch.setenv("KIMI_CODING_USER_AGENT", "kilo-code/2.0")
    reset_settings()
    settings = get_settings().kimi

    assert settings.effective_base_url() == "https://proxy.example/coding"
    assert settings.default_http_headers()["User-Agent"] == "kilo-code/2.0"


def test_kimi_config_extra_headers_merged(monkeypatch):
    monkeypatch.setenv("KIMI_CODING_MODE", "1")
    monkeypatch.setenv("KIMI_EXTRA_HEADERS", '{"X-Trace-Id": "abc", "X-Env": "qa"}')
    reset_settings()
    settings = get_settings().kimi

    headers = settings.default_http_headers()
    assert headers["User-Agent"] == "claude-code/0.1.0"
    assert headers["X-Trace-Id"] == "abc"
    assert headers["X-Env"] == "qa"


def test_kimi_config_coding_mode_off_with_client_user_agent_still_sets_header(monkeypatch):
    monkeypatch.setenv("KIMI_CLIENT_USER_AGENT", "custom-agent/0.9")
    reset_settings()
    settings = get_settings().kimi

    # Explicit UA applies even when coding mode is off.
    assert settings.coding_mode is False
    assert settings.default_http_headers() == {"User-Agent": "custom-agent/0.9"}


def test_kimi_config_extra_headers_invalid_json_ignored(monkeypatch):
    monkeypatch.setenv("KIMI_EXTRA_HEADERS", "not-json")
    reset_settings()
    settings = get_settings().kimi

    assert settings.extra_headers == {}
