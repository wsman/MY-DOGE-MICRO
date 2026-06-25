"""Portfolio repository port."""

from __future__ import annotations

from typing import Protocol

from doge.core.domain.portfolio_models import Portfolio
from doge.shared.scope import TenantScope


class IPortfolioRepository(Protocol):
    def save(self, portfolio: Portfolio, scope: TenantScope) -> None:
        ...

    def get(self, portfolio_id: str, scope: TenantScope) -> Portfolio | None:
        ...
