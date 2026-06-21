"""Repository ports for persisted agent sessions, runs, and trace data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from doge.core.domain.agent_models import (
    AgentApproval,
    AgentArtifact,
    AgentEvent,
    AgentRun,
    AgentSession,
)
from doge.core.ports.document_repository import IDocumentRepository


class ISessionRepository(ABC):
    @abstractmethod
    def save(self, session: AgentSession) -> None:
        ...

    @abstractmethod
    def get(self, session_id: str) -> AgentSession | None:
        ...

    @abstractmethod
    def list_recent(self, limit: int = 20) -> list[AgentSession]:
        ...


class IRunRepository(ABC):
    @abstractmethod
    def save(self, run: AgentRun) -> None:
        ...

    @abstractmethod
    def get(self, run_id: str) -> AgentRun | None:
        ...

    @abstractmethod
    def list_by_session(self, session_id: str) -> list[AgentRun]:
        ...

    @abstractmethod
    def list_recent(self, limit: int = 20) -> list[AgentRun]:
        ...


class IEventRepository(ABC):
    @abstractmethod
    def append(self, event: AgentEvent) -> AgentEvent:
        ...

    @abstractmethod
    def list_for_run(self, run_id: str, after_sequence: int = 0) -> list[AgentEvent]:
        ...


class IArtifactRepository(ABC):
    @abstractmethod
    def save(self, artifact: AgentArtifact) -> None:
        ...

    @abstractmethod
    def list_for_run(self, run_id: str) -> list[AgentArtifact]:
        ...


class IApprovalRepository(ABC):
    @abstractmethod
    def save(self, approval: AgentApproval) -> None:
        ...

    @abstractmethod
    def get(self, approval_id: str) -> AgentApproval | None:
        ...

    @abstractmethod
    def list_for_run(self, run_id: str) -> list[AgentApproval]:
        ...
