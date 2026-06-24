import pytest

from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.tools import ToolRegistry, ToolResult
from doge.core.domain.agent_models import EventType
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.infrastructure.database.agent_repositories import (
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteEventRepository,
    SQLiteRunRepository,
)
from doge.shared.errors import SafeError


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
    kernel = RuntimeKernel(
        model=ToolCallModel(),
        tool_registry=registry,
        run_repository=SQLiteRunRepository(tmp_path / "agent_state.db"),
        event_repository=SQLiteEventRepository(tmp_path / "agent_state.db"),
        artifact_repository=SQLiteArtifactRepository(tmp_path / "agent_state.db"),
        approval_repository=SQLiteApprovalRepository(tmp_path / "agent_state.db"),
    )
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
