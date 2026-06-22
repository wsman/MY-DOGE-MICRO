from doge.application.capabilities.fundamental_provider import FundamentalToolProvider


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
        return {"ticker": ticker, "market": market, "sector": "technology"}


def test_fundamental_provider_executes_connector_tools_and_ratios():
    provider = FundamentalToolProvider(
        financial_statement_repository_factory=lambda: Statements(),
        company_announcement_repository_factory=lambda: Announcements(),
        consensus_estimate_repository_factory=lambda: Consensus(),
        industry_classification_source_factory=lambda: Industry(),
    )

    statements = provider.get_financial_statements("MSFT")
    announcements = provider.get_company_announcements("MSFT", 1)
    ratios = provider.calculate_financial_ratios({"revenue": 100, "net_income": 20, "assets": 200, "equity": 50})
    consensus = provider.compare_consensus_estimates("MSFT")
    classification = provider.get_industry_classification("MSFT")

    assert statements["provider_status"] == "fallback"
    assert announcements["limit"] == 1
    assert ratios["ratios"] == {"net_margin": 0.2, "roa": 0.1, "roe": 0.4}
    assert consensus["provider_status"] == "provider_unavailable"
    assert classification["sector"] == "technology"
    assert set(provider.tool_methods()) == {
        "get_financial_statements",
        "get_company_announcements",
        "calculate_financial_ratios",
        "compare_consensus_estimates",
        "get_industry_classification",
    }
