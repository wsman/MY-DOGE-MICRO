"""Deprecated analysis router — forwards to ``doge.interfaces.api.routers.analysis``."""
import warnings

warnings.warn(
    "src.api.routers.analysis is deprecated; use doge.interfaces.api.routers.analysis instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.interfaces.api.routers import analysis as _analysis

__all__ = getattr(_analysis, "__all__", [])
for _name in dir(_analysis):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_analysis, _name)
