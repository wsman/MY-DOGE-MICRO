"""Shared facade for cross-context primitives.

ADR-0022 keeps this package shallow while existing implementation modules stay
in place. Add only primitives here, not product workflow logic.
"""

from doge.config import Settings, get_settings, reset_settings

__all__ = [
    "Settings",
    "get_settings",
    "reset_settings",
]
