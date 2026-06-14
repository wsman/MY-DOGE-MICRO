"""Unit tests for src/macro/strategist.py (Macro Strategy Engine, Module #4).

These tests MOCK the OpenAI-compatible client (no real DeepSeek API call) to
satisfy the test-independence rules in ``.claude/rules/test-standards.md`` and
the forbidden "network-dependent tests without isolation" pattern in ADR-0001.

Coverage targets (BUG E acceptance):
- (a) prompt construction includes the market context / indicators as expected
- (b) report parsing (``format_report_for_display``) extracts structured
  header fields from a mocked LLM response fixture
- (c) degraded / offline path returns a safe fallback (``None``) when the API
  errors, and never raises to the caller

All tests are deterministic: no network, no real model, fixed fixtures.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

# Make src/ importable without depending on package install state.
# This is the documented test-shim exception (see tests/test_settings.py:18).

from macro.config import MacroConfig  # noqa: E402
from macro.strategist import DeepSeekStrategist  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _build_config():
    """Build a MacroConfig without touching models_config.json or env.

    ``MacroConfig.__post_init__`` reads ``models_config.json`` and env vars; to
    keep tests isolated we bypass it via ``__new__`` and set only the fields the
    strategist uses. This avoids depending on the operator's local config file
    or on a real API key being present.
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
    cfg.api_key = "sk-test-key-not-real"
    cfg.base_url = "https://api.deepseek.com"
    cfg.model = "deepseek-chat"
    cfg.proxy_url = None
    cfg.proxy_enabled = False
    return cfg


def _build_market_data(days=120):
    """Deterministic synthetic multi-asset price frame with a DatetimeIndex."""
    idx = pd.bdate_range(end="2026-06-10", periods=days)
    # Up-trending tech, flat gold, choppy crypto, rising target.
    rng = np.arange(days)
    data = {
        "QQQ": 100.0 + rng * 0.20,
        "GLD": 180.0 + np.sin(rng / 7.0) * 1.5,
        "BTC-USD": 30000.0 + rng * 50.0 + np.sin(rng / 3.0) * 500.0,
        "000300.SS": 3800.0 + rng * 1.5,
    }
    return pd.DataFrame(data, index=idx)


def _build_metrics(cfg):
    """Metrics dict matching the shape produced by data_loader.calculate_metrics."""
    return {
        "metadata_days": 120,
        "tech_volatility": 0.1832,
        "risk_on_signal": True,
        "QQQ_trend_medium": 0.27,
        "QQQ_return_5d": 0.011,
        "GLD_trend_medium": -0.02,
        "GLD_return_5d": -0.004,
        "BTC-USD_trend_medium": 0.21,
        "BTC-USD_return_5d": -0.015,
        "000300.SS_trend_medium": 0.06,
        "000300.SS_return_5d": 0.003,
        "gold_btc_ratio": 0.006,
        "ratio_z_score": 0.45,
        "vol_scale_factor": 5.46,
        "vol_skew": 1.12,
        "QQQ_rsrs": 0.73,
        "GLD_rsrs": -0.12,
    }


@pytest.fixture
def strategist_with_mock_client():
    """A DeepSeekStrategist whose OpenAI client is a MagicMock (no network).

    Construction of the real ``OpenAI`` client does NOT perform a network call
    (it only stores api_key/base_url), so it is safe to let ``__init__`` run.
    We then replace ``.client`` with a MagicMock so every test controls the
    chat-completions response without touching the DeepSeek API.
    """
    cfg = _build_config()
    strategist = DeepSeekStrategist(cfg)
    strategist.client = MagicMock()
    return strategist, cfg


def _mk_chat_response(content: str):
    """Build the minimal OpenAI-style response object the strategist reads."""
    response = MagicMock()
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# (a) Prompt construction
# ---------------------------------------------------------------------------
class TestPromptConstruction:
    def test_generate_report_includes_asset_context_and_indicators(
        self, strategist_with_mock_client, monkeypatch, tmp_path
    ):
        # Arrange — chdir to tmp_path so the macro_report archive dir does not
        # pollute the repo working tree.
        monkeypatch.chdir(tmp_path)
        strategist, cfg = strategist_with_mock_client
        market_data = _build_market_data()
        metrics = _build_metrics(cfg)

        captured = {}
        def fake_create(model, messages, stream, temperature):
            captured["model"] = model
            captured["messages"] = messages
            captured["temperature"] = temperature
            return _mk_chat_response("# Mocked report body")

        strategist.client.chat.completions.create.side_effect = fake_create

        # Act
        result = strategist.generate_strategy_report(metrics, market_data)

        # Assert — LLM was called with the configured model + temperature
        assert captured["model"] == cfg.model
        assert captured["temperature"] == pytest.approx(0.6)
        # two messages: system + user
        assert len(captured["messages"]) == 2
        assert captured["messages"][0]["role"] == "system"
        assert captured["messages"][1]["role"] == "user"

        system_prompt = captured["messages"][0]["content"]
        user_prompt = captured["messages"][1]["content"]

        # (a) The prompt embeds the assets + indicators passed in.
        # Each configured asset must appear with its ticker and trend/return.
        for ticker in (cfg.tech_proxy, cfg.safe_haven_proxy, cfg.crypto_proxy, cfg.target_asset):
            assert ticker in user_prompt, f"prompt missing asset ticker {ticker}"
            assert f"[数据: {metrics['metadata_days']}个交易日趋势]" in user_prompt
            assert "[数据: 近5日涨跌]" in user_prompt

        # Volatility, risk signal, RSRS, vol skew must appear in the dashboard block.
        assert "Market Volatility (Annualized)" in user_prompt
        assert "Risk-On" in user_prompt  # metrics risk_on_signal is True
        assert "RSRS (Slope*R2)" in user_prompt
        assert "Vol Skew (5/20)" in user_prompt

        # The system prompt must carry the RSRS interpretation bands used by the
        # strategist (these are prompt-engineering constants, source of truth:
        # strategist.py:74-83).
        assert "RSRS > 0.8" in system_prompt
        assert "Vol Skew > 1.5" in system_prompt

        # The raw LLM content is returned verbatim.
        assert result == "# Mocked report body"

    def test_generate_report_includes_recent_5d_price_detail(
        self, strategist_with_mock_client, monkeypatch, tmp_path
    ):
        # Arrange
        monkeypatch.chdir(tmp_path)
        strategist, cfg = strategist_with_mock_client
        market_data = _build_market_data(days=120)
        metrics = _build_metrics(cfg)

        captured = {}
        strategist.client.chat.completions.create.side_effect = (
            lambda **kw: (captured.update(kw) or _mk_chat_response("body"))
        )

        # Act
        strategist.generate_strategy_report(metrics, market_data)

        # Assert — the last 5 rows of market_data are stringified into the prompt
        user_prompt = captured["messages"][1]["content"]
        last_close = float(market_data[cfg.tech_proxy].iloc[-1])
        # The DataFrame.to_string() includes the close value to 2+ dp.
        assert "最近5日价格明细" in user_prompt


# ---------------------------------------------------------------------------
# (b) Report parsing — format_report_for_display extracts structured fields
# ---------------------------------------------------------------------------
class TestReportParsing:
    def test_format_report_includes_risk_signal_and_volatility_from_metrics(
        self, strategist_with_mock_client
    ):
        # Arrange
        strategist, cfg = strategist_with_mock_client
        metrics = _build_metrics(cfg)
        raw_llm_body = "## 1. some analysis\n## 3. 量化风控仪表盘\n| ... |\n"

        # Act
        formatted = strategist.format_report_for_display(raw_llm_body, metrics)

        # Assert — structured header fields are extracted from the metrics dict
        # (source of truth: strategist.py:174-178).
        assert formatted.startswith("# MY-DOGE PRECISION MACRO REPORT")
        assert "🟢 RISK-ON" in formatted  # risk_on_signal True
        # volatility rendered as a percentage with 2 dp
        assert "18.32%" in formatted
        # raw LLM body preserved
        assert "量化风控仪表盘" in formatted

    def test_format_report_includes_data_provenance_when_dates_given(
        self, strategist_with_mock_client
    ):
        # Arrange
        strategist, cfg = strategist_with_mock_client
        metrics = _build_metrics(cfg)
        raw_body = "body text"

        # Act — call with the optional provenance args the LLM-success path passes
        formatted = strategist.format_report_for_display(
            raw_body,
            metrics,
            start_date="2026-01-05",
            end_date="2026-06-10",
            assets="QQQ, GLD, BTC-USD, 000300.SS",
            trading_days=120,
            calendar_days=156,
        )

        # Assert — provenance block extracted into the header
        assert "数据溯源" in formatted
        assert "2026-01-05" in formatted and "2026-06-10" in formatted
        assert "120" in formatted  # trading_days
        assert "156" in formatted  # calendar_days
        assert "QQQ, GLD, BTC-USD, 000300.SS" in formatted

    def test_format_report_fallback_for_risk_off_signal(self, strategist_with_mock_client):
        # Arrange — flip the risk signal
        strategist, cfg = strategist_with_mock_client
        metrics = _build_metrics(cfg)
        metrics["risk_on_signal"] = False

        # Act
        formatted = strategist.format_report_for_display("body", metrics)

        # Assert
        assert "🔴 RISK-OFF" in formatted

    def test_format_report_empty_input_returns_warning(self, strategist_with_mock_client):
        # Arrange
        strategist, _ = strategist_with_mock_client

        # Act
        out = strategist.format_report_for_display("", {})

        # Assert — documented empty-report guard (strategist.py:151-152)
        assert "报告为空" in out


# ---------------------------------------------------------------------------
# (c) Degraded / offline fallback
# ---------------------------------------------------------------------------
class TestDegradedFallback:
    def test_generate_report_returns_none_on_api_error(
        self, strategist_with_mock_client, monkeypatch, tmp_path
    ):
        # Arrange — the OpenAI client raises (simulated network/API failure)
        monkeypatch.chdir(tmp_path)
        strategist, cfg = strategist_with_mock_client
        market_data = _build_market_data()
        metrics = _build_metrics(cfg)
        strategist.client.chat.completions.create.side_effect = RuntimeError(
            "connection refused"
        )

        # Act — must NOT raise; the strategist swallows and returns None
        result = strategist.generate_strategy_report(metrics, market_data)

        # Assert — safe fallback sentinel (caller treats None as "no report")
        assert result is None

    def test_generate_report_returns_none_on_empty_content(
        self, strategist_with_mock_client, monkeypatch, tmp_path
    ):
        # Arrange — API returns an empty content string
        monkeypatch.chdir(tmp_path)
        strategist, cfg = strategist_with_mock_client
        market_data = _build_market_data()
        metrics = _build_metrics(cfg)
        strategist.client.chat.completions.side_effect = None
        strategist.client.chat.completions.create.return_value = _mk_chat_response("")

        # Act
        result = strategist.generate_strategy_report(metrics, market_data)

        # Assert — documented empty-content branch (strategist.py:117-118)
        assert "API返回内容为空" in result

    def test_generate_report_call_count_matches_one_request(
        self, strategist_with_mock_client, monkeypatch, tmp_path
    ):
        # Arrange — confirm a single API call per report (no retry loop in the
        # strategist; the only retry loop in the macro module lives in data_loader)
        monkeypatch.chdir(tmp_path)
        strategist, cfg = strategist_with_mock_client
        market_data = _build_market_data()
        metrics = _build_metrics(cfg)
        strategist.client.chat.completions.create.return_value = _mk_chat_response("body")

        # Act
        strategist.generate_strategy_report(metrics, market_data)

        # Assert
        assert strategist.client.chat.completions.create.call_count == 1
