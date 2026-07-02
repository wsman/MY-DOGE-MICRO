"""Shared application service for provider-backed tool execution."""

from __future__ import annotations

from typing import Any

from doge.application.tools.execution_service import ToolExecutionService


COMPATIBILITY_TOOL_METHODS = (
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
)


class ToolApplicationService(ToolExecutionService):
    """Thin facade over the canonical tool execution provider registry."""

    def query_stock(self, ticker: str, market: str = "us", days: int = 20) -> dict[str, Any]:
        return self._provider_execute("query_stock", ticker, market, days)

    def stock_overview(self, ticker: str, market: str = "us") -> dict[str, Any]:
        return self._provider_execute("stock_overview", ticker, market)

    def rsrs_ranking(self, market: str = "us", top: int = 20) -> dict[str, Any]:
        return self._provider_execute("rsrs_ranking", market, top)

    def market_breadth(self, market: str = "us", days: int = 10) -> dict[str, Any]:
        return self._provider_execute("market_breadth", market, days)

    def volume_anomalies(self, min_ratio: float = 3.0, top: int = 20) -> dict[str, Any]:
        return self._provider_execute("volume_anomalies", min_ratio, top)

    def list_views(self) -> dict[str, Any]:
        return self._provider_execute("list_views")

    def get_portfolio_exposure(self, portfolio_id: str) -> dict[str, Any]:
        return self._provider_execute("get_portfolio_exposure", portfolio_id)

    def portfolio_risk(self, portfolio_id: str) -> dict[str, Any]:
        return self._provider_execute("portfolio_risk", portfolio_id)

    def scenario_analysis(self, portfolio_id: str, basis_points: float = 100.0) -> dict[str, Any]:
        return self._provider_execute("scenario_analysis", portfolio_id, basis_points)

    def validate_financial_claims(
        self,
        claim: str,
        ticker: str = "AAPL",
        market: str = "us",
        *,
        context: Any = None,
    ) -> dict[str, Any]:
        return self._provider_execute("validate_financial_claims", claim, ticker, market, context=context)

    def generate_industry_report(
        self,
        industry: str = "semiconductor",
        market: str = "us",
        tickers: list[str] | None = None,
    ) -> dict[str, Any]:
        return self._provider_execute("generate_industry_report", industry, market, tickers)

    def lookup_evidence(self, query: str, limit: int = 5, *, context: Any = None) -> dict[str, Any]:
        return self._provider_execute("lookup_evidence", query, limit, context=context)

    def request_approval(self, action: str, risk_level: str = "high") -> dict[str, Any]:
        return self._provider_execute("request_approval", action, risk_level)

    def get_financial_statements(
        self,
        ticker: str,
        statement_type: str = "income",
        period: str = "annual",
    ) -> dict[str, Any]:
        return self._provider_execute("get_financial_statements", ticker, statement_type, period)

    def get_company_announcements(self, ticker: str, limit: int = 5) -> dict[str, Any]:
        return self._provider_execute("get_company_announcements", ticker, limit)

    def calculate_financial_ratios(self, fields: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._provider_execute("calculate_financial_ratios", fields)

    def compare_consensus_estimates(self, ticker: str, metric: str = "eps") -> dict[str, Any]:
        return self._provider_execute("compare_consensus_estimates", ticker, metric)

    def get_industry_classification(self, ticker: str, market: str = "us") -> dict[str, Any]:
        return self._provider_execute("get_industry_classification", ticker, market)

    def run_sql_query(self, sql: str, readonly: bool = True) -> dict[str, Any]:
        return self._provider_execute("run_sql_query", sql, readonly)

    def run_python_analysis(self, code: str, timeout: float = 5.0) -> dict[str, Any]:
        return self._provider_execute("run_python_analysis", code, timeout)

    def screen_compliance_risk(self, text: str) -> dict[str, Any]:
        return self._provider_execute("screen_compliance_risk", text)

    def publish_investment_memo(self, memo_id: str, distribution_list: list[str] | None = None) -> dict[str, Any]:
        return self._provider_execute("publish_investment_memo", memo_id, distribution_list)

    def propose_portfolio_rebalance(
        self,
        portfolio_id: str,
        proposed_changes: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return self._provider_execute("propose_portfolio_rebalance", portfolio_id, proposed_changes)
