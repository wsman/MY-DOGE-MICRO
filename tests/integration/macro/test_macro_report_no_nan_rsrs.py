"""BLOCKING integration test: a flat-asset macro frame flows through
``GlobalMacroLoader.calculate_metrics`` -> ``DeepSeekStrategist.generate_strategy_report``
and the captured LLM prompt contains a FINITE RSRS value and NEVER the literal
'nan' (S002-002).

Before S002-002 the macro ``calculate_rsrs`` lacked the flat-variance guard, so
a flat / halted / stablecoin price series produced ``NaN``; that NaN propagated
into ``metrics['<tech_proxy>_rsrs']`` and was rendered into the DeepSeek
strategist dashboard table as the literal 'nan' via ``f"{tech_rsrs:.2f}"``
(strategist.py:49,57) — corrupting the macro report.

This test closes that NaN-into-LLM-prompt path end-to-end (with the strategist's
OpenAI client mocked — no real API call, no network).

Determinism: no network; mocked LLM client; deterministic synthetic frame.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

# Test-shim exception (documented in test_settings.py): make src/ importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from macro.config import MacroConfig  # noqa: E402
from macro.data_loader import GlobalMacroLoader  # noqa: E402
from macro.strategist import DeepSeekStrategist  # noqa: E402


# ---------------------------------------------------------------------------
# Config / loader construction WITHOUT touching models_config.json or env
# (MacroConfig.__new__ bypass — same as tests/test_macro_strategist.py:43-59).
# ---------------------------------------------------------------------------
def _build_config() -> MacroConfig:
    cfg = MacroConfig.__new__(MacroConfig)
    cfg.tech_proxy = "QQQ"
    cfg.tech_name = "Tech (Nasdaq)"
    cfg.safe_haven_proxy = "GLD"
    cfg.safe_name = "Gold"
    cfg.crypto_proxy = "BTC-USD"
    cfg.crypto_name = "Crypto"
    cfg.target_asset = "000300.SS"
    cfg.target_name = "A-share core (CSI300)"
    cfg.lookback_days = 120
    cfg.volatility_window = 20
    cfg.api_key = "sk-test-key-not-real"
    cfg.base_url = "https://api.deepseek.com"
    cfg.model = "deepseek-chat"
    cfg.proxy_url = None
    cfg.proxy_enabled = False
    return cfg


def _build_flat_tech_market_data(n: int = 60) -> pd.DataFrame:
    """A multi-asset frame whose tech_proxy (QQQ) is FLAT-CONSTANT over the LAST
    18 bars (the RSRS regression window — the slice calculate_rsrs reads), but
    has a mild uptrend earlier so the advanced-metrics columns are not all-NaN
    after dropna and the RSRS block actually runs. This is the input that
    produced NaN before the S002-002 guard. All four assets the strategist
    references are present."""
    idx = pd.bdate_range(end="2026-06-12", periods=n)
    rng = np.random.default_rng(1)
    cfg = _build_config()
    qqq = np.empty(n)
    # First 42 bars: mild uptrend so log_ret/ann_vol are finite and non-NaN.
    qqq[: n - 18] = 170.0 + np.cumsum(rng.normal(0, 0.5, n - 18))
    # Last 18 bars: FLAT-CONSTANT at the final value of the ramp (was NaN pre-fix).
    qqq[n - 18 :] = qqq[n - 19]
    return pd.DataFrame(
        {
            cfg.tech_proxy: qqq,
            cfg.safe_haven_proxy: 100.0 + rng.normal(0, 1.0, n),
            cfg.crypto_proxy: 30000.0 + rng.normal(0, 100.0, n),
            cfg.target_asset: 3800.0 + rng.normal(0, 5.0, n),
        },
        index=idx,
    )


def _mk_chat_response(content: str):
    """Minimal OpenAI-style response object the strategist reads."""
    response = MagicMock()
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response.choices = [choice]
    return response


def test_macro_report_prompt_has_finite_rsrs_and_never_nan(monkeypatch, tmp_path):
    """End-to-end: flat-asset frame -> calculate_metrics -> mocked strategist ->
    the captured user_prompt's RSRS row shows a finite value (e.g. '0.00') and
    the literal 'nan' never appears.

    Regression for the NaN-into-LLM-prompt corruption path (S002-002).
    """
    # Arrange — chdir to tmp_path so the macro_report archive dir does not
    # pollute the repo working tree (same precaution as test_macro_strategist).
    monkeypatch.chdir(tmp_path)
    cfg = _build_config()
    loader = GlobalMacroLoader(cfg)
    strategist = DeepSeekStrategist(cfg)
    strategist.client = MagicMock()

    market_data = _build_flat_tech_market_data()

    # Act 1 — compute metrics from the flat-asset frame (the path that returned
    # NaN *_rsrs keys before S002-002).
    metrics = loader.calculate_metrics(market_data)
    tech_key = f"{cfg.tech_proxy}_rsrs"
    assert tech_key in metrics, f"{tech_key} missing from metrics"
    # Pre-condition: the metrics value is FINITE (this is the S002-002 fix).
    assert metrics[tech_key] == metrics[tech_key], (
        f"calculate_metrics produced NaN {tech_key}={metrics[tech_key]}"
    )
    assert np.isfinite(metrics[tech_key])

    # Act 2 — feed metrics into the strategist with a mocked LLM client. Capture
    # the user_prompt that would have gone to DeepSeek.
    captured = {}

    def fake_create(model, messages, stream, temperature):
        captured["messages"] = messages
        return _mk_chat_response("# Mocked macro report body")

    strategist.client.chat.completions.create.side_effect = fake_create
    strategist.generate_strategy_report(metrics, market_data)

    # Assert — the captured user_prompt exists and contains a FINITE RSRS value
    # in the dashboard row, and NEVER contains the literal 'nan' anywhere.
    assert "messages" in captured, "strategist did not call the LLM client"
    user_prompt = captured["messages"][1]["content"]
    assert "RSRS" in user_prompt or "rsrs" in user_prompt.lower(), (
        "RSRS dashboard row missing from prompt"
    )
    # The RSRS must render as a finite number (0.00 for the flat tech asset),
    # never as the literal 'nan'.
    assert "nan" not in user_prompt.lower(), (
        f"literal 'nan' present in strategist prompt:\n{user_prompt}"
    )
    # The finite RSRS reading should be '0.00' for the flat tech asset.
    assert "0.00" in user_prompt, (
        f"finite RSRS value '0.00' not found in dashboard prompt:\n{user_prompt}"
    )
