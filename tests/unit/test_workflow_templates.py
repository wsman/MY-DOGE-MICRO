from doge.core.domain.platform_models import WorkflowTemplate
from doge.core.domain.workflow_template import TemplateRunInput, build_template_run_request


def test_template_run_request_merges_policy_and_preserves_metadata():
    template = WorkflowTemplate.create(
        slug="earnings-review",
        name="Earnings review",
        current_version="2",
    )
    template = WorkflowTemplate(
        **{
            **template.__dict__,
            "run_instructions": "Review the latest earnings call.",
            "tool_policy": {
                "model_policy": {"execution_profile": "financial_research", "max_tool_rounds": 5},
                "max_tokens": 4096,
                "allowed_tools": ["stock_overview"],
            },
            "evidence_policy": {"required_citations": 2},
            "output_contract": {"kind": "memo"},
        }
    )

    request = build_template_run_request(
        template,
        TemplateRunInput(
            question="Analyze NVDA Q1",
            model_policy={"max_tool_rounds": 3, "web_search_enabled": True},
            inputs={"ticker": "NVDA"},
        ),
        tenant_id="tenant-a",
        user_hash="user-a",
    )

    assert request["workflow"] == "earnings-review"
    assert request["question"] == "Analyze NVDA Q1"
    assert request["model_policy"]["execution_profile"] == "financial_research"
    assert request["model_policy"]["max_tool_rounds"] == 3
    assert request["model_policy"]["max_tokens"] == 4096
    assert request["model_policy"]["web_search_enabled"] is True
    assert request["model_policy"]["tenant_id"] == "tenant-a"
    assert request["model_policy"]["user_hash"] == "user-a"
    assert request["model_policy"]["template_id"] == template.template_id
    assert request["model_policy"]["template_slug"] == "earnings-review"
    assert request["template"]["inputs"] == {"ticker": "NVDA"}
    assert request["template"]["input_keys"] == ["ticker"]
    assert request["template"]["evidence_policy"] == {"required_citations": 2}
