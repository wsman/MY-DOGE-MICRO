from doge.application.agent.tool_service import ToolApplicationService
from doge.application.agent.tools import ToolRegistry, build_default_tool_registry
from doge.core.domain.enterprise_context import EnterpriseContext


def test_unknown_tool_returns_structured_error():
    result = ToolRegistry().execute("missing", {})

    assert result.ok is False
    assert result.error == "unknown tool"


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
