"""Shared CLI ticker normalization.

The implementation lives in :mod:`doge.core.utils`; this module re-exports it
for backward compatibility with existing CLI imports.
"""

from doge.core.utils import normalize_ticker

__all__ = ["normalize_ticker"]
