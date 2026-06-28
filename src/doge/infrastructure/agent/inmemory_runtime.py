"""RuntimeKernel-backed in-memory research-agent runtime adapter."""

from __future__ import annotations

from typing import Any

from doge.application.agent.approval_coordinator import ApprovalCoordinator
from doge.application.agent.artifact_finalizer import ArtifactFinalizer
from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.run_lifecycle_service import RunLifecycleService
from doge.application.agent.run_stepper import RunStepper
from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.tools import ToolRegistry
from doge.application.agent.transition_recorder import TransitionRecorder
from doge.application.agent.web_search_stage import WebSearchStage
from doge.core.ports.agent_model import IAgentModel
from doge.core.ports.runtime_transaction import IRuntimeTransaction, IRuntimeTransactionFactory
from doge.infrastructure.agent.inmemory_repositories import build_inmemory_repositories
from doge.infrastructure.agent.persisted_runtime import PersistedResearchAgentRuntime
from doge.platform.runtime.services import (
    ArtifactEvaluationService,
    ModelExecutionService,
    ToolExecutionService,
)


class _InMemoryRuntimeTransaction(IRuntimeTransaction):
    """In-memory transaction that delegates to repository save/append methods."""

    def __init__(
        self,
        run_repository: object,
        event_repository: object,
        artifact_repository: object,
        approval_repository: object,
    ) -> None:
        self._run_repo = run_repository
        self._event_repo = event_repository
        self._artifact_repo = artifact_repository
        self._approval_repo = approval_repository
        self._closed = False

    def save_run(self, run: Any) -> None:
        if self._closed:
            return
        self._run_repo.save(run)

    def append_event(self, event: Any) -> Any:
        if self._closed:
            return event
        return self._event_repo.append(event)

    def save_artifact(self, artifact: Any) -> None:
        if self._closed:
            return
        self._artifact_repo.save(artifact)

    def save_approval(self, approval: Any) -> None:
        if self._closed:
            return
        self._approval_repo.save(approval)

    def stage_outbox(self, event: Any) -> None:
        # In-memory runtime does not persist outbox; no-op
        pass

    def commit(self) -> None:
        self._closed = True

    def rollback(self) -> None:
        # In-memory repositories do not support rollback; just mark closed
        self._closed = True


class _InMemoryTransactionFactory(IRuntimeTransactionFactory):
    """Fallback transaction factory for in-memory repositories."""

    def __init__(self, repos):
        self._repos = repos

    def begin(self):
        return _InMemoryRuntimeTransaction(
            run_repository=self._repos["runs"],
            event_repository=self._repos["events"],
            artifact_repository=self._repos["artifacts"],
            approval_repository=self._repos["approvals"],
        )


class InMemoryResearchAgentRuntime(PersistedResearchAgentRuntime):
    """Research runtime backed by RuntimeKernel and process-local repositories."""

    def __init__(self, model: IAgentModel, tool_registry: ToolRegistry) -> None:
        repos = build_inmemory_repositories()
        response_assembler = ModelResponseAssembler()
        model_execution = ModelExecutionService(
            model=model,
            response_assembler=response_assembler,
            web_search_stage=WebSearchStage(model, response_assembler=response_assembler),
        )
        tool_execution = ToolExecutionService(tool_registry=tool_registry)
        artifact_evaluation = ArtifactEvaluationService()
        transition_recorder = TransitionRecorder(
            transaction_factory=_InMemoryTransactionFactory(repos),
        )
        artifact_finalizer = ArtifactFinalizer(evaluation_service=artifact_evaluation)
        context_builder = ContextBuilder(
            document_repository=None,
            evidence_repository=None,
            session_repository=None,
            run_repository=repos["runs"],
        )
        stepper = RunStepper(
            run_repository=repos["runs"],
            event_repository=repos["events"],
            artifact_repository=repos["artifacts"],
            approval_repository=repos["approvals"],
            context_builder=context_builder,
            response_assembler=response_assembler,
            model_execution_service=model_execution,
            tool_execution_service=tool_execution,
            artifact_finalizer=artifact_finalizer,
            transition_recorder=transition_recorder,
        )
        lifecycle = RunLifecycleService(
            run_repository=repos["runs"],
            event_repository=repos["events"],
            artifact_repository=repos["artifacts"],
            approval_repository=repos["approvals"],
            transition_recorder=transition_recorder,
            run_stepper=stepper,
        )
        approval_coordinator = ApprovalCoordinator(
            run_repository=repos["runs"],
            approval_repository=repos["approvals"],
            transition_recorder=transition_recorder,
        )
        kernel = RuntimeKernel(
            lifecycle_service=lifecycle,
            stepper=stepper,
            transition_recorder=transition_recorder,
            approval_coordinator=approval_coordinator,
            artifact_finalizer=artifact_finalizer,
        )
        super().__init__(kernel)
