from types import SimpleNamespace

import pytest

from doge.application.agent.model_router import ModelRouter
from doge.core.domain.agent_models import AgentRun
from doge.core.domain.enterprise_context import IdentitySnapshot
from doge.core.domain.model_policy import ModelPolicy
from doge.core.domain.run_execution_context import RunExecutionContext, WorkflowRunContext


class DocumentRepo:
    def __init__(self, documents):
        self._documents = documents

    def get(self, document_id):
        return self._documents.get(document_id)


def _settings():
    return SimpleNamespace(kimi=SimpleNamespace(general_model="kimi-k2.6", code_model="kimi-k2.7-code"))


def test_model_router_routes_financial_research_to_general_thinking_model():
    run = AgentRun.create(workflow="investment_research", question="q")
    decision = ModelRouter(settings=_settings()).route(run, ModelPolicy())

    assert decision.backend == "direct_kimi_api"
    assert decision.model == "kimi-k2.6"
    assert decision.thinking_enabled is True
    assert decision.files_purpose == "file-extract"


def test_model_router_routes_quant_code_to_code_model_and_rejects_non_thinking():
    run = AgentRun.create(workflow="investment_research", question="q")
    router = ModelRouter(settings=_settings())

    decision = router.route(run, ModelPolicy.from_dict({"execution_profile": "quant_code"}))

    assert decision.model == "kimi-k2.7-code"
    assert decision.thinking_enabled is True

    with pytest.raises(ValueError, match="quant_code requires thinking_enabled=True"):
        router.route(run, ModelPolicy.from_dict({"execution_profile": "quant_code", "thinking_enabled": False}))


def test_model_router_overrides_purpose_for_image_document():
    run = AgentRun.create(
        workflow="investment_research",
        question="q",
        document_ids=["doc-image"],
    )
    documents = DocumentRepo({"doc-image": {"mime_type": "image/png"}})

    decision = ModelRouter(settings=_settings(), document_repository=documents).route(run, ModelPolicy())

    assert decision.files_purpose == "image"


def test_model_router_accepts_web_research_profile():
    run = AgentRun.create(workflow="investment_research", question="q")

    decision = ModelRouter(settings=_settings()).route(
        run,
        ModelPolicy.from_dict({"execution_profile": "web_research"}),
    )

    assert decision.model == "kimi-k2.6"
    assert decision.thinking_enabled is True


def test_model_router_uses_execution_context_identity_for_safety_identifier():
    run = AgentRun.create(workflow="investment_research", question="q")
    execution_context = RunExecutionContext(
        run_id=run.run_id,
        question=run.question,
        model_policy=ModelPolicy(),
        identity_snapshot=IdentitySnapshot(tenant_id="tenant-a", user_hash="user-a"),
        workflow=WorkflowRunContext(workflow=run.workflow),
    )

    decision = ModelRouter(settings=_settings()).route(
        run,
        ModelPolicy(),
        execution_context=execution_context,
    )

    assert decision.safety_identifier == "user-a"
