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
    def save(self, session: AgentSession, tenant_id: str | None = None) -> None:
        ...

    @abstractmethod
    def get(self, session_id: str, tenant_id: str | None = None) -> AgentSession | None:
        ...

    @abstractmethod
    def list_recent(self, limit: int = 20, tenant_id: str | None = None) -> list[AgentSession]:
        ...


class IRunRepository(ABC):
    @abstractmethod
    def save(self, run: AgentRun, tenant_id: str | None = None) -> None:
        ...

    @abstractmethod
    def get(self, run_id: str, tenant_id: str | None = None) -> AgentRun | None:
        ...

    @abstractmethod
    def list_by_session(self, session_id: str, tenant_id: str | None = None) -> list[AgentRun]:
        ...

    @abstractmethod
    def list_recent(self, limit: int = 20, tenant_id: str | None = None) -> list[AgentRun]:
        ...


class IEventRepository(ABC):
    @abstractmethod
    def append(self, event: AgentEvent, tenant_id: str | None = None) -> AgentEvent:
        ...

    @abstractmethod
    def list_for_run(self, run_id: str, after_sequence: int = 0, tenant_id: str | None = None) -> list[AgentEvent]:
        ...


class IArtifactRepository(ABC):
    @abstractmethod
    def save(self, artifact: AgentArtifact, tenant_id: str | None = None) -> None:
        ...

    @abstractmethod
    def list_for_run(self, run_id: str, tenant_id: str | None = None) -> list[AgentArtifact]:
        ...


class IApprovalRepository(ABC):
    @abstractmethod
    def save(self, approval: AgentApproval, tenant_id: str | None = None) -> None:
        ...

    @abstractmethod
    def get(self, approval_id: str, tenant_id: str | None = None) -> AgentApproval | None:
        ...

    @abstractmethod
    def list_for_run(self, run_id: str, tenant_id: str | None = None) -> list[AgentApproval]:
        ...
