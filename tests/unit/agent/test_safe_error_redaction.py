import pytest

from doge.application.agent.approval_coordinator import ApprovalCoordinator
from doge.application.agent.artifact_finalizer import ArtifactFinalizer
from doge.application.agent.context_builder import ContextBuilder
from doge.application.agent.model_response_assembler import ModelResponseAssembler
from doge.application.agent.run_lifecycle_service import RunLifecycleService
from doge.application.agent.run_stepper import RunStepper
from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.tools import ToolRegistry, ToolResult
from doge.application.agent.transition_recorder import TransitionRecorder
from doge.core.domain.agent_models import EventType
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
from doge.shared.errors import SafeError


def _build_kernel(db, model, tool_registry):
    repos = {
        "runs": SQLiteRunRepository(db),
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


def test_safe_error_event_payload_is_client_safe():
    payload = SafeError.create("tool_execution_failed", "tool execution failed").to_event_payload()

    assert payload["code"] == "tool_execution_failed"
    assert payload["message"] == "tool execution failed"
    assert payload["internal_reference"].startswith("err-")


@pytest.mark.asyncio
async def test_tool_exception_persists_safe_error_without_raw_exception_text(tmp_path):
    registry = ToolRegistry()

    def failing_tool() -> ToolResult:
        raise RuntimeError(
            "provider failed Authorization: Bearer sk-liveSecret123 "
            "MOONSHOT_API_KEY=moonshot-secret C:\\Users\\Aby\\secret.txt"
        )

    registry.register(_schema("secret_tool"), lambda **_: failing_tool())
    model = ToolCallModel()
    kernel = _build_kernel(tmp_path / "agent_state.db", model, registry)
    run = await kernel.create_run({"question": "Analyze AAPL"})

    stepped = await kernel.step(run.run_id)

    result = [
        event.payload["result"]
        for event in stepped.events
        if event.event_type == EventType.TOOL_RESULT
    ][-1]
    assert result["error"] == "tool execution failed"
    assert result["safe_error"]["code"] == "tool_execution_failed"
    assert "sk-liveSecret123" not in repr(result)
    assert "moonshot-secret" not in repr(result)
    assert "secret.txt" not in repr(result)


def _schema(name: str):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": name,
            "parameters": {"type": "object", "properties": {}},
        },
    }


class ToolCallModel:
    async def chat(self, messages, **kwargs):
        yield AgentResponse(
            message=AgentMessage(
                role="assistant",
                content="",
                tool_calls=[{
                    "id": "tool-secret",
                    "type": "function",
                    "function": {
                        "name": "secret_tool",
                        "arguments": "{}",
                    },
                }],
            )
        )
