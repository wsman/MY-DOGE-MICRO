from __future__ import annotations

from abc import ABC, abstractmethod

from doge.core.domain.agent_models import AgentApproval, AgentArtifact, AgentEvent, AgentRun


class IRuntimeTransaction(ABC):
    @abstractmethod
    def save_run(self, run: AgentRun) -> None:
        ...

    @abstractmethod
    def append_event(self, event: AgentEvent) -> AgentEvent:
        ...

    @abstractmethod
    def save_artifact(self, artifact: AgentArtifact) -> None:
        ...

    @abstractmethod
    def save_approval(self, approval: AgentApproval) -> None:
        ...

    @abstractmethod
    def stage_outbox(self, event: AgentEvent) -> None:
        ...

    @abstractmethod
    def commit(self) -> None:
        ...

    @abstractmethod
    def rollback(self) -> None:
        ...


class IRuntimeTransactionFactory(ABC):
    @abstractmethod
    def begin(self) -> IRuntimeTransaction:
        ...


class IOutboxRepository(ABC):
    @abstractmethod
    def claim_pending(self, worker_id: str, batch_size: int, lease_seconds: int) -> list[AgentEvent]:
        ...

    @abstractmethod
    def mark_published(self, event_ids: list[str]) -> None:
        ...

    @abstractmethod
    def release_stale(self, lease_timeout_seconds: int) -> int:
        ...
