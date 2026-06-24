"""Tool registry for research-agent workflows."""

from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable

from doge.application.agent.tool_service import ToolApplicationService
from doge.core.domain.tool_descriptor import ToolDescriptor
from doge.core.domain.tool_policy import ToolCategory
from doge.core.ports.tool_entitlement import IToolEntitlementChecker


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

    def __init__(
        self,
        *,
        entitlement_checker: IToolEntitlementChecker | None = None,
        context: Any = None,
    ) -> None:
        self._descriptors: dict[str, ToolDescriptor] = {}
        self._tools: dict[str, Callable[..., ToolResult]] = {}
        self._categories: dict[str, ToolCategory] = {}
        self._entitlement = entitlement_checker or _DefaultEntitlementChecker()
        self._context = context
        self.schemas: list[dict[str, Any]] = []

    def register(
        self,
        schema: dict[str, Any] | ToolDescriptor,
        func: Callable[..., ToolResult],
        category: ToolCategory | str | None = None,
    ) -> None:
        descriptor = schema if isinstance(schema, ToolDescriptor) else None
        if descriptor is not None:
            schema = descriptor.to_schema()
        name = schema["function"]["name"]
        resolved_category = _category(category or schema.get("x-doge-category") or ToolCategory.READ_ONLY)
        schema["x-doge-category"] = resolved_category.value
        if descriptor is None:
            descriptor = ToolDescriptor.from_schema(schema, category=resolved_category)
        self._descriptors[name] = descriptor
        self.schemas.append(schema)
        self._tools[name] = func
        self._categories[name] = resolved_category

    def descriptor_for(self, name: str) -> ToolDescriptor | None:
        """Return the canonical descriptor for a registered tool."""

        return self._descriptors.get(name)

    def descriptors(self) -> tuple[ToolDescriptor, ...]:
        """Return registered descriptors in schema order."""

        names = [schema.get("function", {}).get("name", "") for schema in self.schemas]
        return tuple(self._descriptors[name] for name in names if name in self._descriptors)

    def schemas_for_context(self, context: Any = None) -> list[dict[str, Any]]:
        effective_context = self._context if context is None else context
        allowed: list[dict[str, Any]] = []
        for schema in self.schemas:
            name = schema.get("function", {}).get("name", "")
            category = self._categories.get(name, ToolCategory.READ_ONLY)
            redacted = self._entitlement.redact_schema(effective_context, schema, category)
            if redacted is not None:
                allowed.append(redacted)
        return allowed

    def capability_records_for_context(self, context: Any = None) -> list[dict[str, Any]]:
        effective_context = self._context if context is None else context
        records: list[dict[str, Any]] = []
        for schema in self.schemas_for_context(effective_context):
            name = schema.get("function", {}).get("name", "")
            category = self._categories.get(name, ToolCategory.READ_ONLY)
            descriptor = self._descriptors.get(name)
            records.append({
                "tool_name": name,
                "description": (
                    descriptor.description if descriptor is not None
                    else schema.get("function", {}).get("description", "")
                ),
                "category": category.value,
                "risk_level": _risk_level(category),
                "status": descriptor.status if descriptor is not None else schema.get("x-doge-status", "available"),
                "requires_approval": self._entitlement.requires_approval(effective_context, name, category),
                "metadata": (
                    descriptor.capability_metadata()
                    if descriptor is not None
                    else dict(schema.get("x-doge-metadata", {}))
                ),
            })
        return records

    def execute(self, name: str, arguments: str | dict[str, Any] | None = None, *, context: Any = None) -> ToolResult:
        if name not in self._tools:
            return ToolResult(name=name, data={}, ok=False, error="unknown tool")
        effective_context = self._context if context is None else context
        category = self._categories.get(name, ToolCategory.READ_ONLY)
        if not self._entitlement.can_execute(effective_context, name, category):
            return ToolResult(name=name, data={}, ok=False, error="tool not permitted")
        if isinstance(arguments, str):
            try:
                kwargs = json.loads(arguments or "{}")
            except json.JSONDecodeError:
                return ToolResult(name=name, data={}, ok=False, error="invalid JSON arguments")
        else:
            kwargs = arguments or {}
        try:
            result = _invoke_tool(self._tools[name], kwargs, effective_context)
            if self._entitlement.requires_approval(effective_context, name, category):
                result.data.setdefault("approval_required", True)
                result.data.setdefault("action", name)
                result.data.setdefault("risk_level", "high")
            return result
        except Exception as exc:  # noqa: BLE001 - tool failures become trace data
            return ToolResult(name=name, data={}, ok=False, error=str(exc))

    async def execute_async(
        self,
        name: str,
        arguments: str | dict[str, Any] | None = None,
        *,
        timeout_seconds: float | None = None,
        context: Any = None,
    ) -> ToolResult:
        """Execute a synchronous tool through a cancellable async boundary."""
        call = asyncio.to_thread(self.execute, name, arguments, context=context)
        if timeout_seconds is None:
            return await call
        try:
            return await asyncio.wait_for(call, timeout=timeout_seconds)
        except TimeoutError:
            return ToolResult(name=name, data={}, ok=False, error="tool execution timed out")


def _schema(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str] | None = None,
    *,
    category: ToolCategory = ToolCategory.READ_ONLY,
    status: str = "available",
    metadata: dict[str, Any] | None = None,
) -> ToolDescriptor:
    return ToolDescriptor(
        name=name,
        description=description,
        properties=properties,
        required=tuple(required or ()),
        category=category,
        status=status,
        metadata=metadata or {},
    )


def build_default_tool_registry(
    service: ToolApplicationService | None = None,
    *,
    entitlement_checker: IToolEntitlementChecker | None = None,
    context: Any = None,
) -> ToolRegistry:
    registry = ToolRegistry(entitlement_checker=entitlement_checker, context=context)
    service = service or ToolApplicationService()

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

    def validate_financial_claims(
        claim: str,
        ticker: str = "AAPL",
        market: str = "us",
        context: Any = None,
    ) -> ToolResult:
        return ToolResult(
            "validate_financial_claims",
            data=service.validate_financial_claims(claim, ticker, market, context=context),
        )

    def generate_industry_report(
        industry: str = "semiconductor",
        market: str = "us",
        tickers: list[str] | None = None,
    ) -> ToolResult:
        return ToolResult(
            "generate_industry_report",
            data=service.generate_industry_report(industry, market, tickers),
        )

    def lookup_evidence(query: str, limit: int = 5, context: Any = None) -> ToolResult:
        return ToolResult("lookup_evidence", data=service.lookup_evidence(query, limit, context=context))

    def request_approval(action: str, risk_level: str = "high") -> ToolResult:
        return ToolResult("request_approval", data=service.request_approval(action, risk_level))

    def get_financial_statements(ticker: str, statement_type: str = "income", period: str = "annual") -> ToolResult:
        return ToolResult(
            "get_financial_statements",
            data=service.get_financial_statements(ticker, statement_type, period),
        )

    def get_company_announcements(ticker: str, limit: int = 5) -> ToolResult:
        return ToolResult("get_company_announcements", data=service.get_company_announcements(ticker, limit))

    def calculate_financial_ratios(fields: dict[str, Any] | None = None) -> ToolResult:
        return ToolResult("calculate_financial_ratios", data=service.calculate_financial_ratios(fields))

    def compare_consensus_estimates(ticker: str, metric: str = "eps") -> ToolResult:
        return ToolResult("compare_consensus_estimates", data=service.compare_consensus_estimates(ticker, metric))

    def get_industry_classification(ticker: str, market: str = "us") -> ToolResult:
        return ToolResult("get_industry_classification", data=service.get_industry_classification(ticker, market))

    def run_sql_query(sql: str, readonly: bool = True) -> ToolResult:
        data = service.run_sql_query(sql, readonly)
        return ToolResult("run_sql_query", data=data, ok=bool(data.get("ok", True)), error=data.get("error"))

    def run_python_analysis(code: str, timeout: float = 5.0) -> ToolResult:
        data = service.run_python_analysis(code, timeout)
        return ToolResult("run_python_analysis", data=data, ok=bool(data.get("ok", True)), error=data.get("error"))

    def screen_compliance_risk(text: str) -> ToolResult:
        return ToolResult("screen_compliance_risk", data=service.screen_compliance_risk(text))

    def publish_investment_memo(memo_id: str, distribution_list: list[str] | None = None) -> ToolResult:
        return ToolResult(
            "publish_investment_memo",
            data=service.publish_investment_memo(memo_id, distribution_list),
        )

    def propose_portfolio_rebalance(
        portfolio_id: str,
        proposed_changes: list[dict[str, Any]] | None = None,
    ) -> ToolResult:
        return ToolResult(
            "propose_portfolio_rebalance",
            data=service.propose_portfolio_rebalance(portfolio_id, proposed_changes),
        )

    registry.register(_schema("query_stock", "Query OHLCV rows for a ticker.", {
        "ticker": {"type": "string"},
        "market": {"type": "string", "enum": ["cn", "us"]},
        "days": {"type": "integer", "minimum": 1, "maximum": 500},
    }, ["ticker"], category=ToolCategory.READ_ONLY), query_stock)
    registry.register(_schema("stock_overview", "Get stock overview.", {
        "ticker": {"type": "string"},
        "market": {"type": "string", "enum": ["cn", "us"]},
    }, ["ticker"], category=ToolCategory.READ_ONLY), stock_overview)
    registry.register(_schema("rsrs_ranking", "Get RSRS momentum ranking.", {
        "market": {"type": "string", "enum": ["cn", "us"]},
        "top": {"type": "integer", "minimum": 1, "maximum": 100},
    }, category=ToolCategory.READ_ONLY), rsrs_ranking)
    registry.register(_schema("market_breadth", "Get market breadth rows.", {
        "market": {"type": "string", "enum": ["cn", "us"]},
        "days": {"type": "integer", "minimum": 1, "maximum": 30},
    }, category=ToolCategory.READ_ONLY), market_breadth)
    registry.register(_schema("volume_anomalies", "Get volume anomaly rows.", {
        "min_ratio": {"type": "number", "minimum": 1.0, "maximum": 1000.0},
        "top": {"type": "integer", "minimum": 1, "maximum": 100},
    }, category=ToolCategory.READ_ONLY), volume_anomalies)
    registry.register(_schema("list_views", "List available analytical views.", {}, category=ToolCategory.READ_ONLY), list_views)
    registry.register(_schema("get_portfolio_exposure", "Get demo portfolio exposure.", {
        "portfolio_id": {"type": "string"},
    }, category=ToolCategory.READ_ONLY), get_portfolio_exposure)
    registry.register(_schema("portfolio_risk", "Get deterministic portfolio risk approximations.", {
        "portfolio_id": {"type": "string"},
    }, category=ToolCategory.ANALYTICAL), portfolio_risk)
    registry.register(_schema("scenario_analysis", "Run deterministic portfolio scenario analysis.", {
        "portfolio_id": {"type": "string"},
        "basis_points": {"type": "number"},
    }, category=ToolCategory.ANALYTICAL), scenario_analysis)
    registry.register(_schema("validate_financial_claims", "Validate a material financial claim.", {
        "claim": {"type": "string"},
        "ticker": {"type": "string"},
        "market": {"type": "string", "enum": ["cn", "us"]},
    }, ["claim", "ticker"], category=ToolCategory.ANALYTICAL), validate_financial_claims)
    registry.register(_schema("generate_industry_report", "Generate an evidence-aware industry report.", {
        "industry": {"type": "string"},
        "market": {"type": "string", "enum": ["cn", "us"]},
        "tickers": {
            "type": "array",
            "items": {"type": "string"},
        },
    }, category=ToolCategory.GENERATIVE), generate_industry_report)
    registry.register(_schema("lookup_evidence", "Look up source evidence snippets.", {
        "query": {"type": "string"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
    }, ["query"], category=ToolCategory.READ_ONLY), lookup_evidence)
    registry.register(_schema("request_approval", "Request human approval for a high-risk action.", {
        "action": {"type": "string"},
        "risk_level": {"type": "string", "enum": ["medium", "high"]},
    }, ["action", "risk_level"], category=ToolCategory.HIGH_RISK), request_approval)
    registry.register(_schema("get_financial_statements", "Get demo financial statement fields.", {
        "ticker": {"type": "string"},
        "statement_type": {"type": "string", "enum": ["income", "balance", "cashflow"]},
        "period": {"type": "string", "enum": ["annual", "quarterly"]},
    }, ["ticker"], category=ToolCategory.READ_ONLY), get_financial_statements)
    registry.register(_schema("get_company_announcements", "Search local company announcements/notes.", {
        "ticker": {"type": "string"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
    }, ["ticker"], category=ToolCategory.READ_ONLY), get_company_announcements)
    registry.register(_schema("calculate_financial_ratios", "Calculate deterministic ratios from supplied fields.", {
        "fields": {"type": "object"},
    }, category=ToolCategory.ANALYTICAL), calculate_financial_ratios)
    registry.register(_schema("compare_consensus_estimates", "Compare demo consensus estimates.", {
        "ticker": {"type": "string"},
        "metric": {"type": "string"},
    }, ["ticker"], category=ToolCategory.READ_ONLY), compare_consensus_estimates)
    registry.register(_schema("get_industry_classification", "Resolve local industry classification metadata.", {
        "ticker": {"type": "string"},
        "market": {"type": "string", "enum": ["cn", "us"]},
    }, ["ticker"], category=ToolCategory.READ_ONLY), get_industry_classification)
    registry.register(_schema("run_sql_query", "Run a read-only SQL query against analytical views.", {
        "sql": {"type": "string"},
        "readonly": {"type": "boolean"},
    }, ["sql"], category=ToolCategory.ANALYTICAL), run_sql_query)
    python_analysis_status = service.python_analysis_capability_status()
    registry.register(_schema("run_python_analysis", "Run bounded demo Python analysis.", {
        "code": {"type": "string"},
        "timeout": {"type": "number", "minimum": 1, "maximum": 10},
    }, ["code"], category=ToolCategory.HIGH_RISK, **python_analysis_status), run_python_analysis)
    registry.register(_schema("screen_compliance_risk", "Screen text for compliance risk phrases.", {
        "text": {"type": "string"},
    }, ["text"], category=ToolCategory.ANALYTICAL), screen_compliance_risk)
    registry.register(_schema("publish_investment_memo", "Request approval to publish an investment memo.", {
        "memo_id": {"type": "string"},
        "distribution_list": {"type": "array", "items": {"type": "string"}},
    }, ["memo_id"], category=ToolCategory.HIGH_RISK), publish_investment_memo)
    registry.register(_schema("propose_portfolio_rebalance", "Request approval for a proposed rebalance.", {
        "portfolio_id": {"type": "string"},
        "proposed_changes": {"type": "array", "items": {"type": "object"}},
    }, ["portfolio_id"], category=ToolCategory.HIGH_RISK), propose_portfolio_rebalance)
    return registry


def _category(value: ToolCategory | str) -> ToolCategory:
    if isinstance(value, ToolCategory):
        return value
    return ToolCategory(str(value))


def _risk_level(category: ToolCategory) -> str:
    if category == ToolCategory.HIGH_RISK:
        return "high"
    if category in {ToolCategory.ANALYTICAL, ToolCategory.GENERATIVE}:
        return "medium"
    return "low"


def _invoke_tool(func: Callable[..., ToolResult], kwargs: dict[str, Any], context: Any) -> ToolResult:
    if "context" in inspect.signature(func).parameters and "context" not in kwargs:
        return func(**kwargs, context=context)
    return func(**kwargs)


class _DefaultEntitlementChecker:
    def can_execute(self, context: Any, tool_name: str, category: ToolCategory) -> bool:
        return category != ToolCategory.FORBIDDEN

    def requires_approval(self, context: Any, tool_name: str, category: ToolCategory) -> bool:
        return category == ToolCategory.HIGH_RISK

    def redact_schema(self, context: Any, schema: dict[str, Any], category: ToolCategory) -> dict[str, Any] | None:
        if not self.can_execute(context, schema.get("function", {}).get("name", ""), category):
            return None
        return schema
