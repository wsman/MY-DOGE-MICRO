"""BLOCKING parity tests: the macro duplicate ``GlobalMacroLoader.calculate_rsrs``
(``src/macro/data_loader.py``) is in guard-parity with the canonical Module #5
``MomentumRanker.calculate_rsrs`` (``src/micro/momentum_scanner.py``).

Before S002-002 the macro copy LACKED both the flat-variance guard and the
residual-NaN safety net the canonical copy has, so a flat / halted / stablecoin
price series produced ``NaN`` (scipy returns r_value=NaN on zero-variance y),
which then propagated into ``calculate_metrics`` and the DeepSeek strategist
prompt as the literal 'nan'. S002-002 adds the guards and unifies the sign
convention (zero -> +1) with the canonical path.

Coverage targets (per S002-002 acceptance):
  (a) flat constant series     -> 0.0 (was NaN before the fix)
  (b) near-flat below guard    -> 0.0
  (c) short series < window    -> 0.0 (length guard, already present)
  (d) monotonic increasing     -> > 0 (~ +1.0)
  (e) monotonic decreasing     -> < 0 (~ -1.0)
  (f) PARITY WITH CANONICAL    -> battery of 20 deterministic series where
       macro.calculate_rsrs == MomentumRanker().calculate_rsrs to 1e-9 (BLOCKING)
  (g) result always finite, in [-1.0, 1.0]
  (h) calculate_metrics emits FINITE *_rsrs keys on flat data (no NaN -> prompt)
  (i) sign convention matches canonical at {-1.0, 0.0, +1.0}

The loader is built via the MacroConfig.__new__ bypass (no network / no file
read), the same pattern as tests/test_macro_strategist.py:43-59.

Determinism: pure numeric, no network.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Test-shim exception (documented in test_settings.py): make src/ importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from macro.config import MacroConfig  # noqa: E402
from macro.data_loader import GlobalMacroLoader  # noqa: E402
from micro.momentum_scanner import MomentumRanker  # noqa: E402


# ---------------------------------------------------------------------------
# Config / loader construction WITHOUT touching models_config.json or env.
# Mirrors the MacroConfig.__new__ bypass in tests/test_macro_strategist.py:43-59.
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


@pytest.fixture(scope="module")
def loader() -> GlobalMacroLoader:
    return GlobalMacroLoader(_build_config())


@pytest.fixture(scope="module")
def canonical() -> MomentumRanker:
    return MomentumRanker()


# ---------------------------------------------------------------------------
# (a) flat constant series -> 0.0 (regression: was NaN before the guard)
# ---------------------------------------------------------------------------
def test_flat_constant_series_returns_zero_not_nan(loader):
    # Arrange
    series = pd.Series([180.0] * 20)
    # Act
    result = loader.calculate_rsrs(series)
    # Assert — exactly 0.0, NOT nan. Before S002-002 this returned NaN.
    assert result == pytest.approx(0.0, abs=1e-12)
    assert result == result, "calculate_rsrs returned NaN on a flat series"


# ---------------------------------------------------------------------------
# (b) near-flat below the 1e-10 variance guard -> 0.0
# ---------------------------------------------------------------------------
def test_near_flat_below_variance_guard_returns_zero(loader):
    rng = np.random.default_rng(7)
    series = pd.Series(rng.normal(180.0, 1e-8, size=20))
    assert float(np.var(series.iloc[-18:].values)) <= 1e-10
    result = loader.calculate_rsrs(series)
    assert result == pytest.approx(0.0, abs=1e-12)
    assert result == result


# ---------------------------------------------------------------------------
# (c) short series (< window) -> 0.0 (length guard, pin it)
# ---------------------------------------------------------------------------
def test_short_series_below_window_returns_zero(loader):
    series = pd.Series(np.arange(1, 11, dtype=float))  # 10 bars < 18
    assert loader.calculate_rsrs(series) == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# (d) monotonic increasing -> > 0 (perfect ramp -> +1.0)
# ---------------------------------------------------------------------------
def test_monotonic_increasing_returns_positive(loader):
    series = pd.Series(np.arange(1, 25, dtype=float))
    result = loader.calculate_rsrs(series)
    assert result > 0
    assert result == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# (e) monotonic decreasing -> < 0 (perfect decline -> -1.0)
# ---------------------------------------------------------------------------
def test_monotonic_decreasing_returns_negative(loader):
    series = pd.Series(np.arange(25, 1, -1, dtype=float))
    result = loader.calculate_rsrs(series)
    assert result < 0
    assert result == pytest.approx(-1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# (f) BLOCKING parity battery: macro == canonical on 20 deterministic series.
# This is the regression guard that the two copies cannot drift again.
# ---------------------------------------------------------------------------
def _parity_battery() -> list[tuple[str, pd.Series]]:
    """20 deterministic series spanning flat / ramp / V-shape / noisy up+down /
    near-flat / mixed. Names identify the shape for failure messages."""
    rng = np.random.default_rng(2024)
    n = 30
    series_list: list[tuple[str, pd.Series]] = []
    series_list.append(("flat", pd.Series([50.0] * n)))
    series_list.append(("ramp_up", pd.Series(np.arange(1, n + 1, dtype=float))))
    series_list.append(("ramp_down", pd.Series(np.arange(n, 0, -1, dtype=float))))
    # Palindromic V-shape (zero slope, nonzero variance) — left half descends,
    # right half mirrors -> cov(time, value) == 0.
    half = n // 2
    left = np.arange(half, 0, -1, dtype=float)
    v = np.concatenate([left, left[::-1]])
    series_list.append(("v_shape_palindromic", pd.Series(v)))
    series_list.append(("noisy_uptrend", pd.Series(np.arange(n, dtype=float) + rng.normal(0, 0.5, n))))
    series_list.append(("noisy_downtrend", pd.Series(np.arange(n, 0, -1, dtype=float) + rng.normal(0, 0.5, n))))
    series_list.append(("near_flat", pd.Series(rng.normal(100.0, 1e-8, n))))  # trips guard
    series_list.append(("step_up", pd.Series([10.0] * (n // 2) + [20.0] * (n - n // 2))))
    series_list.append(("step_down", pd.Series([20.0] * (n // 2) + [10.0] * (n - n // 2))))
    series_list.append(("sine", pd.Series(50.0 + 5.0 * np.sin(np.arange(n) * 0.5))))
    series_list.append(("noisy_flat", pd.Series(50.0 + rng.normal(0, 2.0, n))))
    series_list.append(("exp_up", pd.Series(np.geomspace(1.0, 64.0, n))))
    series_list.append(("exp_down", pd.Series(np.geomspace(64.0, 1.0, n))))
    series_list.append(("single_spike", pd.Series(list(np.full(n - 1, 50.0)) + [80.0])))
    series_list.append(("single_dip", pd.Series(list(np.full(n - 1, 50.0)) + [20.0])))
    series_list.append(("mild_uptrend", pd.Series(50.0 + 0.1 * np.arange(n))))
    series_list.append(("mild_downtrend", pd.Series(50.0 - 0.1 * np.arange(n))))
    series_list.append(("w_shape", pd.Series(np.tile([10.0, 30.0, 10.0, 30.0, 10.0], n // 5 + 1)[:n])))
    series_list.append(("big_positive_drift", pd.Series(100.0 + 5.0 * np.arange(n) + rng.normal(0, 1.0, n))))
    series_list.append(("big_negative_drift", pd.Series(100.0 - 5.0 * np.arange(n) + rng.normal(0, 1.0, n))))
    assert len(series_list) == 20
    return series_list


@pytest.mark.parametrize("name,series", _parity_battery())
def test_parity_with_canonical_momentum_scanner(loader, canonical, name, series):
    # Act
    macro_rsrs = loader.calculate_rsrs(series)
    canonical_rsrs = canonical.calculate_rsrs(series)
    # Assert — BLOCKING: the two copies cannot differ by more than 1e-9.
    assert macro_rsrs == pytest.approx(canonical_rsrs, abs=1e-9), (
        f"parity drift on series '{name}': macro={macro_rsrs} canonical={canonical_rsrs}"
    )


# ---------------------------------------------------------------------------
# (g) result always finite and in [-1.0, 1.0] over 30 random series
# ---------------------------------------------------------------------------
def test_result_always_finite_in_unit_range(loader):
    rng = np.random.default_rng(31337)
    for _ in range(30):
        series = pd.Series(rng.normal(100.0, rng.uniform(0.1, 20.0), size=25))
        result = loader.calculate_rsrs(series)
        assert result == result, f"NaN result on series {series.tolist()}"
        assert np.isfinite(result)
        assert -1.0 <= result <= 1.0, f"result {result} out of [-1,1]"


# ---------------------------------------------------------------------------
# (h) calculate_metrics emits FINITE *_rsrs keys on flat data (no NaN -> prompt)
# ---------------------------------------------------------------------------
def test_calculate_metrics_includes_finite_rsrs_keys_on_flat_data(loader):
    # Arrange — a multi-asset frame whose tech_proxy (QQQ) is FLAT-CONSTANT over
    # the LAST 18 bars (the RSRS regression window — the slice calculate_rsrs
    # reads), but has small movement earlier so the advanced-metrics columns
    # (log_ret, ann_vol, vol_scale_factor, vol_skew) are not all-NaN after
    # dropna and the RSRS block actually runs. We need all of [tech_proxy,
    # safe_haven_proxy, crypto_proxy, target_asset] present and >
    # volatility_window (20) rows after dropna.
    n = 60
    idx = pd.bdate_range(end="2026-06-12", periods=n)
    rng = np.random.default_rng(1)
    qqq = np.empty(n)
    # First 42 bars: mild uptrend so log_ret/ann_vol are finite and non-NaN.
    qqq[: n - 18] = 170.0 + np.cumsum(rng.normal(0, 0.5, n - 18))
    # Last 18 bars: FLAT-CONSTANT at the final value of the ramp (was NaN pre-fix).
    qqq[n - 18 :] = qqq[n - 19]
    data = pd.DataFrame(
        {
            loader.config.tech_proxy: qqq,
            loader.config.safe_haven_proxy: 100.0 + rng.normal(0, 1.0, n),
            loader.config.crypto_proxy: 30000.0 + rng.normal(0, 100.0, n),
            loader.config.target_asset: 3800.0 + rng.normal(0, 5.0, n),
        },
        index=idx,
    )

    # Act
    metrics = loader.calculate_metrics(data)

    # Assert — the tech_proxy rsrs key exists, is finite, and is 0.0 (not NaN).
    tech_key = f"{loader.config.tech_proxy}_rsrs"
    assert tech_key in metrics, f"{tech_key} missing from metrics: {sorted(metrics)}"
    assert metrics[tech_key] == metrics[tech_key], f"{tech_key} is NaN: {metrics[tech_key]}"
    assert np.isfinite(metrics[tech_key])
    assert metrics[tech_key] == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# (i) sign convention matches canonical at {-1.0, 0.0, +1.0}
# Ties S002-002 to S002-001's chosen convention.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("slope", [-1.0, 0.0, 1.0])
def test_sign_convention_matches_canonical(loader, canonical, slope):
    """The macro and canonical sign helpers must agree at the boundary values,
    especially slope==0 -> +1 (the unified S002-001 convention). We probe via a
    constructed series whose last-18 OLS slope equals the requested value."""
    # Build an 18-bar series with the exact requested OLS slope: y = slope * x.
    x = np.arange(18, dtype=float)
    y = slope * x + 100.0
    series = pd.Series(y)

    macro_sign = loader.calculate_rsrs(series)
    canonical_sign = canonical.calculate_rsrs(series)
    assert macro_sign == pytest.approx(canonical_sign, abs=1e-9)
    # And the zero-slope case must be POSITIVE under the unified convention
    # (slope==0 -> +1, but R2==0 so the product is 0.0 — the boundary itself is
    # pinned by tests/unit/momentum/test_rsrs_sign_unit.py).
    if slope == 0.0:
        assert macro_sign == pytest.approx(0.0, abs=1e-9)
