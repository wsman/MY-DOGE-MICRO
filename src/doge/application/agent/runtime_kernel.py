"""Persisted research-agent runtime kernel facade."""

from __future__ import annotations

from typing import Any

from doge.application.agent.approval_coordinator import ApprovalCoordinator
from doge.application.agent.artifact_finalizer import ArtifactFinalizer
from doge.application.agent.run_lifecycle_service import RunLifecycleService
from doge.application.agent.run_stepper import RunStepper
from doge.application.agent.runtime_args import (
    approval_args,
    create_run_args,
    failure_args,
    list_runs_args,
    queue_args,
    run_args,
    run_execution_args,
)
from doge.application.agent.transition_recorder import TransitionRecorder
from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun
from doge.core.ports.runtime_services import (
    IApprovalCoordinator,
    IArtifactFinalizer,
    IRunLifecycleService,
    IRunStepper,
    ITransitionRecorder,
)
from doge.shared.scope import TenantScope


class RuntimeKernel:
    """Public facade for agent run runtime operations.

    Public operations:

    - ``create_run`` -> ``AgentRun``
    - ``run_to_pause_or_completion`` -> ``AgentRun``
    - ``queue_run`` -> ``AgentRun``
    - ``step`` -> ``AgentRun``
    - ``resolve_approval`` -> ``AgentRun``
    - ``cancel_run`` -> ``AgentRun``
    - ``finalize_cancelled`` -> ``AgentRun``
    - ``record_failure`` -> ``AgentRun``
    - ``get_run`` -> ``AgentRun | None``
    - ``list_events`` -> ``list[AgentEvent]``
    - ``list_runs`` -> ``list[AgentRun]``
    - ``list_artifacts`` -> ``list[AgentArtifact]``

    Invariant: Kernel delegates; collaborators decide.

    The kernel no longer contains inline business logic. It delegates to
    specialized collaborators:

    - ``RunLifecycleService`` for create/execute/queue/cancel/failure paths.
    - ``RunStepper`` for a single model/tool round.
    - ``ApprovalCoordinator`` for approval resolution.
    - ``TransitionRecorder`` for transactional state recording.
    - ``ArtifactFinalizer`` for artifact construction and metrics.
    """

    def __init__(
        self,
        *,
        lifecycle_service: IRunLifecycleService,
        stepper: IRunStepper,
        transition_recorder: ITransitionRecorder,
        approval_coordinator: IApprovalCoordinator,
        artifact_finalizer: IArtifactFinalizer,
    ) -> None:
        self._lifecycle = lifecycle_service
        self._stepper = stepper
        self._recorder = transition_recorder
        self._approval = approval_coordinator
        self._artifact_finalizer = artifact_finalizer

    async def create_run(
        self,
        scope: TenantScope | dict[str, Any],
        request: dict[str, Any] | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_request = create_run_args(scope, request, tenant_id=tenant_id)
        return await self._lifecycle.create_run(resolved_scope, resolved_request)

    async def run_to_pause_or_completion(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id = run_execution_args(scope, run_id, tenant_id=tenant_id)
        return await self._lifecycle.run_to_pause_or_completion(resolved_scope, resolved_run_id)

    async def queue_run(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        reason: str = "queued",
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id, resolved_reason = queue_args(scope, run_id, reason, tenant_id=tenant_id)
        return await self._lifecycle.queue_run(resolved_scope, resolved_run_id, resolved_reason)

    async def step(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id = run_args(scope, run_id, tenant_id=tenant_id)
        return await self._stepper.step(resolved_scope, resolved_run_id)

    async def resolve_approval(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        approval_id: str | bool | None = None,
        approved: bool = True,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id, resolved_approval_id, resolved_approved = approval_args(
            scope,
            run_id,
            approval_id,
            approved,
            tenant_id=tenant_id,
        )
        return await self._approval.resolve(
            resolved_scope,
            resolved_run_id,
            resolved_approval_id,
            resolved_approved,
        )

    async def cancel_run(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id = run_args(scope, run_id, tenant_id=tenant_id)
        return await self._lifecycle.cancel_run(resolved_scope, resolved_run_id)

    async def finalize_cancelled(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id = run_args(scope, run_id, tenant_id=tenant_id)
        return await self._lifecycle.finalize_cancelled(resolved_scope, resolved_run_id)

    async def record_failure(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        message: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun:
        resolved_scope, resolved_run_id, resolved_message = failure_args(
            scope, run_id, message, tenant_id=tenant_id
        )
        return await self._lifecycle.record_failure(
            resolved_scope, resolved_run_id, resolved_message
        )

    def get_run(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> AgentRun | None:
        resolved_scope, resolved_run_id = run_args(scope, run_id, tenant_id=tenant_id)
        return self._lifecycle.get_run(resolved_scope, resolved_run_id)

    def list_events(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> list[AgentEvent]:
        resolved_scope, resolved_run_id = run_args(scope, run_id, tenant_id=tenant_id)
        return self._lifecycle.list_events(resolved_scope, resolved_run_id)

    def list_runs(
        self,
        scope: TenantScope | str | None = None,
        session_id: str | None = None,
        limit: int = 20,
        *,
        tenant_id: str | None = None,
    ) -> list[AgentRun]:
        resolved_scope, resolved_session_id = list_runs_args(scope, session_id, tenant_id=tenant_id)
        return self._lifecycle.list_runs(resolved_scope, resolved_session_id, limit)

    def list_artifacts(
        self,
        scope: TenantScope | str | None,
        run_id: str | None = None,
        *,
        tenant_id: str | None = None,
    ) -> list[AgentArtifact]:
        resolved_scope, resolved_run_id = run_args(scope, run_id, tenant_id=tenant_id)
        return self._lifecycle.list_artifacts(resolved_scope, resolved_run_id)


__all__ = [
    "RuntimeKernel",
    "RunLifecycleService",
    "RunStepper",
    "TransitionRecorder",
    "ApprovalCoordinator",
    "ArtifactFinalizer",
]
