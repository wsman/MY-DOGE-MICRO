"""Deprecated notes router — forwards to ``doge.interfaces.api.routers.notes``."""
import warnings

warnings.warn(
    "src.api.routers.notes is deprecated; use doge.interfaces.api.routers.notes instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.interfaces.api.routers import notes as _notes

__all__ = getattr(_notes, "__all__", [])
for _name in dir(_notes):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_notes, _name)
