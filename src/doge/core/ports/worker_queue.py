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
    def claim_atomic(self, worker_id: str, lease_seconds: int) -> str | None:
        """Atomically claim one queued or expired run for a worker."""
        ...

    @abstractmethod
    def heartbeat(self, worker_id: str, run_id: str, lease_seconds: int) -> None:
        """Extend an active claim lease for the owning worker."""
        ...

    @abstractmethod
    def release_claim(self, run_id: str, worker_id: str, final_status: str) -> None:
        """Release an active claim by appending its final queue status."""
        ...

    @abstractmethod
    def recover_stalled_leases(self, lease_timeout_seconds: int) -> list[str]:
        """Requeue expired running claims and return their run IDs."""
        ...

    @abstractmethod
    def list_pending(self) -> list[str]:
        """Return run IDs whose latest queue status is queued."""
        ...

    @abstractmethod
    def append_status(self, run_id: str, status: str) -> None:
        """Append a status entry to the queue log."""
        ...

    @abstractmethod
    def is_ready(self) -> bool:
        """Return whether the backing queue store is reachable."""
        ...
