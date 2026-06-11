"""Unit tests for the canonical RSRS formula owned by Module #5
(Micro Momentum Scanner).

These tests import the REAL function from ``src/micro/momentum_scanner.py``;
they do not reimplement the formula. Coverage targets (per BUG E acceptance):

  (a) flat / zero-variance series -> rsrs == 0.0
  (b) strictly monotonic increasing -> rsrs > 0
  (c) strictly monotonic decreasing -> rsrs < 0
  (d) len(series) < window          -> returns 0.0 (length guard)
  (e) vectorized batch path matches the scalar path on the same input

Determinism: pure numeric, no network / filesystem / DB.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Test-shim exception (documented in test_settings.py): make src/ importable
# without depending on package install state. momentum_scanner.py lives in
# src/micro/, so we add src/ to sys.path and import from the micro package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from micro.momentum_scanner import MomentumRanker  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture: one ranker instance shared across tests. Construction has no
# filesystem/network side effects beyond reading models_config.json (which is
# guarded by try/except in _load_config and falls back to defaults).
# ---------------------------------------------------------------------------
@pytest.fixture
def ranker():
    return MomentumRanker()


# ---------------------------------------------------------------------------
# (a) Flat / zero-variance series -> rsrs == 0.0
# ---------------------------------------------------------------------------
def test_calculate_rsrs_flat_series_returns_zero(ranker):
    # Arrange — constant price, 20 bars (>= default window 18)
    flat = pd.Series([5.0] * 20)

    # Act
    rsrs = ranker.calculate_rsrs(flat)

    # Assert — zero-variance input has no trend; the length guard passes but
    # the zero-variance guard must short-circuit to 0.0 (not nan).
    assert rsrs == pytest.approx(0.0, abs=1e-12)


def test_calculate_rsrs_near_flat_series_returns_near_zero(ranker):
    # Arrange — tiny noise around a constant; r^2 ~ 0 so |rsrs| ~ 0
    rng = np.random.default_rng(0)
    near_flat = pd.Series(100.0 + rng.normal(0.0, 1e-8, size=20))

    # Act
    rsrs = ranker.calculate_rsrs(near_flat)

    # Assert — variance below the 1e-10 guard trips the zero-variance branch
    assert rsrs == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# (b) Strictly monotonic increasing -> rsrs > 0
# ---------------------------------------------------------------------------
def test_calculate_rsrs_increasing_series_is_positive(ranker):
    # Arrange — perfect ramp, slope > 0
    increasing = pd.Series(np.arange(1, 25, dtype=float))

    # Act
    rsrs = ranker.calculate_rsrs(increasing)

    # Assert — upward trend, R^2 * sign(+slope) > 0; perfect linear fit => 1.0
    assert rsrs > 0.0
    assert rsrs == pytest.approx(1.0, abs=1e-9)


def test_calculate_rsrs_noisy_uptrend_is_strictly_positive(ranker):
    # Arrange — uptrend with mild noise (deterministic seed)
    rng = np.random.default_rng(1)
    x = np.arange(30, dtype=float)
    noisy_up = pd.Series(2.0 * x + 1.0 + rng.normal(0.0, 0.5, size=30))

    # Act
    rsrs = ranker.calculate_rsrs(noisy_up)

    # Assert — positive slope dominates; rsrs must be > 0 but < 1 (not perfect)
    assert rsrs > 0.0
    assert rsrs < 1.0


# ---------------------------------------------------------------------------
# (c) Strictly monotonic decreasing -> rsrs < 0
# ---------------------------------------------------------------------------
def test_calculate_rsrs_decreasing_series_is_negative(ranker):
    # Arrange — perfect decline, slope < 0
    decreasing = pd.Series(np.arange(25, 1, -1, dtype=float))

    # Act
    rsrs = ranker.calculate_rsrs(decreasing)

    # Assert — downward trend, R^2 * sign(-slope) < 0; perfect fit => -1.0
    assert rsrs < 0.0
    assert rsrs == pytest.approx(-1.0, abs=1e-9)


def test_calculate_rsrs_noisy_downtrend_is_strictly_negative(ranker):
    # Arrange — downtrend with mild noise (deterministic seed)
    rng = np.random.default_rng(2)
    x = np.arange(30, dtype=float)
    noisy_down = pd.Series(-3.0 * x + 100.0 + rng.normal(0.0, 0.5, size=30))

    # Act
    rsrs = ranker.calculate_rsrs(noisy_down)

    # Assert — negative slope dominates; rsrs must be < 0 but > -1
    assert rsrs < 0.0
    assert rsrs > -1.0


# ---------------------------------------------------------------------------
# (d) len(series) < window -> returns 0.0 (length guard)
# ---------------------------------------------------------------------------
def test_calculate_rsrs_short_series_returns_zero(ranker):
    # Arrange — 10 bars, below the default window=18
    short = pd.Series(np.arange(1, 11, dtype=float))

    # Act
    rsrs = ranker.calculate_rsrs(short)

    # Assert — length guard short-circuits before linregress is called
    assert rsrs == 0.0


def test_calculate_rsrs_short_series_with_explicit_window_respects_window(ranker):
    # Arrange — 10 bars; if window=5 we have enough, so it must compute
    short = pd.Series(np.arange(1, 11, dtype=float))

    # Act
    rsrs = ranker.calculate_rsrs(short, window=5)

    # Assert — enough data for window=5, strictly increasing => positive
    assert rsrs > 0.0


# ---------------------------------------------------------------------------
# (e) Vectorized batch path matches the scalar path on the same input
# ---------------------------------------------------------------------------
def test_vectorized_path_matches_scalar_path(ranker):
    # Arrange — 100 stocks x 18 bars, deterministic
    rng = np.random.default_rng(42)
    price_matrix = rng.random((100, 18)) * 100

    # Act
    vec_results = ranker._calculate_rsrs_vectorized(price_matrix)
    scalar_results = np.array(
        [ranker.calculate_rsrs(pd.Series(row)) for row in price_matrix]
    )

    # Assert — paths agree to float-epsilon tolerance
    assert vec_results.shape == (100,)
    max_diff = float(np.max(np.abs(vec_results - scalar_results)))
    assert max_diff < 1e-6, f"max diff {max_diff} exceeds 1e-6"


def test_vectorized_path_matches_scalar_path_including_flat_row(ranker):
    # Arrange — include a flat (zero-variance) row to exercise the divergence
    # that previously produced nan in the scalar path and 0.0 in the vectorized
    # path. Regression guard for BUG E.
    rng = np.random.default_rng(7)
    price_matrix = rng.random((50, 18)) * 100
    price_matrix[0] = 3.0  # exactly flat

    # Act
    vec_results = ranker._calculate_rsrs_vectorized(price_matrix)
    scalar_results = np.array(
        [ranker.calculate_rsrs(pd.Series(row)) for row in price_matrix]
    )

    # Assert — both paths yield finite 0.0 for the flat row and agree elsewhere
    assert np.isfinite(vec_results).all()
    assert np.isfinite(scalar_results).all()
    assert vec_results[0] == pytest.approx(0.0, abs=1e-12)
    assert scalar_results[0] == pytest.approx(0.0, abs=1e-12)
    max_diff = float(np.max(np.abs(vec_results - scalar_results)))
    assert max_diff < 1e-6, f"max diff {max_diff} exceeds 1e-6"


# ---------------------------------------------------------------------------
# Output range invariant
# ---------------------------------------------------------------------------
def test_calculate_rsrs_result_is_in_unit_range(ranker):
    # Arrange — assorted deterministic series
    rng = np.random.default_rng(99)
    series_list = [pd.Series(rng.random(30) * 100) for _ in range(20)]

    # Act / Assert — every result must lie in [-1.0, 1.0]
    for s in series_list:
        rsrs = ranker.calculate_rsrs(s)
        assert -1.0 - 1e-9 <= rsrs <= 1.0 + 1e-9, f"out of range: {rsrs}"
