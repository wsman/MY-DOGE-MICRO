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
from doge.shared.scope import TenantScope


class ISessionRepository(ABC):
    @abstractmethod
    def save(self, session: AgentSession, scope: TenantScope) -> None:
        ...

    @abstractmethod
    def get(self, session_id: str, scope: TenantScope) -> AgentSession | None:
        ...

    @abstractmethod
    def list_recent(self, scope: TenantScope, limit: int = 20) -> list[AgentSession]:
        ...


class IRunRepository(ABC):
    @abstractmethod
    def save(self, run: AgentRun, scope: TenantScope) -> None:
        ...

    @abstractmethod
    def get(self, run_id: str, scope: TenantScope) -> AgentRun | None:
        ...

    @abstractmethod
    def get_run_header(self, run_id: str, scope: TenantScope) -> AgentRun | None:
        ...

    @abstractmethod
    def list_by_session(self, session_id: str, scope: TenantScope) -> list[AgentRun]:
        ...

    @abstractmethod
    def list_recent(self, scope: TenantScope, limit: int = 20) -> list[AgentRun]:
        ...


class IEventRepository(ABC):
    @abstractmethod
    def append(self, event: AgentEvent, scope: TenantScope) -> AgentEvent:
        ...

    @abstractmethod
    def list_for_run(self, run_id: str, scope: TenantScope, after_sequence: int = 0) -> list[AgentEvent]:
        ...


class IArtifactRepository(ABC):
    @abstractmethod
    def save(self, artifact: AgentArtifact, scope: TenantScope) -> None:
        ...

    @abstractmethod
    def list_for_run(self, run_id: str, scope: TenantScope) -> list[AgentArtifact]:
        ...


class IApprovalRepository(ABC):
    @abstractmethod
    def save(self, approval: AgentApproval, scope: TenantScope) -> None:
        ...

    @abstractmethod
    def get(self, approval_id: str, scope: TenantScope) -> AgentApproval | None:
        ...

    @abstractmethod
    def list_for_run(self, run_id: str, scope: TenantScope) -> list[AgentApproval]:
        ...
