"""Shared application service for MCP and agent tool execution."""

from __future__ import annotations

import json
import re
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
        rows = self._stock_service().query(ticker, market, days)
        return {"ticker": ticker, "market": market, "days": days, "rows": rows}

    def stock_overview(self, ticker: str, market: str = "us") -> dict[str, Any]:
        data = self._stock_service().overview(ticker, market)
        return data or {"ticker": ticker, "market": market, "status": "unavailable"}

    def rsrs_ranking(self, market: str = "us", top: int = 20) -> dict[str, Any]:
        from doge.application import composition

        rows = composition.build_ranking_service().rsrs(market, top)
        return {"market": market, "top": top, "rows": rows}

    def market_breadth(self, market: str = "us", days: int = 10) -> dict[str, Any]:
        from doge.application import composition

        rows = composition.build_breadth_service().breadth(market, days)
        return {"market": market, "days": days, "rows": rows}

    def volume_anomalies(self, min_ratio: float = 3.0, top: int = 20) -> dict[str, Any]:
        from doge.application import composition

        rows = composition.build_anomaly_service().anomalies(min_ratio, top)
        return {"min_ratio": min_ratio, "top": top, "rows": rows}

    def list_views(self) -> dict[str, Any]:
        from doge.application import composition

        payload = composition.build_view_service().list_views()
        rows = json.loads(payload)
        return {"views": rows}

    def get_portfolio_exposure(self, portfolio_id: str = "portfolio-demo") -> dict[str, Any]:
        raise NotImplementedError(f"portfolio exposure is not configured for {portfolio_id}")

    def validate_financial_claims(self, claim: str, ticker: str = "AAPL", market: str = "us") -> dict[str, Any]:
        rows = self._stock_service().query(ticker, market, 5)
        status = "data_unavailable"
        if rows:
            status = "validated" if _claim_matches_rows(claim, rows) else "unverified"
        return {
            "claim": claim,
            "ticker": ticker,
            "market": market,
            "status": status,
            "sample_size": len(rows),
        }

    def lookup_evidence(self, query: str, limit: int = 5) -> dict[str, Any]:
        from doge.application import composition

        rows = composition.build_note_repository().search_notes(query, limit=limit)
        return {"query": query, "limit": limit, "results": rows[:limit]}

    def request_approval(self, action: str, risk_level: str = "high") -> dict[str, Any]:
        return {"approval_required": True, "action": action, "risk_level": risk_level}


def _claim_matches_rows(claim: str, rows: list[dict[str, Any]]) -> bool:
    numbers = [float(item) for item in re.findall(r"\d+(?:\.\d+)?", claim)]
    if not numbers:
        return False
    numeric_values: list[float] = []
    for row in rows:
        for value in row.values():
            if isinstance(value, (int, float)):
                numeric_values.append(float(value))
    return any(
        abs(claimed - actual) <= max(0.01, abs(actual) * 0.001)
        for claimed in numbers
        for actual in numeric_values
    )
