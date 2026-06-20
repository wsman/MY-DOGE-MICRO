"""Domain models for research-agent runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(str, Enum):
    RUN_CREATED = "run_created"
    MODEL_RESPONSE = "model_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RESOLVED = "approval_resolved"
    ARTIFACT_CREATED = "artifact_created"
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
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)


@dataclass
class AgentApproval:
    approval_id: str
    action: str
    risk_level: str
    status: str = "pending"
    created_at: str = field(default_factory=utc_now)
    resolved_at: Optional[str] = None


@dataclass
class AgentEvent:
    event_id: str
    run_id: str
    event_type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)


@dataclass
class AgentRun:
    run_id: str
    workflow: str
    question: str
    market: str = "us"
    language: str = "en"
    document_ids: list[str] = field(default_factory=list)
    portfolio_id: Optional[str] = None
    model_policy: dict[str, Any] = field(default_factory=dict)
    status: RunStatus = RunStatus.CREATED
    events: list[AgentEvent] = field(default_factory=list)
    artifacts: list[AgentArtifact] = field(default_factory=list)
    approvals: list[AgentApproval] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        workflow: str,
        question: str,
        market: str = "us",
        language: str = "en",
        document_ids: Optional[list[str]] = None,
        portfolio_id: Optional[str] = None,
        model_policy: Optional[dict[str, Any]] = None,
    ) -> "AgentRun":
        return cls(
            run_id=f"run-{uuid4().hex[:12]}",
            workflow=workflow,
            question=question,
            market=market,
            language=language,
            document_ids=document_ids or [],
            portfolio_id=portfolio_id,
            model_policy=model_policy or {},
        )

    def add_event(self, event_type: EventType, payload: Optional[dict[str, Any]] = None) -> AgentEvent:
        event = AgentEvent(
            event_id=f"evt-{uuid4().hex[:12]}",
            run_id=self.run_id,
            event_type=event_type,
            payload=payload or {},
        )
        self.events.append(event)
        self.updated_at = utc_now()
        return event

    def add_artifact(self, kind: str, title: str, content: str, data: Optional[dict[str, Any]] = None) -> AgentArtifact:
        artifact = AgentArtifact(
            artifact_id=f"art-{uuid4().hex[:12]}",
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
            action=action,
            risk_level=risk_level,
        )
        self.approvals.append(approval)
        self.updated_at = utc_now()
        return approval
