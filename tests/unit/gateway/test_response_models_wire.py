"""Wire-preservation regression for /v1 platform response models.

Sprint 018 added ``response_model`` declarations to the platform GET endpoints so
the entity shapes appear in OpenAPI. ``response_model`` validation filters
undeclared keys by default; these tests lock in that every response model uses
``extra="allow"`` so the existing ``serialize()``/``asdict()`` wire format is
preserved byte-for-byte (no dataclass field dropped, no runtime-only field
dropped, free-form dict fields passed through).
"""

from __future__ import annotations

from doge.core.domain.agent_models import AgentApproval
from doge.core.domain.platform_models import (
    CaseDecision,
    Project,
    ResearchCase,
    WorkflowExecution,
    WorkflowTemplate,
    Workspace,
)
from doge.interfaces.gateway.routers._common import serialize
from doge.interfaces.gateway.routers._response_models import (
    ApprovalListResponse,
    ApprovalResponse,
    CaseDecisionResponse,
    ProjectResponse,
    ResearchCaseResponse,
    RunClaimResponse,
    RunEvalResponse,
    WorkflowExecutionResponse,
    WorkflowTemplateResponse,
    WorkspaceResponse,
)


def test_workspace_response_preserves_dataclass_fields_and_extras():
    workspace = Workspace(
        workspace_id="w-1",
        name="Test",
        description="d",
        tenant_id="t-1",
        metadata={"keep": "me"},
    )
    payload = serialize(workspace)
    payload["runtime_only_field"] = "preserved"

    out = WorkspaceResponse.model_validate(payload).model_dump()

    assert out["workspace_id"] == "w-1"
    assert out["tenant_id"] == "t-1"
    assert out["metadata"] == {"keep": "me"}
    assert out["runtime_only_field"] == "preserved"


def test_workflow_template_response_preserves_free_form_dict_fields():
    template = WorkflowTemplate(
        template_id="tpl-1",
        slug="s",
        name="n",
        input_schema={"a": 1},
        metadata={"contract": {"required_capabilities": ["cap-1"]}},
    )

    out = WorkflowTemplateResponse.model_validate(serialize(template)).model_dump()

    assert out["input_schema"] == {"a": 1}
    assert out["metadata"] == {"contract": {"required_capabilities": ["cap-1"]}}


def test_each_entity_response_accepts_its_serialized_dataclass():
    pairs = [
        (WorkspaceResponse, Workspace(workspace_id="w", name="n")),
        (ProjectResponse, Project(project_id="p", workspace_id="w", name="n")),
        (ResearchCaseResponse, ResearchCase(case_id="c", project_id="p", title="t")),
        (WorkflowExecutionResponse, WorkflowExecution(execution_id="e", case_id="c", template_id="t")),
        (CaseDecisionResponse, CaseDecision(decision_id="d", case_id="c", decision_type="approve")),
        (
            ApprovalResponse,
            AgentApproval(
                approval_id="a",
                action="publish",
                risk_level="high",
                why_needed="why",
                impact="impact",
                deny_consequence="deny",
                publish_target="target",
            ),
        ),
    ]
    for response_model, dataclass_instance in pairs:
        out = response_model.model_validate(serialize(dataclass_instance)).model_dump()
        # Every declared field round-trips (no validation rejection).
        assert response_model.model_fields.keys() <= set(out.keys())


def test_run_eval_response_validates_full_backend_shape():
    payload = {
        "eval_id": "e1",
        "run_id": "r1",
        "summary_id": "s1",
        "coverage_ratio": 0.5,
        "claim_count": 3,
        "supported_claim_count": 2,
        "citation_count": 4,
        "accessible_citation_count": 4,
        "claim_evidence_relation_count": 3,
        "supported_relation_count": 2,
        "partial_relation_count": 1,
        "unrelated_relation_count": 0,
        "classification_confidence_avg": 0.66,
        "failed_checks": ["x"],
        "numeric_validation": {"n": 1},
        "metrics": {"m": 2, "contradicted_relation_count": 0},
    }

    out = RunEvalResponse.model_validate(payload).model_dump()

    assert out["classification_confidence_avg"] == 0.66
    assert out["numeric_validation"] == {"n": 1}
    assert out["metrics"]["contradicted_relation_count"] == 0


def test_run_claim_response_preserves_structured_claim_fields():
    payload = {
        "claim_id": "claim-1",
        "summary_id": "summary-1",
        "run_id": "run-1",
        "claim_text": "Revenue grew 12%.",
        "support_status": "supported",
        "status": "supported",
        "evidence_refs": [{"evidence_id": "evd-1", "source": "doc p.1"}],
        "numeric_check_status": "passed",
        "risk_level": "low",
        "evidence_count": 1,
        "source": "artifact",
    }

    out = RunClaimResponse.model_validate(payload).model_dump()

    assert out["status"] == "supported"
    assert out["numeric_check_status"] == "passed"
    assert out["risk_level"] == "low"
    assert out["evidence_refs"][0]["evidence_id"] == "evd-1"


def test_approval_list_response_preserves_explanation_fields():
    approval = AgentApproval(
        approval_id="appr-1",
        action="publish memo",
        risk_level="high",
        run_id="run-1",
        why_needed="Publishing requires review.",
        impact="Memo can be distributed.",
        deny_consequence="Run stops before publishing.",
        publish_target="ic@example.com",
    )

    out = ApprovalListResponse.model_validate({"approvals": [serialize(approval)]}).model_dump()

    item = out["approvals"][0]
    assert item["why_needed"] == "Publishing requires review."
    assert item["impact"] == "Memo can be distributed."
    assert item["deny_consequence"] == "Run stops before publishing."
    assert item["publish_target"] == "ic@example.com"
