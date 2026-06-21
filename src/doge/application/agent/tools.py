"""Tool registry for research-agent workflows."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Callable

from doge.application.agent.tool_service import ToolApplicationService


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

    async def execute_async(
        self,
        name: str,
        arguments: str | dict[str, Any] | None = None,
        *,
        timeout_seconds: float | None = None,
    ) -> ToolResult:
        """Execute a synchronous tool through a cancellable async boundary."""
        call = asyncio.to_thread(self.execute, name, arguments)
        if timeout_seconds is None:
            return await call
        try:
            return await asyncio.wait_for(call, timeout=timeout_seconds)
        except TimeoutError:
            return ToolResult(name=name, data={}, ok=False, error="tool execution timed out")


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
    service = ToolApplicationService()

    def query_stock(ticker: str, market: str = "us", days: int = 20) -> ToolResult:
        return ToolResult("query_stock", data=service.query_stock(ticker, market, days))

    def stock_overview(ticker: str, market: str = "us") -> ToolResult:
        return ToolResult("stock_overview", data=service.stock_overview(ticker, market))

    def rsrs_ranking(market: str = "us", top: int = 20) -> ToolResult:
        return ToolResult("rsrs_ranking", data=service.rsrs_ranking(market, top))

    def market_breadth(market: str = "us", days: int = 10) -> ToolResult:
        return ToolResult("market_breadth", data=service.market_breadth(market, days))

    def volume_anomalies(min_ratio: float = 3.0, top: int = 20) -> ToolResult:
        return ToolResult("volume_anomalies", data=service.volume_anomalies(min_ratio, top))

    def list_views() -> ToolResult:
        return ToolResult("list_views", data=service.list_views())

    def get_portfolio_exposure(portfolio_id: str = "portfolio-demo") -> ToolResult:
        return ToolResult("get_portfolio_exposure", data=service.get_portfolio_exposure(portfolio_id))

    def portfolio_risk(portfolio_id: str = "portfolio-demo") -> ToolResult:
        return ToolResult("portfolio_risk", data=service.portfolio_risk(portfolio_id))

    def scenario_analysis(portfolio_id: str = "portfolio-demo", basis_points: float = 100.0) -> ToolResult:
        return ToolResult("scenario_analysis", data=service.scenario_analysis(portfolio_id, basis_points))

    def validate_financial_claims(claim: str, ticker: str = "AAPL", market: str = "us") -> ToolResult:
        return ToolResult("validate_financial_claims", data=service.validate_financial_claims(claim, ticker, market))

    def generate_industry_report(
        industry: str = "semiconductor",
        market: str = "us",
        tickers: list[str] | None = None,
    ) -> ToolResult:
        return ToolResult(
            "generate_industry_report",
            data=service.generate_industry_report(industry, market, tickers),
        )

    def lookup_evidence(query: str, limit: int = 5) -> ToolResult:
        return ToolResult("lookup_evidence", data=service.lookup_evidence(query, limit))

    def request_approval(action: str, risk_level: str = "high") -> ToolResult:
        return ToolResult("request_approval", data=service.request_approval(action, risk_level))

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
    registry.register(_schema("portfolio_risk", "Get deterministic portfolio risk approximations.", {
        "portfolio_id": {"type": "string"},
    }), portfolio_risk)
    registry.register(_schema("scenario_analysis", "Run deterministic portfolio scenario analysis.", {
        "portfolio_id": {"type": "string"},
        "basis_points": {"type": "number"},
    }), scenario_analysis)
    registry.register(_schema("validate_financial_claims", "Validate a material financial claim.", {
        "claim": {"type": "string"},
        "ticker": {"type": "string"},
        "market": {"type": "string", "enum": ["cn", "us"]},
    }, ["claim", "ticker"]), validate_financial_claims)
    registry.register(_schema("generate_industry_report", "Generate an evidence-aware industry report.", {
        "industry": {"type": "string"},
        "market": {"type": "string", "enum": ["cn", "us"]},
        "tickers": {
            "type": "array",
            "items": {"type": "string"},
        },
    }), generate_industry_report)
    registry.register(_schema("lookup_evidence", "Look up source evidence snippets.", {
        "query": {"type": "string"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
    }, ["query"]), lookup_evidence)
    registry.register(_schema("request_approval", "Request human approval for a high-risk action.", {
        "action": {"type": "string"},
        "risk_level": {"type": "string", "enum": ["medium", "high"]},
    }, ["action", "risk_level"]), request_approval)
    return registry
