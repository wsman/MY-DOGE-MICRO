"""Shared facade for cross-context primitives.

ADR-0022 keeps this package shallow while existing implementation modules stay
in place. Add only primitives here, not product workflow logic.
"""

from doge.config import Settings, get_settings, reset_settings
from doge.shared.errors import SafeError, safe_error_payload
from doge.shared.scope import LOCAL_TENANT_ID, TenantScope

__all__ = [
    "LOCAL_TENANT_ID",
    "SafeError",
    "Settings",
    "TenantScope",
    "get_settings",
    "reset_settings",
    "safe_error_payload",
]
