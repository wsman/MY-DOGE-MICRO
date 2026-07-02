"""Factory for the default provider-backed tool execution registry."""

from __future__ import annotations

from doge.application.capabilities.registry import ToolExecutionProviderRegistry
from doge.application.capabilities.tool_utils import ServiceFactory
from doge.core.ports.code_executor import ICodeExecutor
from doge.platform.governance.tools import ComplianceToolProvider, PublishingToolProvider
from doge.products.market.tools import MarketToolProvider
from doge.products.portfolio.tools import PortfolioToolProvider
from doge.products.quant.tools import QuantToolProvider
from doge.products.research.tools import FundamentalToolProvider, ResearchToolProvider


def build_default_execution_provider_registry(
    *,
    stock_service_factory: ServiceFactory | None = None,
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
