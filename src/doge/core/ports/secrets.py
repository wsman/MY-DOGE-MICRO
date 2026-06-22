"""Port for retrieving sensitive runtime secrets."""

from __future__ import annotations

from typing import Protocol


class ISecretProvider(Protocol):
    """Read secrets without exposing storage details to adapters."""

    def get_secret(self, name: str) -> str | None:
        """Return the secret value for ``name`` or ``None`` when unavailable."""
