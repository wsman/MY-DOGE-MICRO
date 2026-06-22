import json

from doge.application.agent.tool_service import ToolApplicationService
from doge.application.agent.tools import build_default_tool_registry
from doge.core.domain.enterprise_context import EnterpriseContext
from doge.core.domain.tool_policy import ToolCategory


class StockService:
    def query(self, ticker, market, days):
        return [{"ticker": ticker, "market": market, "close": 101.5, "volume": 1000, "days": days}]

    def overview(self, ticker, market):
        return {"ticker": ticker, "market": market, "status": "ok"}


class RankingService:
    def rsrs(self, market, top):
        return [{"ticker": "AAPL", "rank": 1, "market": market, "top": top}]


class BreadthService:
    def breadth(self, market, days):
        return [{"market": market, "advancers": 10, "days": days}]


class AnomalyService:
    def anomalies(self, min_ratio, top):
        return [{"ticker": "NVDA", "ratio": min_ratio, "top": top}]


class ViewService:
    def list_views(self):
        return json.dumps([{"name": "prices", "kind": "view"}])


class PortfolioService:
    def get_exposure(self, portfolio_id):
        return {"portfolio_id": portfolio_id, "total_market_value": 100.0}


class RiskService:
    def portfolio_risk(self, portfolio_id):
        return {"portfolio_id": portfolio_id, "var_95_one_day_approx": 12.5}


class ScenarioService:
    def rate_shock(self, portfolio_id, basis_points):
        return {"portfolio_id": portfolio_id, "basis_points": basis_points, "estimated_impact": -42.0}


class RAGService:
    def search(self, query, document_ids=None, limit=5):
        return {
            "query": query,
            "limit": limit,
            "results": [{"document_id": "doc-allowed", "chunk_id": "chk-1", "text": "earnings quality improved"}],
        }


class Notes:
    def search_notes(self, query, limit=50):
        return [{"source": "note", "text": query}]


class ReportUseCase:
    def execute(self, request):
        return {"market": request.market, "industry": request.industry, "tickers": request.tickers or []}


class Statements:
    def get_statement(self, ticker, statement_type="income", period="annual"):
        return {"ticker": ticker, "statement_type": statement_type, "period": period, "provider_status": "fallback"}


class Announcements:
    def list_announcements(self, ticker, limit=5):
        return {"ticker": ticker, "announcements": [{"title": "Q1"}], "limit": limit}


class Consensus:
    def compare_estimates(self, ticker, metric="eps"):
        return {"ticker": ticker, "metric": metric, "provider_status": "provider_unavailable"}


class Industry:
    def classify(self, ticker, market="us"):
        return {"ticker": ticker, "market": market, "sector": "technology", "industry": "software"}


class Frame:
    def to_dict(self, orient="records"):
        assert orient == "records"
        return [{"ticker": "AAPL", "close": 101.5}]


class ViewRepository:
    def execute(self, sql, params):
        assert params == []
        assert sql == "select * from prices"
        return Frame()


class FailingStockService:
    def query(self, ticker, market, days):
        raise RuntimeError("service unavailable")


class ReadOnlyEntitlement:
    def can_execute(self, context, tool_name, category):
        return category == ToolCategory.READ_ONLY

    def requires_approval(self, context, tool_name, category):
        return category == ToolCategory.HIGH_RISK

    def redact_schema(self, context, schema, category):
        if not self.can_execute(context, schema.get("function", {}).get("name", ""), category):
            return None
        return schema


def test_provider_facade_method_registry_covers_tool_service_surface():
    service = _service(use_capability_providers=True)

    assert set(service.execution_provider_method_names()) == {
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
    }


def test_provider_facade_direct_method_results_match_legacy_path():
    direct = _service(use_capability_providers=False)
    provider = _service(use_capability_providers=True)

    assert _direct_results(direct) == _direct_results(provider)


def test_provider_facade_registry_schema_and_execution_results_match_legacy_path():
    direct_registry = build_default_tool_registry(service=_service(use_capability_providers=False))
    provider_registry = build_default_tool_registry(service=_service(use_capability_providers=True))

    assert _schema_signature(direct_registry) == _schema_signature(provider_registry)
    for name, arguments in _registry_cases():
        direct = direct_registry.execute(name, arguments)
        provider = provider_registry.execute(name, arguments)
        assert (direct.ok, direct.error, direct.data) == (provider.ok, provider.error, provider.data)


def test_provider_facade_high_risk_tools_still_require_approval():
    registry = build_default_tool_registry(service=_service(use_capability_providers=True))

    result = registry.execute("publish_investment_memo", {"memo_id": "memo-1"})

    assert result.ok is True
    assert result.data["approval_required"] is True
    assert result.data["risk_level"] == "high"


def test_provider_facade_forbidden_tools_remain_unavailable():
    registry = build_default_tool_registry(
        service=_service(use_capability_providers=True),
        entitlement_checker=ReadOnlyEntitlement(),
    )

    hidden = {schema["function"]["name"] for schema in registry.schemas_for_context()}
    result = registry.execute("publish_investment_memo", {"memo_id": "memo-1"})

    assert "publish_investment_memo" not in hidden
    assert result.ok is False
    assert result.error == "tool not permitted"


def test_provider_facade_enterprise_acl_remains_deny_by_default():
    service = _service(use_capability_providers=True)
    context = EnterpriseContext(tenant_id="tenant-a", user_hash="user-a")

    result = service.lookup_evidence("earnings", 2, context=context)

    assert result == {"query": "earnings", "limit": 2, "source": "rag", "results": []}


def test_provider_facade_preserves_dependency_error_propagation():
    service = ToolApplicationService(
        stock_service_factory=lambda: FailingStockService(),
        use_capability_providers=True,
    )

    try:
        service.query_stock("AAPL", "us", 5)
    except RuntimeError as exc:
        assert str(exc) == "service unavailable"
    else:
        raise AssertionError("expected provider-backed query_stock to propagate dependency failure")


def test_composition_uses_provider_facade_only_when_capability_registry_flag_is_on(monkeypatch, tmp_path):
    from doge.application import composition
    from doge.config import reset_settings

    monkeypatch.delenv("DOGE_FEATURE_CAPABILITY_REGISTRY", raising=False)
    reset_settings()
    default_service = composition.build_tool_application_service(db_path=tmp_path / "default.db")

    monkeypatch.setenv("DOGE_FEATURE_CAPABILITY_REGISTRY", "1")
    reset_settings()
    flagged_service = composition.build_tool_application_service(db_path=tmp_path / "flagged.db")

    assert default_service.execution_provider_method_names() == ()
    assert "query_stock" in flagged_service.execution_provider_method_names()

    reset_settings()


def _service(*, use_capability_providers: bool) -> ToolApplicationService:
    return ToolApplicationService(
        stock_service_factory=lambda: StockService(),
        ranking_service_factory=lambda: RankingService(),
        breadth_service_factory=lambda: BreadthService(),
        anomaly_service_factory=lambda: AnomalyService(),
        view_service_factory=lambda: ViewService(),
        portfolio_service_factory=lambda: PortfolioService(),
        risk_service_factory=lambda: RiskService(),
        scenario_service_factory=lambda: ScenarioService(),
        rag_service_factory=lambda: RAGService(),
        note_repository_factory=lambda: Notes(),
        industry_report_use_case_factory=lambda: ReportUseCase(),
        financial_statement_repository_factory=lambda: Statements(),
        company_announcement_repository_factory=lambda: Announcements(),
        consensus_estimate_repository_factory=lambda: Consensus(),
        industry_classification_source_factory=lambda: Industry(),
        view_repository_factory=lambda: ViewRepository(),
        use_capability_providers=use_capability_providers,
    )


def _direct_results(service: ToolApplicationService) -> dict[str, object]:
    return {
        "query_stock": service.query_stock("AAPL", "us", 5),
        "stock_overview": service.stock_overview("AAPL", "us"),
        "rsrs_ranking": service.rsrs_ranking("us", 1),
        "market_breadth": service.market_breadth("us", 2),
        "volume_anomalies": service.volume_anomalies(3.0, 2),
        "list_views": service.list_views(),
        "get_portfolio_exposure": service.get_portfolio_exposure("portfolio-demo"),
        "portfolio_risk": service.portfolio_risk("portfolio-demo"),
        "scenario_analysis": service.scenario_analysis("portfolio-demo", 50),
        "validate_financial_claims": service.validate_financial_claims("earnings quality improved", "AAPL", "us"),
        "generate_industry_report": service.generate_industry_report("software", "us", ["MSFT"]),
        "lookup_evidence": service.lookup_evidence("earnings", 1),
        "request_approval": service.request_approval("publish", "high"),
        "get_financial_statements": service.get_financial_statements("MSFT"),
        "get_company_announcements": service.get_company_announcements("MSFT", 1),
        "calculate_financial_ratios": service.calculate_financial_ratios(
            {"revenue": 100, "net_income": 20, "assets": 200, "equity": 50}
        ),
        "compare_consensus_estimates": service.compare_consensus_estimates("MSFT"),
        "get_industry_classification": service.get_industry_classification("MSFT"),
        "run_sql_query": service.run_sql_query("select * from prices"),
        "run_python_analysis": service.run_python_analysis("print('ok')"),
        "screen_compliance_risk": service.screen_compliance_risk("guaranteed return"),
        "publish_investment_memo": service.publish_investment_memo("memo-1", ["ops@example.test"]),
        "propose_portfolio_rebalance": service.propose_portfolio_rebalance("portfolio-demo", [{"ticker": "AAPL"}]),
    }


def _schema_signature(registry):
    return [
        (
            schema["function"]["name"],
            schema["x-doge-category"],
            schema["function"]["parameters"],
        )
        for schema in registry.schemas
    ]


def _registry_cases():
    return [
        ("query_stock", {"ticker": "AAPL", "market": "us", "days": 5}),
        ("stock_overview", {"ticker": "AAPL", "market": "us"}),
        ("rsrs_ranking", {"market": "us", "top": 1}),
        ("market_breadth", {"market": "us", "days": 2}),
        ("volume_anomalies", {"min_ratio": 3.0, "top": 2}),
        ("list_views", {}),
        ("get_portfolio_exposure", {"portfolio_id": "portfolio-demo"}),
        ("portfolio_risk", {"portfolio_id": "portfolio-demo"}),
        ("scenario_analysis", {"portfolio_id": "portfolio-demo", "basis_points": 50}),
        ("validate_financial_claims", {"claim": "earnings quality improved", "ticker": "AAPL", "market": "us"}),
        ("generate_industry_report", {"industry": "software", "market": "us", "tickers": ["MSFT"]}),
        ("lookup_evidence", {"query": "earnings", "limit": 1}),
        ("request_approval", {"action": "publish", "risk_level": "high"}),
        ("get_financial_statements", {"ticker": "MSFT"}),
        ("get_company_announcements", {"ticker": "MSFT", "limit": 1}),
        (
            "calculate_financial_ratios",
            {"fields": {"revenue": 100, "net_income": 20, "assets": 200, "equity": 50}},
        ),
        ("compare_consensus_estimates", {"ticker": "MSFT"}),
        ("get_industry_classification", {"ticker": "MSFT", "market": "us"}),
        ("run_sql_query", {"sql": "select * from prices"}),
        ("run_python_analysis", {"code": "print('ok')"}),
        ("screen_compliance_risk", {"text": "guaranteed return"}),
        ("publish_investment_memo", {"memo_id": "memo-1", "distribution_list": ["ops@example.test"]}),
        ("propose_portfolio_rebalance", {"portfolio_id": "portfolio-demo", "proposed_changes": [{"ticker": "AAPL"}]}),
    ]
