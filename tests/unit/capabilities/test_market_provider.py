import pytest

from doge.products.market.tools import MarketToolProvider

pytestmark = pytest.mark.module_market


class StockService:
    def query(self, ticker, market, days):
        return [{"ticker": ticker, "market": market, "close": 101.5, "days": days}]

    def overview(self, ticker, market):
        return {"ticker": ticker, "market": market, "status": "ok"}


class RankingService:
    def rsrs(self, market, top):
        return [{"ticker": "AAPL", "rank": 1, "market": market, "top": top}]


class BreadthService:
    def breadth(self, market, days):
        return [{"market": market, "advancers": 10, "days": days}]


class AnomalyService:
    def anomalies(self, min_ratio, top):
        return [{"ticker": "NVDA", "ratio": min_ratio, "top": top}]


def test_market_provider_executes_market_tools():
    provider = MarketToolProvider(
        stock_service_factory=lambda: StockService(),
        ranking_service_factory=lambda: RankingService(),
        breadth_service_factory=lambda: BreadthService(),
        anomaly_service_factory=lambda: AnomalyService(),
    )

    assert provider.query_stock("AAPL", "us", 5)["rows"][0]["close"] == 101.5
    assert provider.stock_overview("AAPL", "us")["status"] == "ok"
    assert provider.rsrs_ranking("us", 1)["rows"][0]["rank"] == 1
    assert provider.market_breadth("us", 2)["rows"][0]["advancers"] == 10
    assert provider.volume_anomalies(3.0, 2)["rows"][0]["ratio"] == 3.0
    assert set(provider.tool_methods()) == {
        "query_stock",
        "stock_overview",
        "rsrs_ranking",
        "market_breadth",
        "volume_anomalies",
    }
