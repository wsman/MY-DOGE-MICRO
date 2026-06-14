"""Unit tests for S002-013 — DeepSeek API key rotation to env var.

Covers the secret-rotation contract (TR-015 / ADR-0005 Migration Plan step 2):

1. ``models_config.json`` ships the ``REPLACE_WITH_DEEPSEEK_API_KEY``
   placeholder for both DeepSeek profiles (never a real ``sk-...`` key), while
   the LM Studio profile keeps its ``lm-studio`` token.
2. ``MacroConfig._apply_runtime_overrides`` promotes ``DEEPSEEK_API_KEY`` to
   the PRIMARY key source and raises ``RuntimeError`` when the env var is unset
   and the on-disk value is the placeholder / ``None`` / empty.
3. The ``DEEPSEEK_MODEL`` override path is preserved by the rewrite.
4. A placeholder never reaches the OpenAI client — the error fires in
   ``MacroConfig`` construction, before any SDK call.

Deterministic and network-free. Uses a FAKE env key; never a real one.
"""
import json
import re
import sys
from pathlib import Path

import pytest

# Make src/ importable without depending on package install state.
# This is the documented test-shim exception (tests/test_settings.py:18,
# tests/test_macro_strategist.py:26).

from macro.config import MacroConfig  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PLACEHOLDER = "REPLACE_WITH_DEEPSEEK_API_KEY"
# A FAKE key — never a real DeepSeek credential.
FAKE_ENV_KEY = "sk-fake-env-not-real-12345"

_SK_KEY_RE = re.compile(r"^sk-[A-Za-z0-9]{20,}$")


def _load_models_config():
    """Load the shipped models_config.json from the project root."""
    with open(PROJECT_ROOT / "models_config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def _build_config_with_key(api_key):
    """Build a MacroConfig without touching models_config.json or env.

    Mirrors the ``__new__`` bypass pattern in
    ``tests/test_macro_strategist.py:43-59``, then invokes
    ``_apply_runtime_overrides`` so the env-promotion / RuntimeError logic is
    exercised. ``DEEPSEEK_API_KEY`` must be controlled by the caller via
    monkeypatch.
    """
    cfg = MacroConfig.__new__(MacroConfig)
    cfg.tech_proxy = "QQQ"
    cfg.tech_name = "科技股(纳指)"
    cfg.safe_haven_proxy = "GLD"
    cfg.safe_name = "避险黄金"
    cfg.crypto_proxy = "BTC-USD"
    cfg.crypto_name = "数字货币"
    cfg.target_asset = "000300.SS"
    cfg.target_name = "A股核心(沪深300)"
    cfg.lookback_days = 120
    cfg.volatility_window = 20
    cfg.api_key = api_key
    cfg.base_url = "https://api.deepseek.com"
    cfg.model = "deepseek-chat"
    cfg.proxy_url = None
    cfg.proxy_enabled = False
    cfg._apply_runtime_overrides()
    return cfg


# ---------------------------------------------------------------------------
# 1. On-disk placeholder contract
# ---------------------------------------------------------------------------
class TestModelsConfigShipsPlaceholder:
    def test_models_config_json_ships_placeholder_not_real_key(self):
        # Arrange
        data = _load_models_config()
        profiles = data["profiles"]

        # Assert — both DeepSeek profiles carry the sentinel, not a real key
        deepseek_profiles = [p for p in profiles if "DeepSeek" in p["name"]]
        assert len(deepseek_profiles) == 2
        for p in deepseek_profiles:
            assert p["api_key"] == PLACEHOLDER

        # The LM Studio profile token is untouched (not a secret)
        lm_profiles = [p for p in profiles if "LM Studio" in p["name"]]
        assert len(lm_profiles) == 1
        assert lm_profiles[0]["api_key"] == "lm-studio"

    def test_no_sk_prefixed_key_in_models_config_json(self):
        """Regression guard: no field anywhere in models_config.json looks like
        a real DeepSeek ``sk-...`` key."""
        # Arrange
        data = _load_models_config()

        def walk(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    yield from walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    yield from walk(v)
            else:
                yield obj

        # Assert — no scalar value matches the real-key shape
        offenders = [v for v in walk(data)
                     if isinstance(v, str) and _SK_KEY_RE.match(v)]
        assert offenders == [], (
            f"models_config.json contains a real-looking sk- key: {offenders}"
        )

    def test_template_uses_same_sentinel(self):
        """Both on-disk config and template share one placeholder pattern so
        grep-based scanners have a single signal."""
        with open(PROJECT_ROOT / "models_config.template.json",
                  "r", encoding="utf-8") as f:
            template = json.load(f)
        deepseek = [p for p in template["profiles"]
                    if "DeepSeek" in p["name"]]
        for p in deepseek:
            assert p["api_key"] == PLACEHOLDER


# ---------------------------------------------------------------------------
# 2. Env-promotion + RuntimeError contract in _apply_runtime_overrides
# ---------------------------------------------------------------------------
class TestMacroConfigEnvPromotion:
    def test_macroconfig_uses_env_var_when_set(self, monkeypatch):
        # Arrange — env var set and non-empty wins over the JSON value
        monkeypatch.setenv("DEEPSEEK_API_KEY", FAKE_ENV_KEY)

        # Act
        cfg = _build_config_with_key(api_key=PLACEHOLDER)

        # Assert — env value is used, not the placeholder
        assert cfg.api_key == FAKE_ENV_KEY

    def test_macroconfig_raises_when_env_unset_and_placeholder_present(
        self, monkeypatch
    ):
        # Arrange — env unset, on-disk value is the placeholder
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        # Act / Assert — RuntimeError (not print-and-continue)
        with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
            _build_config_with_key(api_key=PLACEHOLDER)

    def test_macroconfig_raises_when_env_unset_and_key_none(
        self, monkeypatch
    ):
        # Arrange — env unset, on-disk value is None
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        # Act / Assert
        with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
            _build_config_with_key(api_key=None)

    def test_macroconfig_raises_when_env_unset_and_key_empty(
        self, monkeypatch
    ):
        # Arrange — env unset, on-disk value is empty string
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        # Act / Assert — no silent print-and-continue (old behavior gone)
        with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
            _build_config_with_key(api_key="")


# ---------------------------------------------------------------------------
# 3. Model-override path preserved
# ---------------------------------------------------------------------------
class TestMacroConfigModelOverridePreserved:
    def test_macroconfig_model_override_preserved(self, monkeypatch):
        # Arrange — both env vars set
        monkeypatch.setenv("DEEPSEEK_API_KEY", FAKE_ENV_KEY)
        monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")

        # Act
        cfg = _build_config_with_key(api_key=PLACEHOLDER)

        # Assert — model override path (config.py DEEPSEEK_MODEL) intact
        assert cfg.model == "deepseek-reasoner"
        assert cfg.api_key == FAKE_ENV_KEY


# ---------------------------------------------------------------------------
# 4. Placeholder never reaches the OpenAI constructor
# ---------------------------------------------------------------------------
class TestPlaceholderNeverReachesOpenAI:
    def test_placeholder_does_not_reach_openai_constructor(self, monkeypatch):
        """With env unset and a placeholder in JSON, DeepSeekStrategist must
        fail to construct because MacroConfig raises before the OpenAI()
        call site is reached."""
        # Arrange — import lazily so the macro package path is set up first
        from macro.strategist import DeepSeekStrategist

        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        # A MacroConfig that would carry the placeholder. We cannot construct
        # one normally (it raises), so build the raw object then assert that
        # calling _apply_runtime_overrides raises before strategist can use it.
        cfg = MacroConfig.__new__(MacroConfig)
        cfg.api_key = PLACEHOLDER
        cfg.base_url = "https://api.deepseek.com"
        cfg.model = "deepseek-chat"

        # Act / Assert — the error fires in config resolution, not at SDK time
        with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
            cfg._apply_runtime_overrides()

        # Sanity: DeepSeekStrategist itself is never reached when the config
        # raises (it consumes config.api_key at __init__).
        with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
            # This builds a fresh MacroConfig via __post_init__ which reads the
            # placeholder from models_config.json and raises.
            DeepSeekStrategist(MacroConfig())
