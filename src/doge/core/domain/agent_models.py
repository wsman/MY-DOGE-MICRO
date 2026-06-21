"""Domain models for research-agent sessions and runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from doge.core.domain.model_policy import ModelPolicy


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(str, Enum):
    RUN_CREATED = "run_created"
    RUN_QUEUED = "run_queued"
    MODEL_RESPONSE = "model_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RESOLVED = "approval_resolved"
    ARTIFACT_CREATED = "artifact_created"
    RUN_CANCELLED = "run_cancelled"
    ERROR = "error"


@dataclass
class Citation:
    evidence_id: str
    source: str
    page: Optional[int] = None
    snippet: str = ""


@dataclass
class AgentArtifact:
    artifact_id: str
    kind: str
    title: str
    content: str
    run_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)


@dataclass
class AgentApproval:
    approval_id: str
    action: str
    risk_level: str
    run_id: str = ""
    status: str = "pending"
    created_at: str = field(default_factory=utc_now)
    resolved_at: Optional[str] = None


@dataclass
class AgentEvent:
    event_id: str
    run_id: str
    event_type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    sequence: int = 0
    schema_version: str = "1.0"
    created_at: str = field(default_factory=utc_now)


@dataclass
class AgentTurn:
    turn_id: str
    session_id: str
    user_message: str
    run_id: Optional[str] = None
    created_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        session_id: str,
        user_message: str,
        run_id: Optional[str] = None,
    ) -> "AgentTurn":
        return cls(
            turn_id=f"turn-{uuid4().hex[:12]}",
            session_id=session_id,
            user_message=user_message,
            run_id=run_id,
        )


@dataclass
class AgentSession:
    session_id: str
    title: str
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    turns: list[AgentTurn] = field(default_factory=list)

    @classmethod
    def create(cls, title: str = "Research session") -> "AgentSession":
        now = utc_now()
        return cls(
            session_id=f"ses-{uuid4().hex[:12]}",
            title=title,
            created_at=now,
            updated_at=now,
        )


@dataclass
class AgentRun:
    run_id: str
    workflow: str
    question: str
    session_id: Optional[str] = None
    market: str = "us"
    language: str = "en"
    document_ids: list[str] = field(default_factory=list)
    portfolio_id: Optional[str] = None
    model_policy: ModelPolicy = field(default_factory=ModelPolicy)
    status: RunStatus = RunStatus.CREATED
    events: list[AgentEvent] = field(default_factory=list)
    artifacts: list[AgentArtifact] = field(default_factory=list)
    approvals: list[AgentApproval] = field(default_factory=list)
    cancel_requested_at: Optional[str] = None
    schema_version: str = "1.0"
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        workflow: str,
        question: str,
        run_id: Optional[str] = None,
        market: str = "us",
        language: str = "en",
        session_id: Optional[str] = None,
        document_ids: Optional[list[str]] = None,
        portfolio_id: Optional[str] = None,
        model_policy: Optional[dict[str, Any] | ModelPolicy] = None,
    ) -> "AgentRun":
        return cls(
            run_id=run_id or f"run-{uuid4().hex[:12]}",
            workflow=workflow,
            question=question,
            session_id=session_id,
            market=market,
            language=language,
            document_ids=document_ids or [],
            portfolio_id=portfolio_id,
            model_policy=ModelPolicy.from_dict(model_policy),
        )

    def add_event(self, event_type: EventType, payload: Optional[dict[str, Any]] = None) -> AgentEvent:
        event = AgentEvent(
            event_id=f"evt-{uuid4().hex[:12]}",
            run_id=self.run_id,
            event_type=event_type,
            payload=payload or {},
            sequence=len(self.events) + 1,
        )
        self.events.append(event)
        self.updated_at = utc_now()
        return event

    def add_artifact(self, kind: str, title: str, content: str, data: Optional[dict[str, Any]] = None) -> AgentArtifact:
        artifact = AgentArtifact(
            artifact_id=f"art-{uuid4().hex[:12]}",
            run_id=self.run_id,
            kind=kind,
            title=title,
            content=content,
            data=data or {},
        )
        self.artifacts.append(artifact)
        self.updated_at = utc_now()
        return artifact

    def add_approval(self, action: str, risk_level: str) -> AgentApproval:
        approval = AgentApproval(
            approval_id=f"appr-{uuid4().hex[:12]}",
            run_id=self.run_id,
            action=action,
            risk_level=risk_level,
        )
        self.approvals.append(approval)
        self.updated_at = utc_now()
        return approval
