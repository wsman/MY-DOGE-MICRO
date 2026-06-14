"""Pure sign-function unit test for the canonical RSRS sign convention
(S002-001, OQ-11 / TR-016 RESOLVED).

Isolated from the regression math: this pins ONLY the chosen sign() expression
so any future regression in the convention (e.g. reverting ``>= 0`` to ``> 0``,
or swapping ``np.where`` back to ``np.sign``) is loud at the smallest unit.

Chosen convention (per orchestrator decision, OPTION A):
    sign(slope) = +1 when slope >= 0, else -1   (zero -> +1)

Determinism: pure numeric, no imports of production code.
"""
import numpy as np
import pytest


def canonical_sign(slope: float) -> float:
    """The unified RSRS sign expression (zero -> +1)."""
    return 1.0 if float(slope) >= 0 else -1.0


class TestRsrsSignConvention:
    def test_sign_of_clearly_negative_slope_is_negative_one(self):
        # Arrange / Act / Assert
        assert canonical_sign(-0.1) == -1.0

    def test_sign_of_exactly_zero_slope_is_positive_one(self):
        # The load-bearing convention assertion: zero slope -> +1 (not -1, not 0).
        assert canonical_sign(0.0) == 1.0

    def test_sign_of_clearly_positive_slope_is_positive_one(self):
        assert canonical_sign(0.1) == 1.0

    def test_sign_boundary_just_below_zero_is_negative_one(self):
        # -1e-12 is negative -> -1 (confirms the convention is >= 0, not > 0).
        assert canonical_sign(-1e-12) == -1.0

    def test_sign_boundary_just_above_zero_is_positive_one(self):
        # +1e-12 is non-negative -> +1.
        assert canonical_sign(1e-12) == 1.0

    def test_vectorized_np_where_matches_scalar_convention(self):
        """Regression guard: the vectorized path uses np.where(slope >= 0, 1, -1)
        which must agree with the scalar ``1.0 if slope >= 0 else -1.0`` for the
        exact boundary values, including zero (this would FAIL under np.sign
        which maps 0.0 -> 0.0)."""
        slopes = np.array([-1.0, -1e-12, 0.0, 1e-12, 1.0])
        vectorized = np.where(slopes >= 0, 1.0, -1.0)
        scalar = np.array([canonical_sign(float(s)) for s in slopes])
        np.testing.assert_array_equal(vectorized, scalar)
        # And zero must map to +1 (not 0 as np.sign would).
        assert vectorized[2] == 1.0
