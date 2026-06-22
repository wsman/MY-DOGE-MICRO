from doge.application.capabilities.portfolio_provider import PortfolioToolProvider


class PortfolioService:
    def get_exposure(self, portfolio_id):
        return {"portfolio_id": portfolio_id, "total_market_value": 100.0}


class RiskService:
    def portfolio_risk(self, portfolio_id):
        return {"portfolio_id": portfolio_id, "var_95_one_day_approx": 12.5}


class ScenarioService:
    def rate_shock(self, portfolio_id, basis_points):
        return {"portfolio_id": portfolio_id, "basis_points": basis_points, "estimated_impact": -42.0}


def test_portfolio_provider_executes_portfolio_tools():
    provider = PortfolioToolProvider(
        portfolio_service_factory=lambda: PortfolioService(),
        risk_service_factory=lambda: RiskService(),
        scenario_service_factory=lambda: ScenarioService(),
    )

    exposure = provider.get_portfolio_exposure("portfolio-demo")
    risk = provider.portfolio_risk("portfolio-demo")
    scenario = provider.scenario_analysis("portfolio-demo", 50)

    assert exposure["total_market_value"] == 100.0
    assert risk["var_95_one_day_approx"] == 12.5
    assert scenario["estimated_impact"] == -42.0
    assert set(provider.tool_methods()) == {
        "get_portfolio_exposure",
        "portfolio_risk",
        "scenario_analysis",
    }
