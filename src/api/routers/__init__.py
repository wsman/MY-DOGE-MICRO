"""Deprecated API routers package — forwards to ``doge.interfaces.api.routers``."""
import warnings

warnings.warn(
    "src.api.routers is deprecated; use doge.interfaces.api.routers instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.interfaces.api.routers import scan, data, notes, macro, analysis, config

__all__ = ["scan", "data", "notes", "macro", "analysis", "config"]
