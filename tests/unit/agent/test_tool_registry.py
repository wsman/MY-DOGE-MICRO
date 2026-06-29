from doge.application.agent.tool_service import ToolApplicationService
from doge.application.agent.tools import ToolRegistry, ToolResult, build_default_tool_registry
from doge.application.capabilities.compliance_provider import ComplianceToolProvider
from doge.application.capabilities.executors import SubprocessCodeExecutor
from doge.application.capabilities.fundamental_provider import FundamentalToolProvider
from doge.application.capabilities.market_provider import MarketToolProvider
from doge.application.capabilities.portfolio_provider import PortfolioToolProvider
from doge.application.capabilities.publishing_provider import PublishingToolProvider
from doge.application.capabilities.quant_provider import QuantToolProvider
from doge.application.capabilities.research_provider import ResearchToolProvider
from doge.core.domain.enterprise_context import EnterpriseContext
from doge.core.domain.tool_descriptor import ToolDescriptor
from doge.core.domain.tool_policy import ToolCategory


def test_unknown_tool_returns_structured_error():
    result = ToolRegistry().execute("missing", {})

    assert result.ok is False
    assert result.error == "unknown tool"


def test_tool_exception_error_is_redacted_before_returning_trace_data():
    registry = ToolRegistry()

    def failing_tool() -> ToolResult:
        raise RuntimeError("upstream failed with Authorization: Bearer sk-liveSecret123 and MOONSHOT_API_KEY=sk-key")

    registry.register({
        "type": "function",
        "function": {
            "name": "failing_tool",
            "description": "Fails with a secret-shaped message.",
            "parameters": {"type": "object", "properties": {}},
        },
    }, failing_tool)

    result = registry.execute("failing_tool", {})

    assert result.ok is False
    assert result.error == "tool execution failed"
    assert result.safe_error is not None
    assert result.safe_error["code"] == "tool_execution_failed"
    assert result.safe_error["message"] == "tool execution failed"
    assert result.safe_error["internal_reference"].startswith("err-")
    assert "sk-liveSecret123" not in repr(result)
    assert "sk-key" not in repr(result)


def test_default_registry_contains_core_demo_tools():
    registry = build_default_tool_registry()
    names = {schema["function"]["name"] for schema in registry.schemas}

    assert {
        "query_stock",
        "stock_overview",
        "rsrs_ranking",
        "market_breadth",
        "volume_anomalies",
        "list_views",
        "get_portfolio_exposure",
        "portfolio_risk",
        "scenario_analysis",
        "validate_financial_claims",
        "generate_industry_report",
        "lookup_evidence",
        "request_approval",
    }.issubset(names)
    assert {
        "get_financial_statements",
        "get_company_announcements",
        "calculate_financial_ratios",
        "compare_consensus_estimates",
        "get_industry_classification",
        "run_sql_query",
        "run_python_analysis",
        "screen_compliance_risk",
        "publish_investment_memo",
        "propose_portfolio_rebalance",
    }.issubset(names)


def test_default_registry_marks_high_risk_tools():
    registry = build_default_tool_registry()
    categories = {schema["function"]["name"]: schema["x-doge-category"] for schema in registry.schemas}

    assert categories["publish_investment_memo"] == "high_risk"
    assert categories["propose_portfolio_rebalance"] == "high_risk"
    assert categories["run_python_analysis"] == "high_risk"


def test_high_risk_tool_schemas_include_descriptor_owned_risk_metadata():
    registry = build_default_tool_registry()
    metadata = {
        schema["function"]["name"]: schema["x-doge-metadata"]
        for schema in registry.schemas
    }

    for name in {
        "request_approval",
        "publish_investment_memo",
        "propose_portfolio_rebalance",
        "run_python_analysis",
    }:
        assert metadata[name]["risk_level"] == "high"
        assert metadata[name]["approval_required"] is True


def test_default_registry_schemas_are_generated_from_tool_descriptors():
    registry = build_default_tool_registry()
    schemas = {schema["function"]["name"]: schema for schema in registry.schemas}
    descriptor = registry.descriptor_for("run_python_analysis")

    assert descriptor is not None
    assert descriptor.category == ToolCategory.HIGH_RISK
    assert descriptor.provider == "tool_application_service"
    assert descriptor.method_name == "run_python_analysis"
    assert descriptor.to_schema() == schemas["run_python_analysis"]
    assert {item.name for item in registry.descriptors()} == set(schemas)


def test_default_registry_uses_provider_owned_descriptors():
    service = ToolApplicationService()
    registry = build_default_tool_registry(service=service)

    assert {item.name for item in service.tool_descriptors()} == {
        schema["function"]["name"] for schema in registry.schemas
    }


def test_tool_provider_descriptors_match_execution_methods():
    providers = [
        MarketToolProvider(),
        PortfolioToolProvider(),
        ResearchToolProvider(),
        FundamentalToolProvider(),
        QuantToolProvider(),
        ComplianceToolProvider(),
        PublishingToolProvider(),
    ]

    for provider in providers:
        assert {item.name for item in provider.tool_descriptors()} == set(provider.tool_methods())


def test_registry_keeps_legacy_schema_registration_descriptor_compatible():
    registry = ToolRegistry()
    legacy_schema = {
        "type": "function",
        "function": {
            "name": "legacy_tool",
            "description": "Legacy schema path.",
            "parameters": {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        },
    }
    registry.register(
        legacy_schema,
        lambda value: None,
        category=ToolCategory.READ_ONLY,
    )

    descriptor = registry.descriptor_for("legacy_tool")

    assert descriptor == ToolDescriptor(
        name="legacy_tool",
        description="Legacy schema path.",
        properties={"value": {"type": "string"}},
        required=("value",),
        category=ToolCategory.READ_ONLY,
    )


def test_python_analysis_tool_is_disabled_by_default_but_visible_for_capability_discovery():
    registry = build_default_tool_registry()
    schemas = {schema["function"]["name"]: schema for schema in registry.schemas}

    assert schemas["run_python_analysis"]["x-doge-status"] == "disabled"
    assert {
        "executor": "disabled",
        "disabled_reason": "Python analysis execution is disabled by configuration.",
    }.items() <= schemas["run_python_analysis"]["x-doge-metadata"].items()

    result = registry.execute("run_python_analysis", {"code": "print('ok')"})

    assert result.ok is False
    assert result.error == "Python analysis execution is disabled by configuration."
    assert result.data["approval_required"] is True


def test_python_analysis_tool_can_use_explicit_subprocess_demo_executor():
    service = ToolApplicationService(code_executor=SubprocessCodeExecutor())
    registry = build_default_tool_registry(service=service)

    result = registry.execute("run_python_analysis", {"code": "print('ok')"})

    assert result.ok is True
    assert result.data["stdout"].strip() == "ok"
    assert result.data["approval_required"] is True


def test_high_risk_tool_execution_still_requires_approval():
    registry = build_default_tool_registry()

    result = registry.execute("publish_investment_memo", {"memo_id": "memo-1"})

    assert result.ok is True
    assert result.data["approval_required"] is True
    assert result.data["risk_level"] == "high"


def test_portfolio_tool_returns_demo_exposure():
    class FakePortfolioService:
        def get_exposure(self, portfolio_id):
            return {"portfolio_id": portfolio_id, "total_market_value": 100.0}

    service = ToolApplicationService(portfolio_service_factory=lambda: FakePortfolioService())
    registry = build_default_tool_registry(service=service)

    result = registry.execute("get_portfolio_exposure", {"portfolio_id": "portfolio-demo"})

    assert result.ok is True
    assert result.data["total_market_value"] == 100.0


def test_risk_and_scenario_tools_forward_to_services():
    class FakeRiskService:
        def portfolio_risk(self, portfolio_id):
            return {"portfolio_id": portfolio_id, "var_95_one_day_approx": 12.5}

    class FakeScenarioService:
        def rate_shock(self, portfolio_id, basis_points):
            return {"portfolio_id": portfolio_id, "basis_points": basis_points, "estimated_impact": -42.0}

    service = ToolApplicationService(
        risk_service_factory=lambda: FakeRiskService(),
        scenario_service_factory=lambda: FakeScenarioService(),
    )
    registry = build_default_tool_registry(service=service)

    risk = registry.execute("portfolio_risk", {"portfolio_id": "portfolio-demo"})
    scenario = registry.execute("scenario_analysis", {"portfolio_id": "portfolio-demo", "basis_points": 50})

    assert risk.data["var_95_one_day_approx"] == 12.5
    assert scenario.data["estimated_impact"] == -42.0


def test_lookup_evidence_returns_empty_when_library_absent():
    class EmptyNotes:
        def search_notes(self, query, limit=50):
            return []

    class EmptyRAG:
        def search(self, query, document_ids=None, limit=5):
            return {"query": query, "limit": limit, "results": []}

    service = ToolApplicationService(
        rag_service_factory=lambda: EmptyRAG(),
        note_repository_factory=lambda: EmptyNotes(),
    )
    registry = build_default_tool_registry(service=service)

    result = registry.execute("lookup_evidence", {"query": "earnings quality", "limit": 1})

    assert result.ok is True
    assert result.data["results"] == []


def test_lookup_evidence_tool_receives_enterprise_context():
    class EmptyNotes:
        def search_notes(self, query, limit=50):
            return []

    class ScopedRAG:
        def __init__(self):
            self.document_ids = None

        def search(self, query, document_ids=None, limit=5):
            self.document_ids = document_ids
            return {
                "query": query,
                "limit": limit,
                "results": [
                    {"document_id": "doc-allowed", "chunk_id": "chk-1", "text": "allowed"},
                    {"document_id": "doc-denied", "chunk_id": "chk-2", "text": "denied"},
                ],
            }

    rag = ScopedRAG()
    service = ToolApplicationService(
        rag_service_factory=lambda: rag,
        note_repository_factory=lambda: EmptyNotes(),
    )
    context = EnterpriseContext(
        tenant_id="tenant-a",
        user_hash="user-a",
        document_acl=frozenset({"doc-allowed"}),
    )
    registry = build_default_tool_registry(service=service, context=context)

    result = registry.execute("lookup_evidence", {"query": "quality", "limit": 2})

    assert rag.document_ids == ["doc-allowed"]
    assert [item["document_id"] for item in result.data["results"]] == ["doc-allowed"]


def test_generate_industry_report_tool_forwards_to_use_case():
    from doge.application.contracts.response import IndustryReportResponse

    class FakeUseCase:
        def execute(self, request):
            return IndustryReportResponse(
                market=request.market,
                industry=request.industry,
                report_id="industry-us-semiconductor-demo",
                title="Semiconductor Industry Report",
                content="body",
            )

    service = ToolApplicationService(industry_report_use_case_factory=lambda: FakeUseCase())
    registry = build_default_tool_registry(service=service)

    result = registry.execute(
        "generate_industry_report",
        {"industry": "semiconductor", "market": "us", "tickers": ["NVDA"]},
    )

    assert result.ok is True
    assert result.data["report_id"] == "industry-us-semiconductor-demo"
    assert result.data["industry"] == "semiconductor"
