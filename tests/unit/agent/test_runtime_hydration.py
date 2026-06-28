"""Runtime hydration should compose narrow repository reads."""

from __future__ import annotations

import asyncio

from doge.application.agent.approval_coordinator import ApprovalCoordinator
from doge.application.agent.artifact_finalizer import ArtifactFinalizer
from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.run_lifecycle_service import RunLifecycleService
from doge.application.agent.run_stepper import RunStepper
from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.tools import ToolRegistry
from doge.application.agent.transition_recorder import TransitionRecorder
from doge.core.domain.agent_models import AgentRun
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.infrastructure.database.agent_repositories import (
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteEventRepository,
    SQLiteRunRepository,
)
from doge.infrastructure.database.sqlite_runtime_transaction import SQLiteRuntimeTransactionFactory
from doge.platform.runtime.services import (
    ArtifactEvaluationService,
    ModelExecutionService,
    ToolExecutionService,
)


class FinalModel:
    async def chat(self, messages, **kwargs):
        yield AgentResponse(message=AgentMessage(role="assistant", content="final memo"))


class HeaderOnlyRunRepository(SQLiteRunRepository):
    def __init__(self, db_path):
        super().__init__(db_path)
        self.header_reads = 0
        self.full_reads = 0

    def get_run_header(self, run_id: str, tenant_id: str | None = None) -> AgentRun | None:
        self.header_reads += 1
        return super().get_run_header(run_id, tenant_id=tenant_id)

    def get(self, run_id: str, tenant_id: str | None = None) -> AgentRun | None:
        self.full_reads += 1
        return super().get(run_id, tenant_id=tenant_id)


def _build_kernel(db, model, tool_registry, *, run_repository=None):
    repos = {
        "runs": run_repository or SQLiteRunRepository(db),
        "events": SQLiteEventRepository(db),
        "artifacts": SQLiteArtifactRepository(db),
        "approvals": SQLiteApprovalRepository(db),
    }
    response_assembler = ModelResponseAssembler()
    model_execution = ModelExecutionService(
        model=model,
        response_assembler=response_assembler,
    )
    tool_execution = ToolExecutionService(tool_registry=tool_registry)
    artifact_evaluation = ArtifactEvaluationService()
    transition_recorder = TransitionRecorder(
        transaction_factory=SQLiteRuntimeTransactionFactory(db),
    )
    artifact_finalizer = ArtifactFinalizer(evaluation_service=artifact_evaluation)
    stepper = RunStepper(
        run_repository=repos["runs"],
        event_repository=repos["events"],
        artifact_repository=repos["artifacts"],
        approval_repository=repos["approvals"],
        context_builder=ContextBuilder(
            document_repository=None,
            evidence_repository=None,
            session_repository=None,
            run_repository=repos["runs"],
        ),
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
    return RuntimeKernel(
        lifecycle_service=lifecycle,
        stepper=stepper,
        transition_recorder=transition_recorder,
        approval_coordinator=approval_coordinator,
        artifact_finalizer=artifact_finalizer,
    )


def test_runtime_hydrate_uses_run_header_and_child_repositories(tmp_path) -> None:
    db = tmp_path / "agent_state.db"
    model = FinalModel()
    registry = ToolRegistry()
    runs = HeaderOnlyRunRepository(db)
    kernel = _build_kernel(db, model, registry, run_repository=runs)

    run = asyncio.run(kernel.create_run({"question": "Analyze AAPL"}))
    completed = asyncio.run(kernel.step(run.run_id))

    assert completed.events
    assert completed.artifacts
    assert runs.header_reads > 0
    assert runs.full_reads == 0
