"""Explicit runtime execution context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from doge.core.domain.agent_models import AgentRun
from doge.core.domain.enterprise_context import EnterpriseContext, IdentitySnapshot
from doge.core.domain.model_policy import ModelPolicy


@dataclass(frozen=True)
class WorkflowRunContext:
    """Workflow/template metadata for a run."""

    workflow: str
    template_id: str | None = None
    template_slug: str | None = None
    template_version: str | None = None
    template_name: str | None = None
    template_metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_run_and_policy(cls, run: AgentRun, policy: ModelPolicy) -> "WorkflowRunContext":
        workflow_context = cls.from_mapping(getattr(run, "workflow_context", None))
        if workflow_context is not None:
            return workflow_context
        return cls(
            workflow=run.workflow,
            template_id=_optional_str(policy.extra.get("template_id")),
            template_slug=_optional_str(policy.extra.get("template_slug")),
            template_version=_optional_str(policy.extra.get("template_version")),
            template_name=_optional_str(policy.extra.get("template_name")),
            template_metadata={
                key: value
                for key, value in policy.extra.items()
                if key.startswith("template_")
            },
        )

    @classmethod
    def from_mapping(cls, data: Any) -> "WorkflowRunContext | None":
        if data is None:
            return None
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            return None
        metadata = data.get("template_metadata")
        if not isinstance(metadata, dict):
            metadata = {
                key: value
                for key, value in data.items()
                if str(key).startswith("template_")
            }
        workflow = _optional_str(data.get("workflow")) or "investment_research"
        return cls(
            workflow=workflow,
            template_id=_optional_str(data.get("template_id")),
            template_slug=_optional_str(data.get("template_slug")),
            template_version=_optional_str(data.get("template_version")),
            template_name=_optional_str(data.get("template_name")),
            template_metadata=dict(metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow": self.workflow,
            "template_id": self.template_id,
            "template_slug": self.template_slug,
            "template_version": self.template_version,
            "template_name": self.template_name,
            "template_metadata": dict(self.template_metadata),
        }


@dataclass(frozen=True)
class RunExecutionContext:
    """Typed context passed through one runtime step."""

    run_id: str
    question: str
    model_policy: ModelPolicy
    identity_snapshot: IdentitySnapshot | None
    workflow: WorkflowRunContext

    @classmethod
    def from_run(cls, run: AgentRun) -> "RunExecutionContext":
        policy = ModelPolicy.from_dict(run.model_policy)
        return cls(
            run_id=run.run_id,
            question=run.question,
            model_policy=policy,
            identity_snapshot=run.identity_snapshot,
            workflow=WorkflowRunContext.from_run_and_policy(run, policy),
        )

    @property
    def enterprise_context(self) -> EnterpriseContext:
        return EnterpriseContext.from_identity_snapshot(self.identity_snapshot)

    @property
    def request_id(self) -> str | None:
        return self.identity_snapshot.request_id if self.identity_snapshot is not None else None


def _optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)
