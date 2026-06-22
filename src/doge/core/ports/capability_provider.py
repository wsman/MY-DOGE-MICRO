"""Port for platform capability discovery providers."""

from __future__ import annotations

from typing import Any, Protocol


class ICapabilityProvider(Protocol):
    def collect(self, context: Any = None) -> list[dict[str, Any]]:
        """Return redacted capability records safe for UI/SDK discovery."""
        ...
