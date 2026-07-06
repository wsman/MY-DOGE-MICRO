"""Slot platform error types.

These are ordinary exceptions carrying a stable ``code`` and a client-safe
``public_message``. ``to_safe_error()`` converts them to a :class:`SafeError`
payload for persisted runtime traces (see :mod:`doge.shared.errors`).

Sprint 033 (ADR-0042) — experimental, feature-flagged behind
``DOGE_FEATURE_SLOT_PLATFORM``.
"""

from __future__ import annotations

from typing import Optional

from doge.shared.errors import SafeError


class SlotError(Exception):
    """Base class for slot-platform errors."""

    code: str = "slot_error"

    def __init__(self, public_message: str = "", *, code: Optional[str] = None) -> None:
        self.public_message = public_message or self.code
        if code is not None:
            self.code = code
        super().__init__(self.public_message)

    def to_safe_error(self) -> SafeError:
        """Convert to a client-safe :class:`SafeError` payload."""
        return SafeError.create(self.code, self.public_message)


class SlotManifestValidationError(SlotError):
    """Raised when a slot manifest dict/JSON fails schema validation."""

    code = "slot_manifest_validation_failed"


class SlotConfigurationError(SlotError):
    """Raised when a slot cannot be configured or a requested service is unavailable."""

    code = "slot_configuration_failed"


class SlotAlreadyRegisteredError(SlotError):
    """Raised when registering a slot id that is already registered."""

    code = "slot_already_registered"


class UnknownSlotError(SlotError):
    """Raised when looking up a slot id that is not registered."""

    code = "unknown_slot"
