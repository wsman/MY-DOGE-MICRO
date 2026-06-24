"""Shared application service for provider-backed tool execution."""

from __future__ import annotations

from typing import Any

from doge.application.capabilities.compliance_provider import ComplianceToolProvider
from doge.application.capabilities.fundamental_provider import FundamentalToolProvider
from doge.application.capabilities.market_provider import MarketToolProvider
from doge.application.capabilities.portfolio_provider import PortfolioToolProvider
from doge.application.capabilities.publishing_provider import PublishingToolProvider
from doge.application.capabilities.executors import DisabledCodeExecutor
from doge.application.capabilities.quant_provider import QuantToolProvider
from doge.application.capabilities.registry import ToolExecutionProviderRegistry
from doge.application.capabilities.research_provider import ResearchToolProvider
from doge.application.capabilities.tool_utils import ServiceFactory
from doge.core.domain.tool_descriptor import ToolDescriptor
from doge.core.ports.code_executor import ICodeExecutor


class ToolApplicationService:
    """Thin facade over the canonical tool execution provider registry."""

    def __init__(
        self,
        stock_service_factory: ServiceFactory | None = None,
        *,
        ranking_service_factory: ServiceFactory | None = None,
        breadth_service_factory: ServiceFactory | None = None,
        anomaly_service_factory: ServiceFactory | None = None,
        view_service_factory: ServiceFactory | None = None,
        portfolio_service_factory: ServiceFactory | None = None,
        risk_service_factory: ServiceFactory | None = None,
        scenario_service_factory: ServiceFactory | None = None,
        rag_service_factory: ServiceFactory | None = None,
        note_repository_factory: ServiceFactory | None = None,
        industry_report_use_case_factory: ServiceFactory | None = None,
        financial_statement_repository_factory: ServiceFactory | None = None,
        company_announcement_repository_factory: ServiceFactory | None = None,
        consensus_estimate_repository_factory: ServiceFactory | None = None,
        industry_classification_source_factory: ServiceFactory | None = None,
        view_repository_factory: ServiceFactory | None = None,
        code_executor: ICodeExecutor | None = None,
        use_capability_providers: bool = True,
        execution_provider_registry: ToolExecutionProviderRegistry | None = None,
    ) -> None:
        # `use_capability_providers` is retained as a compatibility parameter.
        # Provider Registry is now the single execution path.
        self._code_executor = code_executor or DisabledCodeExecutor()
        self._execution_provider_registry = execution_provider_registry or self._build_execution_provider_registry(
            stock_service_factory=stock_service_factory,
            ranking_service_factory=ranking_service_factory,
            breadth_service_factory=breadth_service_factory,
            anomaly_service_factory=anomaly_service_factory,
            view_service_factory=view_service_factory,
            portfolio_service_factory=portfolio_service_factory,
            risk_service_factory=risk_service_factory,
            scenario_service_factory=scenario_service_factory,
            rag_service_factory=rag_service_factory,
            note_repository_factory=note_repository_factory,
            industry_report_use_case_factory=industry_report_use_case_factory,
            financial_statement_repository_factory=financial_statement_repository_factory,
            company_announcement_repository_factory=company_announcement_repository_factory,
            consensus_estimate_repository_factory=consensus_estimate_repository_factory,
            industry_classification_source_factory=industry_classification_source_factory,
            view_repository_factory=view_repository_factory,
            code_executor=self._code_executor,
        )

    def execution_provider_method_names(self) -> tuple[str, ...]:
        """Return provider-backed method names for parity tests and diagnostics."""
        return self._execution_provider_registry.method_names()

    def tool_descriptors(self) -> tuple[ToolDescriptor, ...]:
        """Return provider-owned descriptors for default registry assembly."""
        return self._execution_provider_registry.tool_descriptors()

    def python_analysis_capability_status(self) -> dict[str, Any]:
        """Return capability metadata for the Python analysis executor."""
        available = bool(getattr(self._code_executor, "available", False))
        metadata: dict[str, Any] = {
            "executor": str(getattr(self._code_executor, "executor_name", "unknown")),
        }
        disabled_reason = getattr(self._code_executor, "disabled_reason", None)
        if disabled_reason:
            metadata["disabled_reason"] = str(disabled_reason)
        return {
            "status": "available" if available else "disabled",
            "metadata": metadata,
        }

    def _build_execution_provider_registry(
        self,
        *,
        stock_service_factory: ServiceFactory | None,
        ranking_service_factory: ServiceFactory | None,
        breadth_service_factory: ServiceFactory | None,
        anomaly_service_factory: ServiceFactory | None,
        view_service_factory: ServiceFactory | None,
        portfolio_service_factory: ServiceFactory | None,
        risk_service_factory: ServiceFactory | None,
        scenario_service_factory: ServiceFactory | None,
        rag_service_factory: ServiceFactory | None,
        note_repository_factory: ServiceFactory | None,
        industry_report_use_case_factory: ServiceFactory | None,
        financial_statement_repository_factory: ServiceFactory | None,
        company_announcement_repository_factory: ServiceFactory | None,
        consensus_estimate_repository_factory: ServiceFactory | None,
        industry_classification_source_factory: ServiceFactory | None,
        view_repository_factory: ServiceFactory | None,
        code_executor: ICodeExecutor,
    ) -> ToolExecutionProviderRegistry:
        return ToolExecutionProviderRegistry([
            MarketToolProvider(
                stock_service_factory=stock_service_factory,
                ranking_service_factory=ranking_service_factory,
                breadth_service_factory=breadth_service_factory,
                anomaly_service_factory=anomaly_service_factory,
            ),
            PortfolioToolProvider(
                portfolio_service_factory=portfolio_service_factory,
                risk_service_factory=risk_service_factory,
                scenario_service_factory=scenario_service_factory,
            ),
            ResearchToolProvider(
                stock_service_factory=stock_service_factory,
                rag_service_factory=rag_service_factory,
                note_repository_factory=note_repository_factory,
                industry_report_use_case_factory=industry_report_use_case_factory,
            ),
            FundamentalToolProvider(
                financial_statement_repository_factory=financial_statement_repository_factory,
                company_announcement_repository_factory=company_announcement_repository_factory,
                consensus_estimate_repository_factory=consensus_estimate_repository_factory,
                industry_classification_source_factory=industry_classification_source_factory,
            ),
            QuantToolProvider(
                view_service_factory=view_service_factory,
                view_repository_factory=view_repository_factory,
                code_executor=code_executor,
            ),
            ComplianceToolProvider(),
            PublishingToolProvider(),
        ])

    def _provider_execute(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        return self._execution_provider_registry.execute(method_name, *args, **kwargs)

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

    def get_portfolio_exposure(self, portfolio_id: str = "portfolio-demo") -> dict[str, Any]:
        return self._provider_execute("get_portfolio_exposure", portfolio_id)

    def portfolio_risk(self, portfolio_id: str = "portfolio-demo") -> dict[str, Any]:
        return self._provider_execute("portfolio_risk", portfolio_id)

    def scenario_analysis(self, portfolio_id: str = "portfolio-demo", basis_points: float = 100.0) -> dict[str, Any]:
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
