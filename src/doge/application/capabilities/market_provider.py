"""Market data tool execution provider."""

from __future__ import annotations

from typing import Any

from doge.application.capabilities.tool_utils import ServiceFactory, resolve


class MarketToolProvider:
    """Executes read-only market data and ranking tools."""

    def __init__(
        self,
        *,
        stock_service_factory: ServiceFactory | None = None,
        ranking_service_factory: ServiceFactory | None = None,
        breadth_service_factory: ServiceFactory | None = None,
        anomaly_service_factory: ServiceFactory | None = None,
    ) -> None:
        self._stock_service_factory = stock_service_factory
        self._ranking_service_factory = ranking_service_factory
        self._breadth_service_factory = breadth_service_factory
        self._anomaly_service_factory = anomaly_service_factory

    def tool_methods(self) -> dict[str, Any]:
        return {
            "query_stock": self.query_stock,
            "stock_overview": self.stock_overview,
            "rsrs_ranking": self.rsrs_ranking,
            "market_breadth": self.market_breadth,
            "volume_anomalies": self.volume_anomalies,
        }

    def query_stock(self, ticker: str, market: str = "us", days: int = 20) -> dict[str, Any]:
        rows = self._stock_service().query(ticker, market, days)
        return {"ticker": ticker, "market": market, "days": days, "rows": rows}

    def stock_overview(self, ticker: str, market: str = "us") -> dict[str, Any]:
        data = self._stock_service().overview(ticker, market)
        return data or {"ticker": ticker, "market": market, "status": "unavailable"}

    def rsrs_ranking(self, market: str = "us", top: int = 20) -> dict[str, Any]:
        rows = self._ranking_service().rsrs(market, top)
        return {"market": market, "top": top, "rows": rows}

    def market_breadth(self, market: str = "us", days: int = 10) -> dict[str, Any]:
        rows = self._breadth_service().breadth(market, days)
        return {"market": market, "days": days, "rows": rows}

    def volume_anomalies(self, min_ratio: float = 3.0, top: int = 20) -> dict[str, Any]:
        rows = self._anomaly_service().anomalies(min_ratio, top)
        return {"min_ratio": min_ratio, "top": top, "rows": rows}

    def _stock_service(self):
        return resolve(self._stock_service_factory, "stock_service")

    def _ranking_service(self):
        return resolve(self._ranking_service_factory, "ranking_service")

    def _breadth_service(self):
        return resolve(self._breadth_service_factory, "breadth_service")

    def _anomaly_service(self):
        return resolve(self._anomaly_service_factory, "anomaly_service")
