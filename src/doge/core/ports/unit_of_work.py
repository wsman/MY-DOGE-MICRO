"""Unit-of-work port for atomic agent run scheduling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IAgentUnitOfWork(ABC):
    """Atomic transaction boundary for session turn + run enqueue writes."""

    @abstractmethod
    async def enqueue_run_and_turn(
        self,
        *,
        session_id: str,
        message: str,
        workflow: str = "investment_research",
        market: str = "us",
        language: str = "en",
        document_ids: list[str] | None = None,
        portfolio_id: str | None = "portfolio-demo",
        model_policy: dict[str, Any] | None = None,
        identity_snapshot: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        """Create a run, append the session turn, queue it, and return run_id."""
        ...
