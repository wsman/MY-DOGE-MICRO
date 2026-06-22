"""Portfolio tool execution provider."""

from __future__ import annotations

from typing import Any

from doge.application.capabilities.tool_utils import ServiceFactory, resolve


class PortfolioToolProvider:
    """Executes portfolio exposure, risk, and scenario tools."""

    def __init__(
        self,
        *,
        portfolio_service_factory: ServiceFactory | None = None,
        risk_service_factory: ServiceFactory | None = None,
        scenario_service_factory: ServiceFactory | None = None,
    ) -> None:
        self._portfolio_service_factory = portfolio_service_factory
        self._risk_service_factory = risk_service_factory
        self._scenario_service_factory = scenario_service_factory

    def tool_methods(self) -> dict[str, Any]:
        return {
            "get_portfolio_exposure": self.get_portfolio_exposure,
            "portfolio_risk": self.portfolio_risk,
            "scenario_analysis": self.scenario_analysis,
        }

    def get_portfolio_exposure(self, portfolio_id: str = "portfolio-demo") -> dict[str, Any]:
        return self._portfolio_service().get_exposure(portfolio_id)

    def portfolio_risk(self, portfolio_id: str = "portfolio-demo") -> dict[str, Any]:
        return self._risk_service().portfolio_risk(portfolio_id)

    def scenario_analysis(self, portfolio_id: str = "portfolio-demo", basis_points: float = 100.0) -> dict[str, Any]:
        return self._scenario_service().rate_shock(portfolio_id, basis_points)

    def _portfolio_service(self):
        return resolve(self._portfolio_service_factory, "portfolio_service")

    def _risk_service(self):
        return resolve(self._risk_service_factory, "risk_service")

    def _scenario_service(self):
        return resolve(self._scenario_service_factory, "scenario_service")
