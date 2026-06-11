"""Contract test for S002-013 — GET /api/config must redact api_key.

The local FastAPI surface previously returned ``models_config.json`` verbatim,
including the ``api_key`` field of every profile (an active exfiltration vector
to any process that could reach the API port). As of S002-013 the endpoint
deep-copies the loaded dict and drops ``api_key`` from every profile in the
HTTP response — neither a real key, nor the placeholder sentinel, nor
``<redacted>`` is echoed.

This is a BLOCKING API-contract test per ``standards/coding-standards.md``.
"""
import json
import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Make src/ importable (documented test-shim exception). Filter out sibling
# projects on sys.path so `src.api` resolves to THIS repo (mirrors
# tests/test_api_routers.py:79-83).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path[:] = [
    p for p in sys.path
    if p and "MY-DOGE-PRO" not in p and "opendoge" not in p
]
sys.path.insert(0, str(_PROJECT_ROOT))

from src.api import main as api_main  # noqa: E402
from src.api.routers import config as config_router  # noqa: E402

_SK_PREFIX_RE = re.compile(r"^sk-")
PLACEHOLDER = "REPLACE_WITH_DEEPSEEK_API_KEY"


@pytest.fixture
def client_and_profile_with_secret(tmp_path, monkeypatch):
    """A TestClient plus a temp project root whose models_config.json carries
    a real-looking key in one DeepSeek profile and the placeholder in the
    other, so the redaction can be verified to remove BOTH."""
    # Redirect the config router's _PROJECT_ROOT to the temp dir
    monkeypatch.setattr(config_router, "_PROJECT_ROOT", str(tmp_path))

    config = {
        "profiles": [
            {
                "name": "DeepSeek Chat",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-chat",
                # A FAKE key — never a real credential.
                "api_key": "sk-fake-real-looking-key-AAAAAAAAAAAAAAAA",
            },
            {
                "name": "DeepSeek Reasoner",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-reasoner",
                "api_key": PLACEHOLDER,
            },
            {
                "name": "LM Studio (Local)",
                "base_url": "http://localhost:1234/v1",
                "model": "local-model",
                "api_key": "lm-studio",
            },
        ],
        "default_profile": "DeepSeek Chat",
        "macro_settings": {"lookback_days": 120, "volatility_window": 20},
        "assets": {
            "tech": {"symbol": "QQQ", "name": "科技股(纳指)"},
            "safe": {"symbol": "GLD", "name": "避险黄金"},
            "crypto": {"symbol": "BTC-USD", "name": "数字货币"},
            "target": {"symbol": "000300.SS", "name": "A股核心(沪深300)"},
        },
        "proxy_settings": {"enabled": False, "url": "http://127.0.0.1:7890"},
        "scanner_filters": {
            "us_blacklist": ["SQQQ"],
            "min_volume_cn": 200000000,
            "min_volume_us": 20000000,
            "max_change_pct": 400,
            "rsrs_window": 18,
        },
    }
    with open(tmp_path / "models_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f)

    return TestClient(api_main.app), config


class TestGetConfigRedactsApiKey:
    def test_get_config_redacts_or_omits_api_key(
        self, client_and_profile_with_secret
    ):
        # Arrange
        client, _ = client_and_profile_with_secret

        # Act
        r = client.get("/api/config")

        # Assert — HTTP 200 and no profile exposes a key
        assert r.status_code == 200
        body = r.json()
        for profile in body["profiles"]:
            assert "api_key" not in profile, (
                f"profile {profile.get('name')} leaked api_key="
                f"{profile.get('api_key')!r}"
            )
            # Belt-and-braces: no field anywhere holds a real-looking key or
            # the placeholder string.
            for value in profile.values():
                assert not (
                    isinstance(value, str) and _SK_PREFIX_RE.match(value)
                ), f"sk- key leaked in profile {profile.get('name')}"
                assert value != PLACEHOLDER

    def test_get_config_does_not_leak_placeholder(
        self, client_and_profile_with_secret
    ):
        # Arrange
        client, _ = client_and_profile_with_secret

        # Act
        r = client.get("/api/config")

        # Assert — the on-disk placeholder is never echoed to a client
        assert PLACEHOLDER not in r.text

    def test_get_config_preserves_non_secret_fields(
        self, client_and_profile_with_secret
    ):
        # Arrange
        client, original = client_and_profile_with_secret

        # Act
        r = client.get("/api/config")
        body = r.json()

        # Assert — top-level non-secret fields preserved
        assert body["default_profile"] == original["default_profile"]
        assert body["macro_settings"] == original["macro_settings"]
        assert body["assets"] == original["assets"]
        assert body["proxy_settings"] == original["proxy_settings"]
        assert body["scanner_filters"] == original["scanner_filters"]

        # Per-profile non-secret fields preserved (base_url, model, name)
        for orig_p, resp_p in zip(original["profiles"], body["profiles"]):
            assert resp_p["name"] == orig_p["name"]
            assert resp_p["base_url"] == orig_p["base_url"]
            assert resp_p["model"] == orig_p["model"]
            # Only api_key is dropped
            assert set(resp_p.keys()) == {
                "name", "base_url", "model",
            }, f"unexpected profile keys: {set(resp_p.keys())}"


class TestRedactHelperIsSurgical:
    def test_redact_helper_drops_api_key_from_each_profile(self):
        # Arrange
        from src.api.routers.config import _redact_api_keys

        config = {
            "profiles": [
                {"name": "a", "api_key": "sk-real-AAAAAAAAAAAAAAAA"},
                {"name": "b", "api_key": PLACEHOLDER},
                {"name": "c", "api_key": "lm-studio"},
            ],
            "default_profile": "a",
        }

        # Act
        redacted = _redact_api_keys(config)

        # Assert — original is untouched (deep copy), redacted has no api_key
        assert "api_key" in config["profiles"][0]  # original preserved
        for p in redacted["profiles"]:
            assert "api_key" not in p
        assert redacted["default_profile"] == "a"

    def test_redact_helper_handles_missing_profiles_key(self):
        # Arrange — defensive: a config dict without profiles must not crash
        from src.api.routers.config import _redact_api_keys

        # Act
        redacted = _redact_api_keys({"default_profile": "x"})

        # Assert
        assert redacted == {"default_profile": "x"}
