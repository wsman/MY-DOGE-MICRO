"""Process-local container ownership for the API dependency layer.

This module owns the bootstrap :class:`~doge.bootstrap.AppContainer` singleton
used by every API dependency provider. ``deps.py`` and ``factories.py`` reach
the wired container through :func:`get_app_container` so there is a single
owner of the bootstrap composition root for the API surface.
"""

from __future__ import annotations

from doge.bootstrap import build_api_process

#: The bootstrap application container singleton for the API process.
process_graph = build_api_process()
app_container = process_graph.as_app_container()


def get_app_container():
    """Return the API bootstrap container singleton."""

    return app_container
