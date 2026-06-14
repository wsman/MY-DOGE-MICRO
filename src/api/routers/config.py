"""Deprecated config router — forwards to ``doge.interfaces.api.routers.config``."""
import warnings

warnings.warn(
    "src.api.routers.config is deprecated; use doge.interfaces.api.routers.config instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.interfaces.api.routers import config as _config

__all__ = getattr(_config, "__all__", [])
for _name in dir(_config):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_config, _name)
