import pytest

from doge.application.agent.tools import ToolRegistry, ToolResult
from doge.application.composition import build_persisted_research_agent_runtime
from doge.core.domain.agent_models import RunStatus
from doge.infrastructure.agent.inmemory_runtime import InMemoryResearchAgentRuntime
from doge.infrastructure.agent.scripted_model import ScriptedAgentModel
from doge.shared.scope import TenantScope


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


@pytest.mark.asyncio
async def test_inmemory_runtime_completes_full_approval_flow():
    runtime = InMemoryResearchAgentRuntime(model=ScriptedAgentModel(), tool_registry=_registry())
    run = await runtime.create_run({"question": "Analyze AAPL", "model_policy": {"max_tool_rounds": 8}})

    paused = await runtime.run_to_pause_or_completion(run.run_id)
    queued = await runtime.resolve_approval(paused.run_id, paused.approvals[0].approval_id, True)
    completed = await runtime.run_to_pause_or_completion(paused.run_id)

    assert paused.status == RunStatus.AWAITING_APPROVAL
    assert queued.status == RunStatus.QUEUED
    assert completed.status == RunStatus.COMPLETED
    assert completed.artifacts
    assert [event.sequence for event in completed.events] == list(range(1, len(completed.events) + 1))


@pytest.mark.asyncio
async def test_inmemory_repositories_match_sqlite_semantics(tmp_path):
    in_memory = InMemoryResearchAgentRuntime(model=ScriptedAgentModel(), tool_registry=_registry())
    persisted = build_persisted_research_agent_runtime(
        model=ScriptedAgentModel(),
        tool_registry=_registry(),
        db_path=tmp_path / "agent_state.db",
    )

    async def run_flow(runtime):
        run = await runtime.create_run({"question": "Analyze AAPL", "model_policy": {"max_tool_rounds": 8}})
        paused = await runtime.run_to_pause_or_completion(run.run_id)
        await runtime.resolve_approval(paused.run_id, paused.approvals[0].approval_id, True)
        return await runtime.run_to_pause_or_completion(paused.run_id)

    mem_run = await run_flow(in_memory)
    sql_run = await run_flow(persisted)

    assert [event.sequence for event in mem_run.events] == [event.sequence for event in sql_run.events]
    assert [event.event_type for event in mem_run.events] == [event.event_type for event in sql_run.events]
    assert len(mem_run.artifacts) == len(sql_run.artifacts) == 1
    assert len(mem_run.approvals) == len(sql_run.approvals) == 1


@pytest.mark.asyncio
async def test_persisted_runtime_scope_first_create_and_run(tmp_path):
    runtime = build_persisted_research_agent_runtime(
        model=ScriptedAgentModel(),
        tool_registry=_registry(),
        db_path=tmp_path / "agent_state.db",
    )
    scope = TenantScope.enterprise("tenant-a", "user-a")

    run = await runtime.create_run(
        scope,
        {"question": "Analyze AAPL", "model_policy": {"max_tool_rounds": 8}},
    )
    paused = await runtime.run_to_pause_or_completion(scope, run.run_id)

    assert run.identity_snapshot is not None
    assert run.identity_snapshot.tenant_id == "tenant-a"
    assert run.identity_snapshot.user_hash == "user-a"
    assert runtime.get_run(scope, run.run_id) is not None
    assert runtime.get_run(TenantScope.enterprise("tenant-b", "user-b"), run.run_id) is None
    assert paused.status in {RunStatus.AWAITING_APPROVAL, RunStatus.COMPLETED}


@pytest.mark.asyncio
async def test_persisted_runtime_scope_first_rejects_spoofed_identity(tmp_path):
    runtime = build_persisted_research_agent_runtime(
        model=ScriptedAgentModel(),
        tool_registry=_registry(),
        db_path=tmp_path / "agent_state.db",
    )
    scope = TenantScope.enterprise("tenant-a", "user-a")

    with pytest.raises(ValueError, match="tenant mismatch"):
        await runtime.create_run(
            scope,
            {"question": "Analyze AAPL", "identity_snapshot": {"tenant_id": "tenant-b", "user_hash": "user-a"}},
        )
    with pytest.raises(ValueError, match="subject mismatch"):
        await runtime.create_run(
            scope,
            {"question": "Analyze AAPL", "identity_snapshot": {"tenant_id": "tenant-a", "user_hash": "user-b"}},
        )


@pytest.mark.asyncio
async def test_adapter_stream_events_matches_list_events():
    runtime = InMemoryResearchAgentRuntime(model=ScriptedAgentModel(), tool_registry=_registry())
    run = await runtime.create_run({"question": "Analyze AAPL", "model_policy": {"max_tool_rounds": 8}})
    paused = await runtime.run_to_pause_or_completion(run.run_id)
    await runtime.resolve_approval(paused.run_id, paused.approvals[0].approval_id, True)
    completed = await runtime.run_to_pause_or_completion(paused.run_id)

    streamed = [event async for event in runtime.stream_events(completed.run_id)]

    assert streamed == runtime.list_events(completed.run_id)
