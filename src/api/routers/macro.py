"""Deprecated macro router — forwards to ``doge.interfaces.api.routers.macro``."""
import warnings

warnings.warn(
    "src.api.routers.macro is deprecated; use doge.interfaces.api.routers.macro instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.interfaces.api.routers import macro as _macro

__all__ = getattr(_macro, "__all__", [])
for _name in dir(_macro):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_macro, _name)
