import pytest

from doge.application.use_cases.industry_analyzer import IndustryAnalyzerAgentUseCase
from doge.application.use_cases.macro_strategist import MacroStrategistAgentUseCase
from doge.core.domain.agent_models import AgentRun, RunStatus


class FakeRuntime:
    def __init__(self):
        self.requests = []

    async def create_run(self, request):
        self.requests.append(request)
        return AgentRun.create(
            workflow=request["workflow"],
            question=request["question"],
            market=request["market"],
            document_ids=request["document_ids"],
            portfolio_id=request["portfolio_id"],
            model_policy=request["model_policy"],
        )

    async def run_to_pause_or_completion(self, run_id):
        run = AgentRun.create(workflow="completed", question="done", run_id=run_id)
        run.status = RunStatus.COMPLETED
        run.add_artifact("investment_memo", "memo", "done")
        return run


@pytest.mark.asyncio
async def test_macro_strategist_agent_use_case_creates_runtime_run():
    runtime = FakeRuntime()

    run = await MacroStrategistAgentUseCase(runtime).execute(market="us")

    assert run.status == RunStatus.COMPLETED
    assert runtime.requests[0]["workflow"] == "macro_research"
    assert runtime.requests[0]["model_policy"].execution_profile == "financial_research"


@pytest.mark.asyncio
async def test_industry_analyzer_agent_use_case_creates_runtime_run():
    runtime = FakeRuntime()

    run = await IndustryAnalyzerAgentUseCase(runtime).execute(industry="semiconductor", market="us")

    assert run.status == RunStatus.COMPLETED
    assert runtime.requests[0]["workflow"] == "industry_research"
    assert "semiconductor" in runtime.requests[0]["question"]
