"""Shared application service for MCP and agent tool execution."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
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
        from doge.application import composition

        return composition.build_portfolio_service().get_exposure(portfolio_id)

    def portfolio_risk(self, portfolio_id: str = "portfolio-demo") -> dict[str, Any]:
        from doge.application import composition

        return composition.build_risk_service().portfolio_risk(portfolio_id)

    def scenario_analysis(self, portfolio_id: str = "portfolio-demo", basis_points: float = 100.0) -> dict[str, Any]:
        from doge.application import composition

        return composition.build_scenario_service().rate_shock(portfolio_id, basis_points)

    def validate_financial_claims(self, claim: str, ticker: str = "AAPL", market: str = "us") -> dict[str, Any]:
        evidence = []
        try:
            from doge.application import composition

            evidence = composition.build_rag_service().search(claim, limit=3).get("results", [])
        except Exception:
            evidence = []
        rows = self._stock_service().query(ticker, market, 5)
        status = "data_unavailable"
        if evidence:
            status = "supported" if _claim_matches_evidence(claim, evidence) else "insufficient_evidence"
        elif rows:
            status = "supported" if _claim_matches_rows(claim, rows) else "contradicted"
        return {
            "claim": claim,
            "ticker": ticker,
            "market": market,
            "status": status,
            "sample_size": len(rows),
            "evidence": evidence,
        }

    def generate_industry_report(
        self,
        industry: str = "semiconductor",
        market: str = "us",
        tickers: list[str] | None = None,
    ) -> dict[str, Any]:
        from doge.application import composition
        from doge.application.contracts.request import GenerateIndustryReportRequest

        response = composition.build_generate_industry_report_use_case().execute(
            GenerateIndustryReportRequest(
                market=market,
                industry=industry,
                tickers=tickers,
            )
        )
        return asdict(response) if is_dataclass(response) else dict(response)

    def lookup_evidence(self, query: str, limit: int = 5) -> dict[str, Any]:
        from doge.application import composition

        try:
            rag_result = composition.build_rag_service().search(query, limit=limit)
            if rag_result.get("results"):
                return rag_result
        except Exception:
            pass
        rows = composition.build_note_repository().search_notes(query, limit=limit)
        return {"query": query, "limit": limit, "source": "notes", "results": rows[:limit]}

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


def _claim_matches_evidence(claim: str, evidence: list[dict[str, Any]]) -> bool:
    numbers = re.findall(r"\d+(?:\.\d+)?", claim)
    texts = " ".join(str(item.get("text", "")) for item in evidence).lower()
    if numbers:
        return any(number in texts for number in numbers)
    claim_terms = {term for term in re.findall(r"[\w\u4e00-\u9fff]+", claim.lower()) if len(term) > 3}
    if not claim_terms:
        return False
    evidence_terms = set(re.findall(r"[\w\u4e00-\u9fff]+", texts))
    return bool(claim_terms & evidence_terms)
