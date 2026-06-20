import pytest

from doge.application.agent.research_runtime import ResearchAgentRuntime, ScriptedAgentModel
from doge.core.domain.agent_models import EventType, RunStatus


@pytest.mark.asyncio
async def test_scripted_runtime_pauses_for_approval_then_completes():
    runtime = ResearchAgentRuntime(model=ScriptedAgentModel())
    run = await runtime.create_run({
        "workflow": "investment_research",
        "question": "Analyze earnings quality and portfolio risk.",
        "portfolio_id": "portfolio-demo",
        "model_policy": {"max_tool_rounds": 8},
    })

    run = await runtime.run_to_pause_or_completion(run.run_id)

    assert run.status == RunStatus.AWAITING_APPROVAL
    assert run.approvals
    assert EventType.TOOL_CALL in {event.event_type for event in run.events}
    assert EventType.APPROVAL_REQUESTED in {event.event_type for event in run.events}

    run = await runtime.resolve_approval(run.run_id, run.approvals[0].approval_id, True)

    assert run.status == RunStatus.COMPLETED
    assert run.artifacts[0].kind == "investment_memo"
    assert "Investment Committee Memo" in run.artifacts[0].content


def test_missing_run_returns_none_and_empty_lookup_errors():
    runtime = ResearchAgentRuntime(model=ScriptedAgentModel())

    assert runtime.get_run("missing") is None
    with pytest.raises(KeyError):
        runtime.list_events("missing")
