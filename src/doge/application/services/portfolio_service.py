"""Portfolio analytics services."""

from __future__ import annotations

import math
from typing import Any

from doge.core.domain.portfolio_models import Portfolio
from doge.core.ports.financial_connectors import IRiskFactorSource
from doge.core.ports.portfolio_repository import IPortfolioRepository


class PortfolioService:
    def __init__(self, repository: IPortfolioRepository) -> None:
        self._repository = repository

    def get_exposure(self, portfolio_id: str = "portfolio-demo") -> dict[str, Any]:
        portfolio = self._require_portfolio(portfolio_id)
        total = portfolio.total_market_value
        return {
            "portfolio_id": portfolio.portfolio_id,
            "name": portfolio.name,
            "total_market_value": total,
            "by_asset_class": _group_exposure(portfolio, "asset_class"),
            "by_sector": _group_exposure(portfolio, "sector"),
            "holdings": [holding.to_dict() for holding in portfolio.holdings],
        }

    def _require_portfolio(self, portfolio_id: str) -> Portfolio:
        portfolio = self._repository.get(portfolio_id)
        if portfolio is None:
            raise KeyError(f"portfolio not found: {portfolio_id}")
        return portfolio


class _DefaultRiskFactorSource:
    def asset_volatility(self, asset_class: str) -> float:
        return {"equity": 0.22, "bond": 0.08, "cash": 0.01}.get(asset_class, 0.15)

    def asset_drawdown(self, asset_class: str) -> float:
        return {"equity": 0.35, "bond": 0.12, "cash": 0.0}.get(asset_class, 0.2)

    def asset_duration(self, asset_class: str) -> float:
        return {"bond": 7.0}.get(asset_class, 0.0)


class RiskService:
    """Deterministic risk approximations for local demo portfolios."""

    def __init__(
        self,
        repository: IPortfolioRepository,
        risk_factor_source: IRiskFactorSource | None = None,
    ) -> None:
        self._repository = repository
        self._risk_factors = risk_factor_source or _DefaultRiskFactorSource()

    def portfolio_risk(self, portfolio_id: str = "portfolio-demo") -> dict[str, Any]:
        portfolio = self._repository.get(portfolio_id)
        if portfolio is None:
            raise KeyError(f"portfolio not found: {portfolio_id}")
        total = max(portfolio.total_market_value, 1.0)
        weights = [holding.market_value / total for holding in portfolio.holdings]
        weighted_vol = sum(
            weight * self._risk_factors.asset_volatility(holding.asset_class)
            for weight, holding in zip(weights, portfolio.holdings)
        )
        max_drawdown = sum(
            weight * self._risk_factors.asset_drawdown(holding.asset_class)
            for weight, holding in zip(weights, portfolio.holdings)
        )
        var_95 = total * weighted_vol * 1.65 / math.sqrt(252)
        return {
            "portfolio_id": portfolio.portfolio_id,
            "total_market_value": portfolio.total_market_value,
            "annualized_volatility_approx": round(weighted_vol, 6),
            "max_drawdown_approx": round(max_drawdown, 6),
            "var_95_one_day_approx": round(var_95, 2),
            "method": "asset-class weighted deterministic approximation",
            "risk_factor_source": "static_local_assumptions",
        }


class ScenarioService:
    def __init__(
        self,
        repository: IPortfolioRepository,
        risk_factor_source: IRiskFactorSource | None = None,
    ) -> None:
        self._repository = repository
        self._risk_factors = risk_factor_source or _DefaultRiskFactorSource()

    def rate_shock(self, portfolio_id: str = "portfolio-demo", basis_points: float = 100.0) -> dict[str, Any]:
        portfolio = self._repository.get(portfolio_id)
        if portfolio is None:
            raise KeyError(f"portfolio not found: {portfolio_id}")
        total_impact = 0.0
        rows = []
        for holding in portfolio.holdings:
            duration = self._risk_factors.asset_duration(holding.asset_class)
            impact = -holding.market_value * duration * (basis_points / 10000.0)
            total_impact += impact
            rows.append({**holding.to_dict(), "duration_assumption": duration, "impact": round(impact, 2)})
        return {
            "portfolio_id": portfolio.portfolio_id,
            "basis_points": basis_points,
            "estimated_impact": round(total_impact, 2),
            "holdings": rows,
            "method": "duration approximation for bond holdings; non-bond duration assumed 0",
            "risk_factor_source": "static_local_assumptions",
        }


def _group_exposure(portfolio: Portfolio, field: str) -> list[dict[str, Any]]:
    total = max(portfolio.total_market_value, 1.0)
    grouped: dict[str, float] = {}
    for holding in portfolio.holdings:
        key = getattr(holding, field)
        grouped[key] = grouped.get(key, 0.0) + holding.market_value
    return [
        {"name": key, "market_value": value, "weight": round(value / total, 6)}
        for key, value in sorted(grouped.items())
    ]
