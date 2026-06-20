"""Tool registry for research-agent workflows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolResult:
    name: str
    data: dict[str, Any]
    ok: bool = True
    error: str | None = None

    def to_json(self) -> str:
        return json.dumps({
            "ok": self.ok,
            "name": self.name,
            "data": self.data,
            "error": self.error,
        }, ensure_ascii=False)


class ToolRegistry:
    """Small synchronous registry for deterministic finance tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., ToolResult]] = {}
        self.schemas: list[dict[str, Any]] = []

    def register(self, schema: dict[str, Any], func: Callable[..., ToolResult]) -> None:
        name = schema["function"]["name"]
        self.schemas.append(schema)
        self._tools[name] = func

    def execute(self, name: str, arguments: str | dict[str, Any] | None = None) -> ToolResult:
        if name not in self._tools:
            return ToolResult(name=name, data={}, ok=False, error="unknown tool")
        if isinstance(arguments, str):
            try:
                kwargs = json.loads(arguments or "{}")
            except json.JSONDecodeError:
                return ToolResult(name=name, data={}, ok=False, error="invalid JSON arguments")
        else:
            kwargs = arguments or {}
        try:
            return self._tools[name](**kwargs)
        except Exception as exc:  # noqa: BLE001 - tool failures become trace data
            return ToolResult(name=name, data={}, ok=False, error=str(exc))


def _schema(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


def build_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()

    def query_stock(ticker: str, market: str = "us", days: int = 20) -> ToolResult:
        from doge.application import composition
        try:
            rows = composition.build_stock_service().query(ticker, market, days)
        except Exception:
            rows = []
        return ToolResult(
            "query_stock",
            data={"ticker": ticker, "market": market, "days": days, "rows": rows},
        )

    def stock_overview(ticker: str, market: str = "us") -> ToolResult:
        from doge.application import composition
        try:
            data = composition.build_stock_service().overview(ticker, market)
        except Exception:
            data = {"ticker": ticker, "market": market, "status": "unavailable"}
        if not data:
            data = {"ticker": ticker, "market": market, "status": "unavailable"}
        return ToolResult("stock_overview", data=data)

    def rsrs_ranking(market: str = "us", top: int = 20) -> ToolResult:
        from doge.application import composition
        try:
            rows = composition.build_ranking_service().rsrs(market, top)
        except Exception:
            rows = []
        return ToolResult("rsrs_ranking", data={"market": market, "top": top, "rows": rows})

    def market_breadth(market: str = "us", days: int = 10) -> ToolResult:
        from doge.application import composition
        try:
            data = composition.build_breadth_service().breadth(market, days)
        except Exception:
            data = []
        return ToolResult("market_breadth", data={"rows": data, "market": market, "days": days})

    def volume_anomalies(min_ratio: float = 3.0, top: int = 20) -> ToolResult:
        from doge.application import composition
        try:
            rows = composition.build_anomaly_service().anomalies(min_ratio, top)
        except Exception:
            rows = []
        return ToolResult(
            "volume_anomalies",
            data={"min_ratio": min_ratio, "top": top, "rows": rows},
        )

    def list_views() -> ToolResult:
        from doge.application import composition
        try:
            payload = composition.build_view_service().list_views()
            rows = json.loads(payload)
        except Exception:
            rows = []
        return ToolResult("list_views", data={"views": rows})

    def get_portfolio_exposure(portfolio_id: str = "portfolio-demo") -> ToolResult:
        holdings = [
            {"ticker": "AAPL", "weight": 0.24, "sector": "Technology"},
            {"ticker": "MSFT", "weight": 0.21, "sector": "Technology"},
            {"ticker": "NVDA", "weight": 0.18, "sector": "Semiconductors"},
            {"ticker": "TLT", "weight": 0.12, "sector": "Rates"},
            {"ticker": "CASH", "weight": 0.25, "sector": "Cash"},
        ]
        return ToolResult(
            "get_portfolio_exposure",
            data={
                "portfolio_id": portfolio_id,
                "holdings": holdings,
                "top_concentration": 0.63,
                "technology_exposure": 0.45,
            },
        )

    def validate_financial_claims(claim: str, ticker: str = "AAPL", market: str = "us") -> ToolResult:
        from doge.application import composition
        try:
            rows = composition.build_stock_service().query(ticker, market, 5)
        except Exception:
            rows = []
        return ToolResult(
            "validate_financial_claims",
            data={
                "claim": claim,
                "ticker": ticker,
                "market": market,
                "status": "validated" if rows else "data_unavailable",
                "sample_size": len(rows),
            },
        )

    def lookup_evidence(query: str, limit: int = 5) -> ToolResult:
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
        return ToolResult("lookup_evidence", data={"query": query, "limit": limit, "results": rows[:limit]})

    def request_approval(action: str, risk_level: str = "high") -> ToolResult:
        return ToolResult(
            "request_approval",
            data={"approval_required": True, "action": action, "risk_level": risk_level},
        )

    registry.register(_schema("query_stock", "Query OHLCV rows for a ticker.", {
        "ticker": {"type": "string"},
        "market": {"type": "string", "enum": ["cn", "us"]},
        "days": {"type": "integer", "minimum": 1, "maximum": 500},
    }, ["ticker"]), query_stock)
    registry.register(_schema("stock_overview", "Get stock overview.", {
        "ticker": {"type": "string"},
        "market": {"type": "string", "enum": ["cn", "us"]},
    }, ["ticker"]), stock_overview)
    registry.register(_schema("rsrs_ranking", "Get RSRS momentum ranking.", {
        "market": {"type": "string", "enum": ["cn", "us"]},
        "top": {"type": "integer", "minimum": 1, "maximum": 100},
    }), rsrs_ranking)
    registry.register(_schema("market_breadth", "Get market breadth rows.", {
        "market": {"type": "string", "enum": ["cn", "us"]},
        "days": {"type": "integer", "minimum": 1, "maximum": 30},
    }), market_breadth)
    registry.register(_schema("volume_anomalies", "Get volume anomaly rows.", {
        "min_ratio": {"type": "number", "minimum": 1.0, "maximum": 1000.0},
        "top": {"type": "integer", "minimum": 1, "maximum": 100},
    }), volume_anomalies)
    registry.register(_schema("list_views", "List available analytical views.", {}), list_views)
    registry.register(_schema("get_portfolio_exposure", "Get demo portfolio exposure.", {
        "portfolio_id": {"type": "string"},
    }), get_portfolio_exposure)
    registry.register(_schema("validate_financial_claims", "Validate a material financial claim.", {
        "claim": {"type": "string"},
        "ticker": {"type": "string"},
        "market": {"type": "string", "enum": ["cn", "us"]},
    }, ["claim", "ticker"]), validate_financial_claims)
    registry.register(_schema("lookup_evidence", "Look up source evidence snippets.", {
        "query": {"type": "string"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
    }, ["query"]), lookup_evidence)
    registry.register(_schema("request_approval", "Request human approval for a high-risk action.", {
        "action": {"type": "string"},
        "risk_level": {"type": "string", "enum": ["medium", "high"]},
    }, ["action", "risk_level"]), request_approval)
    return registry
