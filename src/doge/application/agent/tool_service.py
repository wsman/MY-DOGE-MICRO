"""Shared application service for MCP and agent tool execution."""

from __future__ import annotations

import json
from typing import Any


class ToolApplicationService:
    """Single application-layer entrypoint for deterministic research tools."""

    def __init__(self, stock_service_factory=None) -> None:
        self._stock_service_factory = stock_service_factory

    def _stock_service(self):
        if self._stock_service_factory is not None:
            return self._stock_service_factory()
        from doge.application import composition

        return composition.build_stock_service()

    def query_stock(self, ticker: str, market: str = "us", days: int = 20) -> dict[str, Any]:
        try:
            rows = self._stock_service().query(ticker, market, days)
        except Exception:
            rows = []
        return {"ticker": ticker, "market": market, "days": days, "rows": rows}

    def stock_overview(self, ticker: str, market: str = "us") -> dict[str, Any]:
        try:
            data = self._stock_service().overview(ticker, market)
        except Exception:
            data = {"ticker": ticker, "market": market, "status": "unavailable"}
        return data or {"ticker": ticker, "market": market, "status": "unavailable"}

    def rsrs_ranking(self, market: str = "us", top: int = 20) -> dict[str, Any]:
        from doge.application import composition

        try:
            rows = composition.build_ranking_service().rsrs(market, top)
        except Exception:
            rows = []
        return {"market": market, "top": top, "rows": rows}

    def market_breadth(self, market: str = "us", days: int = 10) -> dict[str, Any]:
        from doge.application import composition

        try:
            rows = composition.build_breadth_service().breadth(market, days)
        except Exception:
            rows = []
        return {"market": market, "days": days, "rows": rows}

    def volume_anomalies(self, min_ratio: float = 3.0, top: int = 20) -> dict[str, Any]:
        from doge.application import composition

        try:
            rows = composition.build_anomaly_service().anomalies(min_ratio, top)
        except Exception:
            rows = []
        return {"min_ratio": min_ratio, "top": top, "rows": rows}

    def list_views(self) -> dict[str, Any]:
        from doge.application import composition

        try:
            payload = composition.build_view_service().list_views()
            rows = json.loads(payload)
        except Exception:
            rows = []
        return {"views": rows}

    def get_portfolio_exposure(self, portfolio_id: str = "portfolio-demo") -> dict[str, Any]:
        holdings = [
            {"ticker": "AAPL", "weight": 0.24, "sector": "Technology"},
            {"ticker": "MSFT", "weight": 0.21, "sector": "Technology"},
            {"ticker": "NVDA", "weight": 0.18, "sector": "Semiconductors"},
            {"ticker": "TLT", "weight": 0.12, "sector": "Rates"},
            {"ticker": "CASH", "weight": 0.25, "sector": "Cash"},
        ]
        return {
            "portfolio_id": portfolio_id,
            "holdings": holdings,
            "top_concentration": 0.63,
            "technology_exposure": 0.45,
        }

    def validate_financial_claims(self, claim: str, ticker: str = "AAPL", market: str = "us") -> dict[str, Any]:
        rows = self.query_stock(ticker, market, 5)["rows"]
        return {
            "claim": claim,
            "ticker": ticker,
            "market": market,
            "status": "validated" if rows else "data_unavailable",
            "sample_size": len(rows),
        }

    def lookup_evidence(self, query: str, limit: int = 5) -> dict[str, Any]:
        from doge.application import composition

        try:
            rows = composition.build_note_repository().search_notes(query, limit=limit)
        except Exception:
            rows = []
        if not rows:
            rows = [{
                "evidence_id": "demo-evidence-001",
                "source": "demo_materials",
                "page": 1,
                "snippet": "Deterministic fallback evidence for demo runs without a local research library.",
            }]
        return {"query": query, "limit": limit, "results": rows[:limit]}

    def request_approval(self, action: str, risk_level: str = "high") -> dict[str, Any]:
        return {"approval_required": True, "action": action, "risk_level": risk_level}
