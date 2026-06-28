"""Runtime factory helpers for repositories and persistence adapters."""

from __future__ import annotations

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
from doge.infrastructure.database.sqlite_runtime_transaction import (
    SQLiteOutboxRepository,
    SQLiteRuntimeTransactionFactory,
)
from doge.infrastructure.database.sqlite_uow import SQLiteAgentUnitOfWork


def build_event_subscriber(db_path, *, poll_interval_seconds: float = 0.1):
    return SQLiteEventSubscriber(db_path, poll_interval_seconds=poll_interval_seconds)


def build_runtime_outbox_repository(db_path):
    return SQLiteOutboxRepository(db_path)


def build_agent_repositories(db_path):
    return {
        "sessions": SQLiteSessionRepository(db_path),
        "runs": SQLiteRunRepository(db_path),
        "events": SQLiteEventRepository(db_path),
        "artifacts": SQLiteArtifactRepository(db_path),
        "approvals": SQLiteApprovalRepository(db_path),
        "documents": SQLiteDocumentRepository(db_path),
        "evidence": SQLiteEvidenceRepository(db_path),
        "run_queue": SQLiteRunQueue(db_path),
        "idempotency": SQLiteIdempotencyStore(db_path),
        "governance": SQLiteEnterpriseGovernanceRepository(db_path),
    }


def build_agent_document_repository(db_path):
    return SQLiteDocumentRepository(db_path)


def build_agent_evidence_repository(db_path):
    return SQLiteEvidenceRepository(db_path)


def build_agent_run_queue(db_path):
    return SQLiteRunQueue(db_path)


def build_agent_idempotency_store(db_path):
    return SQLiteIdempotencyStore(db_path)


def build_agent_unit_of_work(db_path, event_publisher: Any = None):
    return SQLiteAgentUnitOfWork(db_path, event_publisher=event_publisher)


def build_runtime_transaction_factory(db_path):
    return SQLiteRuntimeTransactionFactory(db_path)
