"""Portfolio repository port."""

from __future__ import annotations

from typing import Protocol

from doge.core.domain.portfolio_models import Portfolio


class IPortfolioRepository(Protocol):
    def save(self, portfolio: Portfolio, tenant_id: str | None = None) -> None:
        ...

    def get(self, portfolio_id: str, tenant_id: str | None = None) -> Portfolio | None:
        ...
