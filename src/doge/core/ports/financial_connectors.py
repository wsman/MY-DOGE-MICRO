"""Ports for replaceable financial research data connectors."""

from __future__ import annotations

from typing import Any, Protocol


class IFinancialStatementRepository(Protocol):
    """Read normalized financial statement fields from a provider."""

    def get_statement(self, ticker: str, statement_type: str = "income", period: str = "annual") -> dict[str, Any]:
        ...


class ICompanyAnnouncementRepository(Protocol):
    """Read company announcements or disclosures from a provider."""

    def list_announcements(self, ticker: str, limit: int = 5) -> dict[str, Any]:
        ...


class IConsensusEstimateRepository(Protocol):
    """Read sell-side or provider consensus estimates."""

    def compare_estimates(self, ticker: str, metric: str = "eps") -> dict[str, Any]:
        ...


class IIndustryClassificationSource(Protocol):
    """Resolve ticker-to-industry metadata."""

    def classify(self, ticker: str, market: str = "us") -> dict[str, Any]:
        ...


class IRiskFactorSource(Protocol):
    """Provide configurable assumptions for demo risk/scenario tools."""

    def asset_volatility(self, asset_class: str) -> float:
        ...

    def asset_drawdown(self, asset_class: str) -> float:
        ...

    def asset_duration(self, asset_class: str) -> float:
        ...
