from doge.application.agent.tools import ToolRegistry, build_default_tool_registry


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
    } == names


def test_portfolio_tool_returns_demo_exposure(monkeypatch):
    from doge.application import composition

    class FakePortfolioService:
        def get_exposure(self, portfolio_id):
            return {"portfolio_id": portfolio_id, "total_market_value": 100.0}

    monkeypatch.setattr(composition, "build_portfolio_service", lambda: FakePortfolioService())
    registry = build_default_tool_registry()

    result = registry.execute("get_portfolio_exposure", {"portfolio_id": "portfolio-demo"})

    assert result.ok is True
    assert result.data["total_market_value"] == 100.0


def test_risk_and_scenario_tools_forward_to_services(monkeypatch):
    from doge.application import composition

    class FakeRiskService:
        def portfolio_risk(self, portfolio_id):
            return {"portfolio_id": portfolio_id, "var_95_one_day_approx": 12.5}

    class FakeScenarioService:
        def rate_shock(self, portfolio_id, basis_points):
            return {"portfolio_id": portfolio_id, "basis_points": basis_points, "estimated_impact": -42.0}

    monkeypatch.setattr(composition, "build_risk_service", lambda: FakeRiskService())
    monkeypatch.setattr(composition, "build_scenario_service", lambda: FakeScenarioService())
    registry = build_default_tool_registry()

    risk = registry.execute("portfolio_risk", {"portfolio_id": "portfolio-demo"})
    scenario = registry.execute("scenario_analysis", {"portfolio_id": "portfolio-demo", "basis_points": 50})

    assert risk.data["var_95_one_day_approx"] == 12.5
    assert scenario.data["estimated_impact"] == -42.0


def test_lookup_evidence_returns_empty_when_library_absent(monkeypatch):
    from doge.application import composition

    class EmptyNotes:
        def search_notes(self, query, limit=50):
            return []

    class EmptyRAG:
        def search(self, query, limit=5):
            return {"query": query, "limit": limit, "results": []}

    monkeypatch.setattr(composition, "build_rag_service", lambda: EmptyRAG())
    monkeypatch.setattr(composition, "build_note_repository", lambda: EmptyNotes())
    registry = build_default_tool_registry()

    result = registry.execute("lookup_evidence", {"query": "earnings quality", "limit": 1})

    assert result.ok is True
    assert result.data["results"] == []


def test_generate_industry_report_tool_forwards_to_use_case(monkeypatch):
    from doge.application import composition
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

    monkeypatch.setattr(composition, "build_generate_industry_report_use_case", lambda: FakeUseCase())
    registry = build_default_tool_registry()

    result = registry.execute(
        "generate_industry_report",
        {"industry": "semiconductor", "market": "us", "tickers": ["NVDA"]},
    )

    assert result.ok is True
    assert result.data["report_id"] == "industry-us-semiconductor-demo"
    assert result.data["industry"] == "semiconductor"
