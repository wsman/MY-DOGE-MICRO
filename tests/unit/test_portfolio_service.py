from doge.application.services.portfolio_service import PortfolioService, RiskService, ScenarioService
from doge.core.domain.portfolio_models import Portfolio, PortfolioHolding
from doge.infrastructure.database.portfolio_repository import SQLitePortfolioRepository, demo_portfolio


class AggressiveRiskFactors:
    def asset_volatility(self, asset_class):
        return 0.5

    def asset_drawdown(self, asset_class):
        return 0.75

    def asset_duration(self, asset_class):
        return 10.0 if asset_class == "bond" else 0.0


def test_portfolio_repository_round_trips_holdings(tmp_path):
    repo = SQLitePortfolioRepository(tmp_path / "agent_state.db")
    repo.save(demo_portfolio())

    portfolio = repo.get("portfolio-demo")

    assert portfolio is not None
    assert portfolio.total_market_value == 70000.0
    assert portfolio.holdings[0].symbol == "AAPL"


def test_portfolio_repository_filters_by_tenant(tmp_path):
    repo = SQLitePortfolioRepository(tmp_path / "agent_state.db")
    repo.save(Portfolio(portfolio_id="p1", name="Tenant A", holdings=[]), tenant_id="tenant-a")
    repo.save(Portfolio(portfolio_id="p2", name="Tenant B", holdings=[]), tenant_id="tenant-b")

    assert repo.get("p1", tenant_id="tenant-a") is not None
    assert repo.get("p2", tenant_id="tenant-a") is None
    assert repo.get("p2").name == "Tenant B"


def test_portfolio_service_groups_exposure(tmp_path):
    repo = SQLitePortfolioRepository(tmp_path / "agent_state.db")
    repo.save(Portfolio(
        portfolio_id="p1",
        name="Test",
        holdings=[
            PortfolioHolding("AAA", "equity", "technology", 60.0),
            PortfolioHolding("BBB", "bond", "rates", 40.0),
        ],
    ))

    result = PortfolioService(repo).get_exposure("p1")

    assert result["total_market_value"] == 100.0
    assert {"name": "technology", "market_value": 60.0, "weight": 0.6} in result["by_sector"]
    assert {"name": "bond", "market_value": 40.0, "weight": 0.4} in result["by_asset_class"]


def test_risk_service_returns_deterministic_metrics(tmp_path):
    repo = SQLitePortfolioRepository(tmp_path / "agent_state.db")
    repo.save(demo_portfolio())

    result = RiskService(repo).portfolio_risk("portfolio-demo")

    assert result["annualized_volatility_approx"] > 0
    assert result["var_95_one_day_approx"] > 0
    assert result["method"] == "asset-class weighted deterministic approximation"


def test_scenario_service_applies_rate_shock_to_bonds(tmp_path):
    repo = SQLitePortfolioRepository(tmp_path / "agent_state.db")
    repo.save(demo_portfolio())

    result = ScenarioService(repo).rate_shock("portfolio-demo", basis_points=100)

    assert result["estimated_impact"] == -1260.0
    assert any(item["symbol"] == "TLT" and item["impact"] == -1260.0 for item in result["holdings"])


def test_risk_and_scenario_services_accept_factor_source(tmp_path):
    repo = SQLitePortfolioRepository(tmp_path / "agent_state.db")
    repo.save(demo_portfolio())

    risk = RiskService(repo, AggressiveRiskFactors()).portfolio_risk("portfolio-demo")
    scenario = ScenarioService(repo, AggressiveRiskFactors()).rate_shock("portfolio-demo", basis_points=100)

    assert risk["annualized_volatility_approx"] == 0.5
    assert risk["max_drawdown_approx"] == 0.75
    assert any(item["symbol"] == "TLT" and item["duration_assumption"] == 10.0 for item in scenario["holdings"])
