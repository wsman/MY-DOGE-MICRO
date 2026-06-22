import pytest

from doge.application.agent.runtime_kernel import RuntimeKernel
from doge.application.agent.tools import ToolRegistry, ToolResult
from doge.core.domain.agent_models import EventType, RunStatus
from doge.core.ports.enterprise_governance import EnterpriseAclGrant
from doge.core.ports.agent_model import AgentMessage, AgentResponse
from doge.core.ports.model_router import RoutingDecision
from doge.infrastructure.agent.scripted_model import ScriptedAgentModel
from doge.infrastructure.database.agent_repositories import (
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteEventRepository,
    SQLiteRunRepository,
)
from doge.infrastructure.database.enterprise_governance import SQLiteEnterpriseGovernanceRepository


def _schema(name: str):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": name,
            "parameters": {"type": "object", "properties": {}},
        },
    }


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(_schema("stock_overview"), lambda **_: ToolResult("stock_overview", {"ticker": "AAPL"}))
    registry.register(_schema("get_portfolio_exposure"), lambda **_: ToolResult(
        "get_portfolio_exposure",
        {"portfolio_id": "portfolio-demo", "holdings": []},
    ))
    registry.register(_schema("request_approval"), lambda **kwargs: ToolResult(
        "request_approval",
        {
            "approval_required": True,
            "action": kwargs.get("action", "publish"),
            "risk_level": kwargs.get("risk_level", "high"),
        },
    ))
    return registry


def _kernel(tmp_path):
    db = tmp_path / "agent_state.db"
    return RuntimeKernel(
        model=ScriptedAgentModel(),
        tool_registry=_registry(),
        run_repository=SQLiteRunRepository(db),
        event_repository=SQLiteEventRepository(db),
        artifact_repository=SQLiteArtifactRepository(db),
        approval_repository=SQLiteApprovalRepository(db),
    )


@pytest.mark.asyncio
async def test_kernel_create_run_persists_to_repository(tmp_path):
    kernel = _kernel(tmp_path)

    run = await kernel.create_run({"question": "Analyze AAPL", "session_id": "ses-1"})

    loaded = kernel.get_run(run.run_id)
    assert loaded is not None
    assert loaded.session_id == "ses-1"
    assert loaded.events[0].sequence == 1


@pytest.mark.asyncio
async def test_kernel_create_run_records_template_metadata_in_created_event(tmp_path):
    kernel = _kernel(tmp_path)

    run = await kernel.create_run({
        "question": "Analyze NVDA",
        "template": {"template_id": "tpl-1", "slug": "earnings-review"},
    })

    loaded = kernel.get_run(run.run_id)
    assert loaded is not None
    assert loaded.events[0].event_type == EventType.RUN_CREATED
    assert loaded.events[0].payload["template"] == {"template_id": "tpl-1", "slug": "earnings-review"}


@pytest.mark.asyncio
async def test_kernel_step_rebuilds_messages_from_events(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})

    await kernel.step(run.run_id)
    await kernel.step(run.run_id)

    loaded = kernel.get_run(run.run_id)
    assert loaded is not None
    assert [event.sequence for event in loaded.events] == sorted(event.sequence for event in loaded.events)
    assert any(event.payload.get("name") == "get_portfolio_exposure" for event in loaded.events)


@pytest.mark.asyncio
async def test_kernel_resolve_approval_resumes_loop(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})
    paused = await kernel.run_to_pause_or_completion(run.run_id)
    approval_id = paused.approvals[0].approval_id

    queued = await kernel.resolve_approval(paused.run_id, approval_id, True)
    completed = await kernel.run_to_pause_or_completion(paused.run_id)

    assert queued.status == RunStatus.QUEUED
    assert completed.status == RunStatus.COMPLETED
    assert completed.artifacts


@pytest.mark.asyncio
async def test_kernel_cancel_run_transitions_state_machine(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})

    cancelling = await kernel.cancel_run(run.run_id)

    assert cancelling.status == RunStatus.CANCELLING
    assert cancelling.cancel_requested_at is not None


@pytest.mark.asyncio
async def test_kernel_resolve_approval_denied_fails_run(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})
    paused = await kernel.run_to_pause_or_completion(run.run_id)

    failed = await kernel.resolve_approval(paused.run_id, paused.approvals[0].approval_id, False)

    assert failed.status == RunStatus.FAILED
    assert failed.artifacts == []
    assert any(
        event.event_type == EventType.APPROVAL_RESOLVED
        and event.payload.get("approved") is False
        for event in failed.events
    )
    assert all(event.event_type != EventType.ARTIFACT_CREATED for event in failed.events)


class SearchThenFinalModel:
    def __init__(self):
        self.calls = []

    async def chat(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        if len(self.calls) == 1:
            yield AgentResponse(message=AgentMessage(role="assistant", content="search facts"))
            return
        assert any("Web search context" in str(message.content) for message in messages)
        yield AgentResponse(message=AgentMessage(role="assistant", content="final memo"))


class BackendRouter:
    def route(self, run, policy):
        return RoutingDecision(
            backend="kimi_agent_sdk",
            model="kimi-k2.6",
            thinking_enabled=True,
        )


class BackendModel:
    async def chat(self, messages, **kwargs):
        raise AssertionError("direct model should not be called")


class FakeBackend:
    def __init__(self):
        self.calls = []

    async def chat(
        self,
        messages,
        tools=None,
        tool_choice=None,
        max_tokens=16384,
        request_metadata=None,
        prompt_cache_key=None,
        model=None,
    ):
        self.calls.append((messages, tools, tool_choice, max_tokens, request_metadata, prompt_cache_key, model))
        yield AgentResponse(message=AgentMessage(role="assistant", content="backend memo"))


class ApprovalBackend:
    async def chat(
        self,
        messages,
        tools=None,
        tool_choice=None,
        max_tokens=16384,
        request_metadata=None,
        prompt_cache_key=None,
        model=None,
    ):
        yield AgentResponse(
            message=AgentMessage(
                role="assistant",
                content="",
                tool_calls=[{
                    "id": "appr-sdk",
                    "type": "function",
                    "function": {
                        "name": "request_approval",
                        "arguments": "{\"action\":\"publish\",\"risk_level\":\"high\"}",
                    },
                }],
            )
        )


class ToolSchemaCaptureModel:
    def __init__(self):
        self.tools = None

    async def chat(self, messages, **kwargs):
        self.tools = kwargs.get("tools")
        yield AgentResponse(message=AgentMessage(role="assistant", content="done"))


class StockToolCallModel:
    async def chat(self, messages, **kwargs):
        yield AgentResponse(
            message=AgentMessage(
                role="assistant",
                content="",
                tool_calls=[{
                    "id": "tool-1",
                    "type": "function",
                    "function": {
                        "name": "stock_overview",
                        "arguments": "{\"ticker\":\"AAPL\",\"market\":\"us\"}",
                    },
                }],
            )
        )


@pytest.mark.asyncio
async def test_kernel_cancel_completed_run_is_idempotent(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})
    paused = await kernel.run_to_pause_or_completion(run.run_id)
    await kernel.resolve_approval(paused.run_id, paused.approvals[0].approval_id, True)
    completed = await kernel.run_to_pause_or_completion(paused.run_id)
    event_count = len(completed.events)

    cancelled = await kernel.cancel_run(completed.run_id)

    assert cancelled.status == RunStatus.COMPLETED
    assert len(cancelled.events) == event_count
    assert all(event.event_type != EventType.RUN_CANCELLED for event in cancelled.events)


@pytest.mark.asyncio
async def test_kernel_step_cancels_mid_run(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})
    run.status = RunStatus.CANCELLING
    kernel._runs.save(run)

    cancelled = await kernel.step(run.run_id)

    assert cancelled.status == RunStatus.CANCELLED
    assert any(event.event_type == EventType.RUN_CANCELLED for event in cancelled.events)


@pytest.mark.asyncio
async def test_kernel_event_sequence_is_contiguous_and_ordered(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})
    paused = await kernel.run_to_pause_or_completion(run.run_id)
    await kernel.resolve_approval(paused.run_id, paused.approvals[0].approval_id, True)
    completed = await kernel.run_to_pause_or_completion(paused.run_id)

    events = completed.events
    event_types = [event.event_type for event in events]

    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    assert event_types[0] == EventType.RUN_CREATED
    assert event_types.index(EventType.APPROVAL_REQUESTED) < event_types.index(EventType.APPROVAL_RESOLVED)
    assert event_types.index(EventType.APPROVAL_RESOLVED) < event_types.index(EventType.RUN_QUEUED)
    assert event_types.index(EventType.RUN_QUEUED) < event_types.index(EventType.ARTIFACT_CREATED)
    assert event_types[-2:] == [EventType.MODEL_RESPONSE, EventType.ARTIFACT_CREATED]
    assert event_types.count(EventType.MODEL_RESPONSE) > 1
    assert event_types.count(EventType.TOOL_CALL) > 1
    assert event_types.count(EventType.TOOL_RESULT) > 1


@pytest.mark.asyncio
async def test_kernel_artifact_only_on_completed(tmp_path):
    kernel = _kernel(tmp_path)
    run = await kernel.create_run({"question": "Analyze AAPL"})
    paused = await kernel.run_to_pause_or_completion(run.run_id)

    assert paused.status == RunStatus.AWAITING_APPROVAL
    assert paused.artifacts == []

    queued = await kernel.resolve_approval(paused.run_id, paused.approvals[0].approval_id, True)
    completed = await kernel.run_to_pause_or_completion(paused.run_id)

    assert queued.status == RunStatus.QUEUED
    assert completed.status == RunStatus.COMPLETED
    assert len(completed.artifacts) == 1
    artifact = completed.artifacts[0]
    assert artifact.kind == "investment_memo"
    assert artifact.data["tool_execution_success"] == 1.0
    assert artifact.data["numerical_consistency"] is None
    assert artifact.data["citation_precision"] is None
    assert "usage" in artifact.data


@pytest.mark.asyncio
async def test_kernel_runs_web_search_stage_when_policy_enabled(tmp_path):
    db = tmp_path / "agent_state.db"
    model = SearchThenFinalModel()
    kernel = RuntimeKernel(
        model=model,
        tool_registry=ToolRegistry(),
        run_repository=SQLiteRunRepository(db),
        event_repository=SQLiteEventRepository(db),
        artifact_repository=SQLiteArtifactRepository(db),
        approval_repository=SQLiteApprovalRepository(db),
    )
    run = await kernel.create_run({
        "question": "Analyze current market",
        "model_policy": {"web_search_enabled": True},
    })

    completed = await kernel.step(run.run_id)

    assert completed.artifacts[0].content == "final memo"
    assert model.calls[0][1]["thinking_enabled"] is False
    assert len(model.calls) == 2


@pytest.mark.asyncio
async def test_kernel_runs_web_search_stage_when_profile_enabled(tmp_path):
    db = tmp_path / "agent_state.db"
    model = SearchThenFinalModel()
    kernel = RuntimeKernel(
        model=model,
        tool_registry=ToolRegistry(),
        run_repository=SQLiteRunRepository(db),
        event_repository=SQLiteEventRepository(db),
        artifact_repository=SQLiteArtifactRepository(db),
        approval_repository=SQLiteApprovalRepository(db),
    )
    run = await kernel.create_run({
        "question": "Analyze current market",
        "model_policy": {"execution_profile": "web_research"},
    })

    completed = await kernel.step(run.run_id)

    assert completed.artifacts[0].content == "final memo"
    assert model.calls[0][1]["thinking_enabled"] is False
    assert len(model.calls) == 2


@pytest.mark.asyncio
async def test_kernel_routes_non_direct_backend_to_injected_backend(tmp_path):
    db = tmp_path / "agent_state.db"
    backend = FakeBackend()
    kernel = RuntimeKernel(
        model=BackendModel(),
        tool_registry=ToolRegistry(),
        run_repository=SQLiteRunRepository(db),
        event_repository=SQLiteEventRepository(db),
        artifact_repository=SQLiteArtifactRepository(db),
        approval_repository=SQLiteApprovalRepository(db),
        model_router=BackendRouter(),
        agent_backends={"kimi_agent_sdk": backend},
    )
    run = await kernel.create_run({"question": "Automate"})

    completed = await kernel.step(run.run_id)

    assert completed.artifacts[0].content == "backend memo"
    assert backend.calls


@pytest.mark.asyncio
async def test_kernel_routes_backend_approval_into_runtime_approval_flow(tmp_path):
    db = tmp_path / "agent_state.db"
    kernel = RuntimeKernel(
        model=BackendModel(),
        tool_registry=_registry(),
        run_repository=SQLiteRunRepository(db),
        event_repository=SQLiteEventRepository(db),
        artifact_repository=SQLiteArtifactRepository(db),
        approval_repository=SQLiteApprovalRepository(db),
        model_router=BackendRouter(),
        agent_backends={"kimi_agent_sdk": ApprovalBackend()},
    )
    run = await kernel.create_run({"question": "Automate"})

    paused = await kernel.step(run.run_id)

    assert paused.status == RunStatus.AWAITING_APPROVAL
    assert paused.approvals[0].action == "publish"
    assert any(event.event_type == EventType.APPROVAL_REQUESTED for event in paused.events)


@pytest.mark.asyncio
async def test_kernel_filters_enterprise_tool_schemas_by_persistent_acl(tmp_path):
    db = tmp_path / "agent_state.db"
    governance = SQLiteEnterpriseGovernanceRepository(db)
    governance.grant(_tool_grant("stock_overview"))
    model = ToolSchemaCaptureModel()
    kernel = RuntimeKernel(
        model=model,
        tool_registry=_registry(),
        run_repository=SQLiteRunRepository(db),
        event_repository=SQLiteEventRepository(db),
        artifact_repository=SQLiteArtifactRepository(db),
        approval_repository=SQLiteApprovalRepository(db),
        governance_repository=governance,
    )
    run = await kernel.create_run({
        "question": "Analyze AAPL",
        "model_policy": _enterprise_policy(),
    })

    await kernel.step(run.run_id)

    assert [schema["function"]["name"] for schema in model.tools] == ["stock_overview"]
    assert "model_route" in [event.event_type for event in governance.list_audit_events("tenant-a")]


@pytest.mark.asyncio
async def test_kernel_denies_enterprise_tool_call_without_persistent_acl(tmp_path):
    db = tmp_path / "agent_state.db"
    governance = SQLiteEnterpriseGovernanceRepository(db)
    kernel = RuntimeKernel(
        model=StockToolCallModel(),
        tool_registry=_registry(),
        run_repository=SQLiteRunRepository(db),
        event_repository=SQLiteEventRepository(db),
        artifact_repository=SQLiteArtifactRepository(db),
        approval_repository=SQLiteApprovalRepository(db),
        governance_repository=governance,
    )
    run = await kernel.create_run({
        "question": "Analyze AAPL",
        "model_policy": _enterprise_policy(),
    })

    stepped = await kernel.step(run.run_id)

    tool_results = [event for event in stepped.events if event.event_type == EventType.TOOL_RESULT]
    assert tool_results[-1].payload["result"]["ok"] is False
    assert tool_results[-1].payload["result"]["error"] == "tool not permitted"
    assert "tool_denied" in [event.event_type for event in governance.list_audit_events("tenant-a")]


@pytest.mark.asyncio
async def test_kernel_allows_enterprise_tool_call_with_persistent_acl(tmp_path):
    db = tmp_path / "agent_state.db"
    governance = SQLiteEnterpriseGovernanceRepository(db)
    governance.grant(_tool_grant("stock_overview"))
    kernel = RuntimeKernel(
        model=StockToolCallModel(),
        tool_registry=_registry(),
        run_repository=SQLiteRunRepository(db),
        event_repository=SQLiteEventRepository(db),
        artifact_repository=SQLiteArtifactRepository(db),
        approval_repository=SQLiteApprovalRepository(db),
        governance_repository=governance,
    )
    run = await kernel.create_run({
        "question": "Analyze AAPL",
        "model_policy": _enterprise_policy(),
    })

    stepped = await kernel.step(run.run_id)

    tool_results = [event for event in stepped.events if event.event_type == EventType.TOOL_RESULT]
    assert tool_results[-1].payload["result"]["ok"] is True
    assert tool_results[-1].payload["result"]["data"]["ticker"] == "AAPL"
    assert "tool_execute" in [event.event_type for event in governance.list_audit_events("tenant-a")]


def _enterprise_policy() -> dict:
    return {
        "tenant_id": "tenant-a",
        "user_hash": "user-a",
        "role": "analyst",
        "request_id": "req-runtime",
    }


def _tool_grant(tool_name: str) -> EnterpriseAclGrant:
    return EnterpriseAclGrant(
        tenant_id="tenant-a",
        subject_hash="user-a",
        resource_type="tool",
        resource_id=tool_name,
        permission="execute",
        provenance="test",
    )
