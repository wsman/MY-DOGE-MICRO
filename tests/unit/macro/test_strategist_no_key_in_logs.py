"""Unit test for S002-013 / ADR-0005 decision item 2 — the API key is never
printed or logged.

When the OpenAI client raises (simulated provider/transport failure), the
strategist catches the exception and returns ``None``. The error path must not
emit the API key into any log record, even though the key is in scope on the
``DeepSeekStrategist`` instance and on the captured exception.

Deterministic and network-free. Uses a FAKE key; never a real one.
"""
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

# Make src/ importable (documented test-shim exception).

from macro.config import MacroConfig  # noqa: E402
from macro.data_loader import GlobalMacroLoader  # noqa: E402
from macro.strategist import DeepSeekStrategist  # noqa: E402

# A FAKE key — never a real DeepSeek credential. Distinctive so any leak is
# obvious in captured records.
FAKE_KEY = "sk-fake-test-key-not-real-1234567890"


def _build_config_with_fake_key():
    """Build a MacroConfig carrying a FAKE key, bypassing JSON + env.

    Mirrors ``tests/test_macro_strategist.py:43-59``.
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
    cfg.api_key = FAKE_KEY
    cfg.base_url = "https://api.deepseek.com"
    cfg.model = "deepseek-chat"
    cfg.proxy_url = None
    cfg.proxy_enabled = False
    return cfg


def _build_market_data(days=120):
    """Deterministic synthetic multi-asset price frame with a DatetimeIndex."""
    idx = pd.bdate_range(end="2026-06-10", periods=days)
    rng = np.arange(days)
    data = {
        "QQQ": 100.0 + rng * 0.20,
        "GLD": 180.0 + np.sin(rng / 7.0) * 1.5,
        "BTC-USD": 30000.0 + rng * 50.0 + np.sin(rng / 3.0) * 500.0,
        "000300.SS": 4000.0 + rng * 1.5,
    }
    return pd.DataFrame(data, index=idx)


def _build_metrics(cfg):
    """Minimal metrics dict the strategist accepts."""
    return {
        "metadata_days": 120,
        "rsrs": {"tech": 0.5, "safe": -0.2, "crypto": 0.1, "target": 0.3},
        "volatility": {"tech": 0.18, "safe": 0.05, "crypto": 0.6, "target": 0.12},
    }


class TestStrategistNeverLogsApiKey:
    def test_generate_report_failure_does_not_log_api_key(
        self, monkeypatch, tmp_path, caplog
    ):
        # Arrange — strategist with a mocked client that raises on call.
        # The exception message deliberately DOES embed the fake key, so a
        # naive error path that logs the exception would leak it.
        monkeypatch.chdir(tmp_path)
        cfg = _build_config_with_fake_key()
        strategist = DeepSeekStrategist(cfg)
        strategist.client = MagicMock()
        strategist.client.chat.completions.create.side_effect = RuntimeError(
            f"auth failed for key={FAKE_KEY}"
        )

        market_data = _build_market_data()
        metrics = _build_metrics(cfg)

        # Act — capture all log records at DEBUG+ across the macro logger
        with caplog.at_level(logging.DEBUG, logger="macro.strategist"):
            result = strategist.generate_strategy_report(metrics, market_data)

        # Assert — degraded sentinel, no raise (ADR-0005 decision item 4)
        assert result is None

        # Assert — the FAKE key string appears in NO emitted record (ADR-0005
        # decision item 2: the key is never printed or logged)
        for record in caplog.records:
            assert FAKE_KEY not in record.getMessage(), (
                f"API key leaked into log record: {record.getMessage()!r}"
            )
        # Belt-and-braces across the full captured text
        assert FAKE_KEY not in caplog.text


class TestMacroConfigReprNeverLeaksApiKey:
    def test_repr_masks_api_key_when_present(self):
        cfg = _build_config_with_fake_key()
        repr_str = repr(cfg)
        assert FAKE_KEY not in repr_str, (
            f"API key leaked into MacroConfig.__repr__: {repr_str!r}"
        )
        assert "api_key='***'" in repr_str, (
            f"Expected redacted api_key marker in repr, got: {repr_str!r}"
        )

    def test_repr_shows_none_when_key_absent(self):
        cfg = _build_config_with_fake_key()
        cfg.api_key = None
        repr_str = repr(cfg)
        assert "api_key=None" in repr_str, (
            f"Expected api_key=None in repr when key absent, got: {repr_str!r}"
        )


class TestGlobalMacroLoaderInitNeverLogsApiKey:
    def test_loader_init_log_does_not_contain_api_key(self, caplog):
        cfg = _build_config_with_fake_key()
        with caplog.at_level(logging.DEBUG, logger="macro.data_loader"):
            GlobalMacroLoader(cfg)
        assert FAKE_KEY not in caplog.text, (
            f"API key leaked into data_loader logs: {caplog.text!r}"
        )
        for record in caplog.records:
            assert FAKE_KEY not in record.getMessage(), (
                f"API key leaked into data_loader log record: "
                f"{record.getMessage()!r}"
            )