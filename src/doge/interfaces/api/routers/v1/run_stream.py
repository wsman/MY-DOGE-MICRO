"""Compatibility shim for ``doge.interfaces.gateway.routers.run_stream``.

ADR-0025 streaming terms stay documented here for legacy static checks:
``list_events`` is persisted replay, ``stream_events`` is replay-only
compatibility, and ``RunStreamHandler`` is the live SSE boundary.

The canonical implementation constructs
``RunStreamHandler(runtime=runtime, subscriber=subscriber)`` and imports it via
``from doge.interfaces.api.handlers import RunStreamHandler``.
"""

from doge.interfaces.api.handlers import RunStreamHandler
from doge.interfaces.gateway.routers.run_stream import *  # noqa: F401,F403

__all__ = [name for name in globals() if not name.startswith("_")]
