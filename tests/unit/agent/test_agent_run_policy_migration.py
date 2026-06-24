from doge.core.domain.agent_models import AgentRun
from doge.core.domain.model_policy import ModelPolicy
from doge.core.domain.run_execution_context import WorkflowRunContext
from doge.infrastructure.database.agent_repositories import SQLiteRunRepository


def test_agent_run_create_normalizes_dict_policy():
    run = AgentRun.create(
        workflow="investment_research",
        question="q",
        model_policy={"execution_profile": "quant_code", "max_tool_rounds": 3},
    )

    assert isinstance(run.model_policy, ModelPolicy)
    assert run.model_policy.execution_profile == "quant_code"
    assert run.model_policy.max_tool_rounds == 3


def test_sqlite_run_repository_roundtrips_model_policy(tmp_path):
    db = tmp_path / "agent_state.db"
    repo = SQLiteRunRepository(db)
    run = AgentRun.create(
        workflow="investment_research",
        question="q",
        model_policy={"execution_profile": "vision_analysis", "max_tokens": 1024},
    )

    repo.save(run)
    loaded = repo.get(run.run_id)

    assert loaded is not None
    assert isinstance(loaded.model_policy, ModelPolicy)
    assert loaded.model_policy.execution_profile == "vision_analysis"
    assert loaded.model_policy.max_tokens == 1024


def test_sqlite_run_repository_roundtrips_workflow_context(tmp_path):
    db = tmp_path / "agent_state.db"
    repo = SQLiteRunRepository(db)
    run = AgentRun.create(
        workflow="earnings-review",
        question="q",
        model_policy={"execution_profile": "financial_research"},
        workflow_context=WorkflowRunContext(
            workflow="earnings-review",
            template_id="tpl-1",
            template_slug="earnings-review",
            template_metadata={"input_keys": ["ticker"]},
        ),
    )

    repo.save(run)
    loaded = repo.get(run.run_id)

    assert loaded is not None
    assert isinstance(loaded.workflow_context, WorkflowRunContext)
    assert loaded.workflow_context.template_id == "tpl-1"
    assert loaded.workflow_context.template_slug == "earnings-review"
    assert loaded.workflow_context.template_metadata == {"input_keys": ["ticker"]}
