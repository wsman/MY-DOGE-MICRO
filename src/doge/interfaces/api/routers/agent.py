"""Compatibility shim for ``doge.interfaces.api_legacy.routers.agent``.

The legacy implementation still exposes replay-only ``runtime.stream_events(``
for `/api/*` compatibility. New live streaming must use `/v1/*`.
"""

from doge.interfaces.api_legacy.routers.agent import *  # noqa: F401,F403
