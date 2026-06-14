"""Deprecated API entrypoint — forwards to ``doge.interfaces.api``.

``src.api`` is kept as a backwards-compatible shim for Sprint 007. The
canonical FastAPI app now lives in ``doge.interfaces.api.main``. This module
re-exports the entire public namespace of the canonical module so existing
imports and monkeypatches continue to work.

This shim will be removed in Sprint 008.
"""
import warnings

warnings.warn(
    "src.api is deprecated; use doge.interfaces.api instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.interfaces.api import main as _main

__all__ = getattr(_main, "__all__", [])
for _name in dir(_main):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_main, _name)
