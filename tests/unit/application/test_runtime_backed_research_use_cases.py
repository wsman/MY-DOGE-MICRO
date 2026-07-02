import pytest

from doge.application.use_cases.industry_analyzer import IndustryAnalyzerAgentUseCase
from doge.application.use_cases.macro_strategist import MacroStrategistAgentUseCase
from doge.application.use_cases.run_use_cases import ExecuteRun
from doge.core.domain.agent_models import AgentRun, RunStatus

pytestmark = pytest.mark.module_research


class FakeRuntime:
    def __init__(self):
        self.requests = []
        self.scopes = []

    async def create_run(self, scope, request=None):
        if request is None:
            request = scope
            scope = None
        self.scopes.append(scope)
        self.requests.append(request)
        return AgentRun.create(
            workflow=request["workflow"],
            question=request["question"],
            market=request["market"],
            document_ids=request["document_ids"],
            portfolio_id=request["portfolio_id"],
            model_policy=request["model_policy"],
        )

    async def run_to_pause_or_completion(self, scope, run_id=None):
        if run_id is None:
            run_id = scope
        run = AgentRun.create(workflow="completed", question="done", run_id=run_id)
        run.status = RunStatus.COMPLETED
        run.add_artifact("investment_memo", "memo", "done")
        return run


@pytest.mark.asyncio
async def test_execute_run_use_case_uses_local_scope():
    runtime = FakeRuntime()

    run = await ExecuteRun(runtime).execute("Analyze AAPL")

    assert run.status == RunStatus.COMPLETED
    assert runtime.requests[0]["workflow"] == "investment_research"
    assert runtime.scopes[0].tenant_id == "local"


@pytest.mark.asyncio
async def test_macro_strategist_agent_use_case_creates_runtime_run():
    runtime = FakeRuntime()

    run = await MacroStrategistAgentUseCase(runtime).execute(market="us")

    assert run.status == RunStatus.COMPLETED
    assert runtime.requests[0]["workflow"] == "macro_research"
    assert runtime.requests[0]["model_policy"].execution_profile == "financial_research"
    assert runtime.scopes[0].tenant_id == "local"


@pytest.mark.asyncio
async def test_industry_analyzer_agent_use_case_creates_runtime_run():
    runtime = FakeRuntime()

    run = await IndustryAnalyzerAgentUseCase(runtime).execute(industry="semiconductor", market="us")

    assert run.status == RunStatus.COMPLETED
    assert runtime.requests[0]["workflow"] == "industry_research"
    assert "semiconductor" in runtime.requests[0]["question"]
    assert runtime.scopes[0].tenant_id == "local"
