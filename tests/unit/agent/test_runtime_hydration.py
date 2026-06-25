"""Runtime hydration should compose narrow repository reads."""

from __future__ import annotations

import asyncio

from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.tools import ToolRegistry
from doge.core.domain.agent_models import AgentRun
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.infrastructure.database.agent_repositories import (
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteEventRepository,
    SQLiteRunRepository,
)
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


def test_runtime_hydrate_uses_run_header_and_child_repositories(tmp_path) -> None:
    db = tmp_path / "agent_state.db"
    model = FinalModel()
    registry = ToolRegistry()
    runs = HeaderOnlyRunRepository(db)
    kernel = RuntimeKernel(
        model=model,
        tool_registry=registry,
        run_repository=runs,
        event_repository=SQLiteEventRepository(db),
        artifact_repository=SQLiteArtifactRepository(db),
        approval_repository=SQLiteApprovalRepository(db),
        model_execution_service=ModelExecutionService(model=model),
        tool_execution_service=ToolExecutionService(tool_registry=registry),
        artifact_evaluation_service=ArtifactEvaluationService(),
    )

    run = asyncio.run(kernel.create_run({"question": "Analyze AAPL"}))
    completed = asyncio.run(kernel.step(run.run_id))

    assert completed.events
    assert completed.artifacts
    assert runs.header_reads > 0
    assert runs.full_reads == 0
