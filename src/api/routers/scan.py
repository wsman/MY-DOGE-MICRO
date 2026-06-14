"""Deprecated scan router — forwards to ``doge.interfaces.api.routers.scan``."""
import warnings

warnings.warn(
    "src.api.routers.scan is deprecated; use doge.interfaces.api.routers.scan instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.interfaces.api.routers import scan as _scan

__all__ = getattr(_scan, "__all__", [])
for _name in dir(_scan):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_scan, _name)
