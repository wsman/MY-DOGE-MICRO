"""Deprecated data router — forwards to ``doge.interfaces.api.routers.data``."""
import warnings

warnings.warn(
    "src.api.routers.data is deprecated; use doge.interfaces.api.routers.data instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.interfaces.api.routers import data as _data

__all__ = getattr(_data, "__all__", [])
for _name in dir(_data):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_data, _name)
