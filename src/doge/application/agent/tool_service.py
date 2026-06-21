"""Shared application service for MCP and agent tool execution."""

from __future__ import annotations

import json
import re
import subprocess
import sys
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

    def get_financial_statements(
        self,
        ticker: str,
        statement_type: str = "income",
        period: str = "annual",
    ) -> dict[str, Any]:
        overview = self.stock_overview(ticker, "us")
        return {
            "ticker": ticker,
            "statement_type": statement_type,
            "period": period,
            "status": "demo_unavailable" if overview.get("status") == "unavailable" else "demo",
            "fields": {
                key: value
                for key, value in overview.items()
                if isinstance(value, (int, float, str)) and key not in {"ticker", "market"}
            },
        }

    def get_company_announcements(self, ticker: str, limit: int = 5) -> dict[str, Any]:
        from doge.application import composition

        try:
            rows = composition.build_note_repository().search_notes(ticker, limit=limit)
        except Exception:
            rows = []
        return {"ticker": ticker, "limit": limit, "announcements": rows[:limit], "source": "local_notes"}

    def calculate_financial_ratios(self, fields: dict[str, Any] | None = None) -> dict[str, Any]:
        values = fields or {}
        revenue = _num(values.get("revenue"))
        net_income = _num(values.get("net_income"))
        assets = _num(values.get("assets"))
        equity = _num(values.get("equity"))
        ratios: dict[str, float] = {}
        if revenue:
            ratios["net_margin"] = net_income / revenue
        if assets:
            ratios["roa"] = net_income / assets
        if equity:
            ratios["roe"] = net_income / equity
        return {"ratios": ratios, "status": "calculated" if ratios else "insufficient_fields"}

    def compare_consensus_estimates(self, ticker: str, metric: str = "eps") -> dict[str, Any]:
        return {
            "ticker": ticker,
            "metric": metric,
            "status": "demo_unavailable",
            "message": "Consensus connector is not configured in this local reference implementation.",
        }

    def run_sql_query(self, sql: str, readonly: bool = True) -> dict[str, Any]:
        if not readonly or _looks_mutating_sql(sql):
            return {"ok": False, "error": "Only read-only SELECT/WITH queries are allowed."}
        try:
            from doge.application import composition

            frame = composition.build_view_repository(read_only=True).execute(sql, [])
            rows = frame.to_dict(orient="records") if hasattr(frame, "to_dict") else []
            return {"ok": True, "rows": rows[:100], "row_count": len(rows)}
        except Exception:
            return {"ok": False, "error": "SQL query failed."}

    def run_python_analysis(self, code: str, timeout: float = 5.0) -> dict[str, Any]:
        if _unsafe_python(code):
            return {"ok": False, "error": "Code uses disallowed operations in the demo sandbox."}
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-c", code],
                text=True,
                capture_output=True,
                timeout=max(1.0, min(float(timeout), 10.0)),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Python analysis timed out."}
        return {
            "ok": completed.returncode == 0,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-2000:] if completed.returncode else "",
            "returncode": completed.returncode,
        }

    def screen_compliance_risk(self, text: str) -> dict[str, Any]:
        lowered = text.lower()
        hits = [
            word
            for word in ("guaranteed return", "inside information", "auto trade", "无风险", "内幕")
            if word in lowered
        ]
        return {"risk": "high" if hits else "low", "matches": hits}

    def publish_investment_memo(self, memo_id: str, distribution_list: list[str] | None = None) -> dict[str, Any]:
        return {
            "approval_required": True,
            "action": f"publish investment memo {memo_id}",
            "risk_level": "high",
            "distribution_list": distribution_list or [],
        }

    def propose_portfolio_rebalance(
        self,
        portfolio_id: str,
        proposed_changes: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "approval_required": True,
            "action": f"propose rebalance for portfolio {portfolio_id}",
            "risk_level": "high",
            "portfolio_id": portfolio_id,
            "proposed_changes": proposed_changes or [],
        }


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


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _looks_mutating_sql(sql: str) -> bool:
    stripped = sql.strip().lower()
    if not (stripped.startswith("select") or stripped.startswith("with")):
        return True
    return bool(re.search(r"\b(insert|update|delete|drop|alter|create|attach|copy|pragma)\b", stripped))


def _unsafe_python(code: str) -> bool:
    lowered = code.lower()
    blocked = (
        "import os",
        "import subprocess",
        "import socket",
        "from os",
        "from subprocess",
        "open(",
        "__",
        "eval(",
        "exec(",
    )
    return any(token in lowered for token in blocked)
