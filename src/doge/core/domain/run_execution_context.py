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
