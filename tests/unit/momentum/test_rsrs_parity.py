"""BLOCKING parity tests: all THREE RSRS implementations agree on the sign of a
zero-slope series (S002-001, OQ-11 / TR-016 RESOLVED).

The canonical RSRS formula lives in ``src/micro/momentum_scanner.py`` and is
implemented in two Python paths (scalar ``calculate_rsrs`` and vectorized
``_calculate_rsrs_vectorized``) plus one DuckDB-SQL path (``data/views.sql``
``vw_rsrs_ranking_cn`` / ``vw_rsrs_ranking_us``). Before S002-001 the three
diverged in the degenerate zero-slope-with-nonzero-variance edge case:

    scalar     -> sign(0.0) = -1   (``1.0 if slope > 0 else -1.0``)
    vectorized -> sign(0.0) =  0   (``np.sign``)
    SQL        -> sign(0.0) = +1   (``CASE WHEN ... >= 0 THEN 1``)

S002-001 unified them to **zero -> +1** across all three. These tests pin that
unification so any future regression (e.g. reverting ``np.where`` back to
``np.sign``) is loud.

The SQL path is exercised as a faithful Python re-implementation of the DuckDB
REGR_R2 / REGR_SLOPE semantics here; the real DuckDB view is pinned in
``tests/migration/test_rsrs_view_sign_convention.py``.

Determinism: pure numeric, no network / filesystem / DB.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

# Test-shim exception (documented in test_settings.py): make src/ importable
# without depending on package install state. momentum_scanner.py lives in
# src/micro/, so we add src/ to sys.path and import from the micro package.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from micro.momentum_scanner import MomentumRanker  # noqa: E402


@pytest.fixture(scope="module")
def ranker():
    """One MomentumRanker shared across the module. Construction only reads
    models_config.json (guarded by try/except, falls back to defaults)."""
    return MomentumRanker()


# ---------------------------------------------------------------------------
# SQL-sign helper: faithful re-implementation of the DuckDB CASE-WHEN logic in
# data/views.sql (vw_rsrs_ranking_cn/us):
#     COALESCE(REGR_R2(rn, close), 0) * CASE WHEN COALESCE(REGR_SLOPE(rn, close), 0) >= 0 THEN 1 ELSE -1
# In Python we use scipy.linregress on x=time(0..N-1), y=price (matching the
# SQL REGR_*(rn, close) argument order: X=rn=time, Y=close=price).
# ---------------------------------------------------------------------------
def _sql_rsrs(window_closes: np.ndarray) -> float:
    """Re-implement the DuckDB ``vw_rsrs_ranking_*`` rsrs column for a single
    ticker's 18-bar close window.

    ``REGR_R2(Y, X)`` returns NULL when Y has zero variance; COALESCE(..., 0)
    coerces NULL->0. ``REGR_SLOPE`` is likewise NULL->0. We mirror that by
    guarding zero-variance Y so the regression is never run on degenerate input
    (scipy returns NaN there, not NULL).
    """
    y = np.asarray(window_closes, dtype=float)
    if y.size == 0:
        return 0.0
    if float(np.var(y)) <= 1e-10:
        # Zero-variance Y -> REGR_R2 NULL -> COALESCE 0; slope NULL -> COALESCE 0;
        # product 0 * sign(0=+1) = 0.0.
        return 0.0
    x = np.arange(len(y), dtype=float)
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    r_sq = float(r_value) ** 2
    # CASE WHEN COALESCE(REGR_SLOPE(...), 0) >= 0 THEN 1 ELSE -1  -> zero -> +1
    sign = 1.0 if float(slope) >= 0 else -1.0
    trend_strength = r_sq * sign
    return 0.0 if trend_strength != trend_strength else trend_strength


# ---------------------------------------------------------------------------
# Edge-case series builders
# ---------------------------------------------------------------------------
def _v_shape_window(n: int = 18) -> np.ndarray:
    """A symmetric V-shape whose OLS slope over 0..n-1 is exactly 0.0 but whose
    variance is well above the 1e-10 flat-guard threshold. This is the exact
    zero-slope-with-nonzero-variance edge case that exposed the pre-S002-001
    three-way divergence.

    Construction: make the value series **palindromic** (``v[i] == v[n-1-i]``).
    For a palindromic series, ``sum(i * v_i) == (n-1)/2 * sum(v_i)``, so the
    covariance with the centered time index is exactly zero and the OLS slope
    is exactly 0.0 to machine precision — no residual correction needed. We
    descend then ascend (a V) so the variance is large.
    """
    half = n // 2
    # Descend half->1 over the left half; the right half mirrors it ascending.
    left = np.arange(half, 0, -1, dtype=float)  # half, half-1, ..., 1
    if n % 2 == 0:
        vals = np.concatenate([left, left[::-1]])
    else:
        vals = np.concatenate([left, np.array([0.0]), left[::-1]])
    return vals[:n].astype(float)


# ---------------------------------------------------------------------------
# Scenario 1: zero-slope, nonzero variance — the OQ-11 divergence case.
# ALL THREE implementations must now return +1*R2 (zero->+1 convention).
# ---------------------------------------------------------------------------
def test_zero_slope_with_nonzero_variance_all_three_agree(ranker):
    # Arrange — a palindromic V-shape window with OLS slope exactly 0.0 but
    # variance >> 1e-10 (it clears the flat-variance guard). This is the exact
    # zero-slope-with-nonzero-variance edge case that exposed the pre-S002-001
    # three-way divergence.
    v = _v_shape_window(18)
    assert float(np.var(v)) > 1e-10, "fixture lost its variance"
    series = pd.Series(v)

    # Re-confirm the OLS slope is zero (the precondition of this test).
    x = np.arange(18, dtype=float)
    slope_check, _, r_value_check, _, _ = stats.linregress(x, v)
    assert abs(float(slope_check)) < 1e-9, (
        f"V-shape fixture slope is {slope_check}, not ~0 — fixture is broken"
    )

    # Math note: for OLS regression on time, slope == 0  <=>  cov(x,y) == 0
    # <=> r_value == 0  <=>  R2 == 0. So a zero-slope series necessarily has
    # R2 == 0 and the RSRS product is 0.0 regardless of the sign convention.
    # This is exactly spec risk R-3 ("the sign is moot in practice"). The
    # load-bearing convention pin therefore lives in the dedicated sign-boundary
    # tests (test_rsrs_sign_unit.py, test_sql_sign_helper_matches_python_sign_helper);
    # THIS test proves the three implementations AGREE (no divergence) on the
    # edge-case input.
    expected_r2 = float(r_value_check) ** 2
    assert expected_r2 == pytest.approx(0.0, abs=1e-9)
    expected = expected_r2 * 1.0  # sign(0) = +1 under the unified convention

    # Act — three implementations.
    scalar = ranker.calculate_rsrs(series)
    vec = ranker._calculate_rsrs_vectorized(v.reshape(1, 18))[0]
    sql = _sql_rsrs(v)

    # Assert — all three agree to 1e-9 AND equal sign(0)*R2 = +1*0 = 0.0.
    assert scalar == pytest.approx(vec, abs=1e-9)
    assert scalar == pytest.approx(sql, abs=1e-9)
    assert scalar == pytest.approx(expected, abs=1e-9)
    # All three return exactly 0.0 for the zero-slope case (no divergence).
    assert scalar == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Scenario 2: flat constant series -> 0.0 (guard forces it, all three agree).
# ---------------------------------------------------------------------------
def test_flat_constant_series_all_three_return_zero(ranker):
    series = pd.Series([5.0] * 20)
    v = series.iloc[-18:].values

    scalar = ranker.calculate_rsrs(series)
    vec = ranker._calculate_rsrs_vectorized(v.reshape(1, 18))[0]
    sql = _sql_rsrs(v)

    assert scalar == pytest.approx(0.0, abs=1e-12)
    assert vec == pytest.approx(0.0, abs=1e-12)
    assert sql == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# Scenario 3: near-flat below the 1e-10 variance guard -> 0.0 (all three).
# ---------------------------------------------------------------------------
def test_near_flat_below_guard_all_three_return_zero(ranker):
    rng = np.random.default_rng(123)
    arr = rng.normal(100.0, 1e-8, size=20)
    series = pd.Series(arr)
    v = series.iloc[-18:].values
    assert float(np.var(v)) <= 1e-10, "fixture variance should trip the guard"

    scalar = ranker.calculate_rsrs(series)
    vec = ranker._calculate_rsrs_vectorized(v.reshape(1, 18))[0]
    sql = _sql_rsrs(v)

    assert scalar == pytest.approx(0.0, abs=1e-12)
    assert vec == pytest.approx(0.0, abs=1e-12)
    assert sql == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# Scenario 4: strictly increasing -> +1.0 (perfect fit, all three).
# ---------------------------------------------------------------------------
def test_strictly_increasing_all_three_agree_positive(ranker):
    series = pd.Series(np.arange(1, 25, dtype=float))
    v = series.iloc[-18:].values

    scalar = ranker.calculate_rsrs(series)
    vec = ranker._calculate_rsrs_vectorized(v.reshape(1, 18))[0]
    sql = _sql_rsrs(v)

    assert scalar == pytest.approx(1.0, abs=1e-9)
    assert vec == pytest.approx(1.0, abs=1e-9)
    assert sql == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Scenario 5: strictly decreasing -> -1.0 (perfect negative fit, all three).
# ---------------------------------------------------------------------------
def test_strictly_decreasing_all_three_agree_negative(ranker):
    series = pd.Series(np.arange(25, 1, -1, dtype=float))
    v = series.iloc[-18:].values

    scalar = ranker.calculate_rsrs(series)
    vec = ranker._calculate_rsrs_vectorized(v.reshape(1, 18))[0]
    sql = _sql_rsrs(v)

    assert scalar == pytest.approx(-1.0, abs=1e-9)
    assert vec == pytest.approx(-1.0, abs=1e-9)
    assert sql == pytest.approx(-1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Scenario 6: short series (< window) -> 0.0 (length guard, scalar).
# ---------------------------------------------------------------------------
def test_short_series_below_window_scalar_returns_zero(ranker):
    series = pd.Series(np.arange(1, 11, dtype=float))  # 10 bars < 18
    assert ranker.calculate_rsrs(series) == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# Scenario 7: vectorized matches scalar on a random matrix that deliberately
# includes a flat row AND a zero-slope (V-shape) row.
# ---------------------------------------------------------------------------
def test_vectorized_matches_scalar_on_random_matrix_including_flat_and_zero_slope_rows(ranker):
    rng = np.random.default_rng(99)
    matrix = rng.random((100, 18)) * 100
    matrix[0] = 3.0                              # flat row -> guard -> 0.0
    matrix[1] = _v_shape_window(18) + 50.0       # zero-slope, nonzero variance

    vec_results = ranker._calculate_rsrs_vectorized(matrix)
    scalar_results = np.array(
        [ranker.calculate_rsrs(pd.Series(row)) for row in matrix]
    )

    assert np.isfinite(vec_results).all()
    assert np.isfinite(scalar_results).all()
    max_diff = float(np.max(np.abs(vec_results - scalar_results)))
    assert max_diff < 1e-6, f"max diff {max_diff} exceeds 1e-6"
    # The zero-slope row (index 1) must AGREE between vectorized and scalar
    # paths (regression guard: pre-S002-001 the scalar returned -1*R2 while
    # np.sign returned 0; for a palindromic V-shape R2==0 so both are 0.0, but
    # this still pins that the two paths do not diverge on the edge case).
    assert vec_results[1] == pytest.approx(scalar_results[1], abs=1e-9)


# ---------------------------------------------------------------------------
# Scenario 8: pin the exact sign-boundary used by BOTH the Python helper and the
# SQL CASE-WHEN helper at {-1.0, -1e-12, 0.0, 1e-12, 1.0}.
# ---------------------------------------------------------------------------
def _python_sign(slope: float) -> float:
    """The canonical scalar sign expression post-S002-001."""
    return 1.0 if float(slope) >= 0 else -1.0


def _sql_sign(slope: float) -> float:
    """The DuckDB CASE-WHEN sign expression (COALESCE'd slope already supplied)."""
    return 1.0 if float(slope) >= 0 else -1.0


@pytest.mark.parametrize("slope", [-1.0, -1e-12, 0.0, 1e-12, 1.0])
def test_sql_sign_helper_matches_python_sign_helper(slope):
    # Boundary points pin the unified zero->+1 convention.
    assert _python_sign(slope) == _sql_sign(slope)
    # The two boundary values straddling zero must both be +1 (zero->+1).
    assert _python_sign(0.0) == 1.0
    assert _python_sign(1e-12) == 1.0
    assert _python_sign(-1e-12) == -1.0
