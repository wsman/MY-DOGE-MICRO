from doge.core.domain.agent_models import AgentRun
from doge.core.domain.enterprise_context import IdentitySnapshot
from doge.core.domain.run_execution_context import RunExecutionContext, WorkflowRunContext


def test_run_execution_context_extracts_policy_identity_and_template_metadata():
    run = AgentRun.create(
        workflow="investment_research",
        question="Review NVDA",
        model_policy={
            "execution_profile": "financial_research",
            "template_id": "tpl-1",
            "template_slug": "earnings-review",
            "template_version": "2",
            "template_name": "Earnings Review",
        },
        identity_snapshot=IdentitySnapshot(
            tenant_id="tenant-a",
            user_hash="user-a",
            request_id="req-1",
        ),
    )

    context = RunExecutionContext.from_run(run)

    assert context.model_policy.execution_profile == "financial_research"
    assert context.identity_snapshot is not None
    assert context.enterprise_context.tenant_id == "tenant-a"
    assert context.request_id == "req-1"
    assert context.workflow.workflow == "investment_research"
    assert context.workflow.template_id == "tpl-1"
    assert context.workflow.template_slug == "earnings-review"
    assert context.workflow.template_metadata["template_name"] == "Earnings Review"


def test_run_execution_context_prefers_first_class_workflow_context():
    run = AgentRun.create(
        workflow="investment_research",
        question="Review NVDA",
        model_policy={
            "template_id": "legacy-tpl",
            "template_slug": "legacy-template",
        },
        workflow_context=WorkflowRunContext(
            workflow="earnings-review",
            template_id="tpl-1",
            template_slug="earnings-review",
            template_version="2",
            template_name="Earnings Review",
            template_metadata={"input_keys": ["ticker"]},
        ),
    )

    context = RunExecutionContext.from_run(run)

    assert context.workflow.workflow == "earnings-review"
    assert context.workflow.template_id == "tpl-1"
    assert context.workflow.template_slug == "earnings-review"
    assert context.workflow.template_metadata == {"input_keys": ["ticker"]}
