"""Runtime bootstrap container."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from doge.infrastructure.database.agent_repositories import (
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteDocumentRepository,
    SQLiteEventRepository,
    SQLiteIdempotencyStore,
    SQLiteRunQueue,
    SQLiteRunRepository,
    SQLiteSessionRepository,
)
from doge.infrastructure.database.enterprise_governance import SQLiteEnterpriseGovernanceRepository
from doge.infrastructure.database.event_subscriber import SQLiteEventSubscriber
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository
from doge.infrastructure.database.sqlite_runtime_transaction import SQLiteOutboxRepository
from doge.infrastructure.database.sqlite_uow import SQLiteAgentUnitOfWork
from doge.application.use_cases.session_use_cases import CreateSession, ListSessions, ResumeSession


@dataclass(frozen=True)
class RuntimeContainer:
    """Typed entry point for agent runtime wiring."""

    db_path: Path | str | None = None

    def build_research_agent_runtime(self, model: Any = None, tool_registry: Any = None):
        composition = _composition()
        return composition.build_research_agent_runtime(model=model, tool_registry=tool_registry)

    def build_persisted_research_agent_runtime(
        self,
        model: Any = None,
        tool_registry: Any = None,
        event_publisher: Any = None,
    ):
        composition = _composition()
        return composition.build_persisted_research_agent_runtime(
            model=model,
            tool_registry=tool_registry,
            event_publisher=event_publisher,
            db_path=self.db_path,
        )

    def build_event_subscriber(self, *, poll_interval_seconds: float = 0.1):
        return SQLiteEventSubscriber(self.db_path, poll_interval_seconds=poll_interval_seconds)

    def build_runtime_outbox_repository(self):
        return SQLiteOutboxRepository(self.db_path)

    def build_agent_repositories(self):
        return {
            "sessions": SQLiteSessionRepository(self.db_path),
            "runs": SQLiteRunRepository(self.db_path),
            "events": SQLiteEventRepository(self.db_path),
            "artifacts": SQLiteArtifactRepository(self.db_path),
            "approvals": SQLiteApprovalRepository(self.db_path),
            "documents": SQLiteDocumentRepository(self.db_path),
            "evidence": SQLiteEvidenceRepository(self.db_path),
            "run_queue": SQLiteRunQueue(self.db_path),
            "idempotency": SQLiteIdempotencyStore(self.db_path),
            "governance": SQLiteEnterpriseGovernanceRepository(self.db_path),
        }

    def build_agent_document_repository(self):
        return SQLiteDocumentRepository(self.db_path)

    def build_agent_evidence_repository(self):
        return SQLiteEvidenceRepository(self.db_path)

    def build_agent_run_queue(self):
        return SQLiteRunQueue(self.db_path)

    def build_agent_idempotency_store(self):
        return SQLiteIdempotencyStore(self.db_path)

    def build_agent_unit_of_work(self, event_publisher: Any = None):
        return SQLiteAgentUnitOfWork(self.db_path, event_publisher=event_publisher)

    def build_create_session_use_case(self) -> CreateSession:
        return CreateSession(SQLiteSessionRepository(self.db_path))

    def build_resume_session_use_case(self) -> ResumeSession:
        return ResumeSession(SQLiteSessionRepository(self.db_path))

    def build_list_sessions_use_case(self) -> ListSessions:
        return ListSessions(SQLiteSessionRepository(self.db_path))

    def build_run_summary_use_case(self, runtime: Any = None, evidence_repository: Any = None):
        composition = _composition()
        return composition.build_run_summary_use_case(
            runtime=runtime,
            evidence_repository=evidence_repository,
            db_path=self.db_path,
        )

    def build_capability_registry_use_case(self):
        composition = _composition()
        return composition.build_capability_registry_use_case()

    def build_default_tool_registry(self, entitlement_checker: Any = None, context: Any = None):
        composition = _composition()
        return composition.build_default_tool_registry(
            entitlement_checker=entitlement_checker,
            context=context,
            db_path=self.db_path,
        )

    def build_execute_run_use_case(self, model: Any = None, tool_registry: Any = None):
        composition = _composition()
        return composition.build_execute_run_use_case(
            model=model,
            tool_registry=tool_registry,
            db_path=self.db_path,
        )

    def build_resume_run_use_case(self, model: Any = None, tool_registry: Any = None):
        composition = _composition()
        return composition.build_resume_run_use_case(
            model=model,
            tool_registry=tool_registry,
            db_path=self.db_path,
        )


def build_runtime_container(db_path: Path | str | None = None) -> RuntimeContainer:
    """Build the runtime container."""

    return RuntimeContainer(db_path=db_path)


def _composition():
    from doge.application import composition

    return composition
