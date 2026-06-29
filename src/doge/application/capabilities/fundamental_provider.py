"""Fundamental data tool execution provider.

Compatibility implementation; canonical facade is `doge.products.research.tools`.
"""

from __future__ import annotations

from typing import Any

from doge.application.capabilities.tool_utils import ServiceFactory, num, resolve
from doge.core.domain.tool_descriptor import ToolDescriptor
from doge.core.domain.tool_policy import ToolCategory


class FundamentalToolProvider:
    """Executes deterministic financial statement and classification tools."""

    def __init__(
        self,
        *,
        financial_statement_repository_factory: ServiceFactory | None = None,
        company_announcement_repository_factory: ServiceFactory | None = None,
        consensus_estimate_repository_factory: ServiceFactory | None = None,
        industry_classification_source_factory: ServiceFactory | None = None,
    ) -> None:
        self._financial_statement_repository_factory = financial_statement_repository_factory
        self._company_announcement_repository_factory = company_announcement_repository_factory
        self._consensus_estimate_repository_factory = consensus_estimate_repository_factory
        self._industry_classification_source_factory = industry_classification_source_factory

    def tool_methods(self) -> dict[str, Any]:
        return {
            "get_financial_statements": self.get_financial_statements,
            "get_company_announcements": self.get_company_announcements,
            "calculate_financial_ratios": self.calculate_financial_ratios,
            "compare_consensus_estimates": self.compare_consensus_estimates,
            "get_industry_classification": self.get_industry_classification,
        }

    def tool_descriptors(self) -> tuple[ToolDescriptor, ...]:
        return (
            ToolDescriptor(
                name="get_financial_statements",
                description="Get demo financial statement fields.",
                properties={
                    "ticker": {"type": "string"},
                    "statement_type": {"type": "string", "enum": ["income", "balance", "cashflow"]},
                    "period": {"type": "string", "enum": ["annual", "quarterly"]},
                },
                required=("ticker",),
                category=ToolCategory.READ_ONLY,
            ),
            ToolDescriptor(
                name="get_company_announcements",
                description="Search local company announcements/notes.",
                properties={
                    "ticker": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                required=("ticker",),
                category=ToolCategory.READ_ONLY,
            ),
            ToolDescriptor(
                name="calculate_financial_ratios",
                description="Calculate deterministic ratios from supplied fields.",
                properties={"fields": {"type": "object"}},
                category=ToolCategory.ANALYTICAL,
            ),
            ToolDescriptor(
                name="compare_consensus_estimates",
                description="Compare demo consensus estimates.",
                properties={
                    "ticker": {"type": "string"},
                    "metric": {"type": "string"},
                },
                required=("ticker",),
                category=ToolCategory.READ_ONLY,
            ),
            ToolDescriptor(
                name="get_industry_classification",
                description="Resolve local industry classification metadata.",
                properties={
                    "ticker": {"type": "string"},
                    "market": {"type": "string", "enum": ["cn", "us"]},
                },
                required=("ticker",),
                category=ToolCategory.READ_ONLY,
            ),
        )

    def get_financial_statements(
        self,
        ticker: str,
        statement_type: str = "income",
        period: str = "annual",
    ) -> dict[str, Any]:
        return self._financial_statement_repository().get_statement(ticker, statement_type, period)

    def get_company_announcements(self, ticker: str, limit: int = 5) -> dict[str, Any]:
        return self._company_announcement_repository().list_announcements(ticker, limit)

    def calculate_financial_ratios(self, fields: dict[str, Any] | None = None) -> dict[str, Any]:
        values = fields or {}
        revenue = num(values.get("revenue"))
        net_income = num(values.get("net_income"))
        assets = num(values.get("assets"))
        equity = num(values.get("equity"))
        ratios: dict[str, float] = {}
        if revenue:
            ratios["net_margin"] = net_income / revenue
        if assets:
            ratios["roa"] = net_income / assets
        if equity:
            ratios["roe"] = net_income / equity
        return {"ratios": ratios, "status": "calculated" if ratios else "insufficient_fields"}

    def compare_consensus_estimates(self, ticker: str, metric: str = "eps") -> dict[str, Any]:
        return self._consensus_estimate_repository().compare_estimates(ticker, metric)

    def get_industry_classification(self, ticker: str, market: str = "us") -> dict[str, Any]:
        return self._industry_classification_source().classify(ticker, market)

    def _financial_statement_repository(self):
        return resolve(self._financial_statement_repository_factory, "financial_statement_repository")

    def _company_announcement_repository(self):
        return resolve(self._company_announcement_repository_factory, "company_announcement_repository")

    def _consensus_estimate_repository(self):
        return resolve(self._consensus_estimate_repository_factory, "consensus_estimate_repository")

    def _industry_classification_source(self):
        return resolve(self._industry_classification_source_factory, "industry_classification_source")
