"""Worker queue port for durable agent run scheduling."""

from __future__ import annotations

from abc import ABC, abstractmethod


class IRunQueue(ABC):
    @abstractmethod
    def enqueue(self, run_id: str) -> None:
        """Append a queued status for a run."""
        ...

    @abstractmethod
    def dequeue(self) -> str | None:
        """Optionally claim a queued run from durable storage."""
        ...

    @abstractmethod
    def list_pending(self) -> list[str]:
        """Return run IDs whose latest queue status is queued or running."""
        ...

    @abstractmethod
    def append_status(self, run_id: str, status: str) -> None:
        """Append a status entry to the queue log."""
        ...

    @abstractmethod
    def is_ready(self) -> bool:
        """Return whether the backing queue store is reachable."""
        ...
