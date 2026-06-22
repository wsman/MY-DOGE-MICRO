"""Shared application service for MCP and agent tool execution."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from typing import Any

from doge.application.capabilities.compliance_provider import ComplianceToolProvider
from doge.application.capabilities.fundamental_provider import FundamentalToolProvider
from doge.application.capabilities.market_provider import MarketToolProvider
from doge.application.capabilities.portfolio_provider import PortfolioToolProvider
from doge.application.capabilities.publishing_provider import PublishingToolProvider
from doge.application.capabilities.quant_provider import QuantToolProvider
from doge.application.capabilities.registry import ToolExecutionProviderRegistry
from doge.application.capabilities.research_provider import ResearchToolProvider
from doge.application.capabilities.tool_utils import (
    ServiceFactory,
    claim_matches_evidence as _claim_matches_evidence,
    claim_matches_rows as _claim_matches_rows,
    document_scope_from_context as _document_scope_from_context,
    filter_results_for_context as _filter_results_for_context,
    is_restricted_context as _is_restricted_context,
    looks_mutating_sql as _looks_mutating_sql,
    num as _num,
    resolve as _resolve,
    unsafe_python as _unsafe_python,
)


_NO_PROVIDER = object()


class ToolApplicationService:
    """Application-layer facade for deterministic research tools."""

    def __init__(
        self,
        stock_service_factory: ServiceFactory | None = None,
        *,
        ranking_service_factory: ServiceFactory | None = None,
        breadth_service_factory: ServiceFactory | None = None,
        anomaly_service_factory: ServiceFactory | None = None,
        view_service_factory: ServiceFactory | None = None,
        portfolio_service_factory: ServiceFactory | None = None,
        risk_service_factory: ServiceFactory | None = None,
        scenario_service_factory: ServiceFactory | None = None,
        rag_service_factory: ServiceFactory | None = None,
        note_repository_factory: ServiceFactory | None = None,
        industry_report_use_case_factory: ServiceFactory | None = None,
        financial_statement_repository_factory: ServiceFactory | None = None,
        company_announcement_repository_factory: ServiceFactory | None = None,
        consensus_estimate_repository_factory: ServiceFactory | None = None,
        industry_classification_source_factory: ServiceFactory | None = None,
        view_repository_factory: ServiceFactory | None = None,
        use_capability_providers: bool = False,
        execution_provider_registry: ToolExecutionProviderRegistry | None = None,
    ) -> None:
        self._stock_service_factory = stock_service_factory
        self._ranking_service_factory = ranking_service_factory
        self._breadth_service_factory = breadth_service_factory
        self._anomaly_service_factory = anomaly_service_factory
        self._view_service_factory = view_service_factory
        self._portfolio_service_factory = portfolio_service_factory
        self._risk_service_factory = risk_service_factory
        self._scenario_service_factory = scenario_service_factory
        self._rag_service_factory = rag_service_factory
        self._note_repository_factory = note_repository_factory
        self._industry_report_use_case_factory = industry_report_use_case_factory
        self._financial_statement_repository_factory = financial_statement_repository_factory
        self._company_announcement_repository_factory = company_announcement_repository_factory
        self._consensus_estimate_repository_factory = consensus_estimate_repository_factory
        self._industry_classification_source_factory = industry_classification_source_factory
        self._view_repository_factory = view_repository_factory
        self._execution_provider_registry = execution_provider_registry
        if self._execution_provider_registry is None and use_capability_providers:
            self._execution_provider_registry = self._build_execution_provider_registry()

    def execution_provider_method_names(self) -> tuple[str, ...]:
        """Return provider-backed method names for parity tests and diagnostics."""
        if self._execution_provider_registry is None:
            return ()
        return self._execution_provider_registry.method_names()

    def _build_execution_provider_registry(self) -> ToolExecutionProviderRegistry:
        return ToolExecutionProviderRegistry([
            MarketToolProvider(
                stock_service_factory=self._stock_service_factory,
                ranking_service_factory=self._ranking_service_factory,
                breadth_service_factory=self._breadth_service_factory,
                anomaly_service_factory=self._anomaly_service_factory,
            ),
            PortfolioToolProvider(
                portfolio_service_factory=self._portfolio_service_factory,
                risk_service_factory=self._risk_service_factory,
                scenario_service_factory=self._scenario_service_factory,
            ),
            ResearchToolProvider(
                stock_service_factory=self._stock_service_factory,
                rag_service_factory=self._rag_service_factory,
                note_repository_factory=self._note_repository_factory,
                industry_report_use_case_factory=self._industry_report_use_case_factory,
            ),
            FundamentalToolProvider(
                financial_statement_repository_factory=self._financial_statement_repository_factory,
                company_announcement_repository_factory=self._company_announcement_repository_factory,
                consensus_estimate_repository_factory=self._consensus_estimate_repository_factory,
                industry_classification_source_factory=self._industry_classification_source_factory,
            ),
            QuantToolProvider(
                view_service_factory=self._view_service_factory,
                view_repository_factory=self._view_repository_factory,
            ),
            ComplianceToolProvider(),
            PublishingToolProvider(),
        ])

    def _provider_execute(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        if self._execution_provider_registry is None:
            return _NO_PROVIDER
        return self._execution_provider_registry.execute(method_name, *args, **kwargs)

    def _stock_service(self):
        return _resolve(self._stock_service_factory, "stock_service")

    def _ranking_service(self):
        return _resolve(self._ranking_service_factory, "ranking_service")

    def _breadth_service(self):
        return _resolve(self._breadth_service_factory, "breadth_service")

    def _anomaly_service(self):
        return _resolve(self._anomaly_service_factory, "anomaly_service")

    def _view_service(self):
        return _resolve(self._view_service_factory, "view_service")

    def _portfolio_service(self):
        return _resolve(self._portfolio_service_factory, "portfolio_service")

    def _risk_service(self):
        return _resolve(self._risk_service_factory, "risk_service")

    def _scenario_service(self):
        return _resolve(self._scenario_service_factory, "scenario_service")

    def _rag_service(self):
        return _resolve(self._rag_service_factory, "rag_service")

    def _note_repository(self):
        return _resolve(self._note_repository_factory, "note_repository")

    def _industry_report_use_case(self):
        return _resolve(self._industry_report_use_case_factory, "industry_report_use_case")

    def _financial_statement_repository(self):
        return _resolve(self._financial_statement_repository_factory, "financial_statement_repository")

    def _company_announcement_repository(self):
        return _resolve(self._company_announcement_repository_factory, "company_announcement_repository")

    def _consensus_estimate_repository(self):
        return _resolve(self._consensus_estimate_repository_factory, "consensus_estimate_repository")

    def _industry_classification_source(self):
        return _resolve(self._industry_classification_source_factory, "industry_classification_source")

    def _view_repository(self):
        return _resolve(self._view_repository_factory, "view_repository")

    def query_stock(self, ticker: str, market: str = "us", days: int = 20) -> dict[str, Any]:
        result = self._provider_execute("query_stock", ticker, market, days)
        if result is not _NO_PROVIDER:
            return result
        rows = self._stock_service().query(ticker, market, days)
        return {"ticker": ticker, "market": market, "days": days, "rows": rows}

    def stock_overview(self, ticker: str, market: str = "us") -> dict[str, Any]:
        result = self._provider_execute("stock_overview", ticker, market)
        if result is not _NO_PROVIDER:
            return result
        data = self._stock_service().overview(ticker, market)
        return data or {"ticker": ticker, "market": market, "status": "unavailable"}

    def rsrs_ranking(self, market: str = "us", top: int = 20) -> dict[str, Any]:
        result = self._provider_execute("rsrs_ranking", market, top)
        if result is not _NO_PROVIDER:
            return result
        rows = self._ranking_service().rsrs(market, top)
        return {"market": market, "top": top, "rows": rows}

    def market_breadth(self, market: str = "us", days: int = 10) -> dict[str, Any]:
        result = self._provider_execute("market_breadth", market, days)
        if result is not _NO_PROVIDER:
            return result
        rows = self._breadth_service().breadth(market, days)
        return {"market": market, "days": days, "rows": rows}

    def volume_anomalies(self, min_ratio: float = 3.0, top: int = 20) -> dict[str, Any]:
        result = self._provider_execute("volume_anomalies", min_ratio, top)
        if result is not _NO_PROVIDER:
            return result
        rows = self._anomaly_service().anomalies(min_ratio, top)
        return {"min_ratio": min_ratio, "top": top, "rows": rows}

    def list_views(self) -> dict[str, Any]:
        result = self._provider_execute("list_views")
        if result is not _NO_PROVIDER:
            return result
        payload = self._view_service().list_views()
        rows = json.loads(payload)
        return {"views": rows}

    def get_portfolio_exposure(self, portfolio_id: str = "portfolio-demo") -> dict[str, Any]:
        result = self._provider_execute("get_portfolio_exposure", portfolio_id)
        if result is not _NO_PROVIDER:
            return result
        return self._portfolio_service().get_exposure(portfolio_id)

    def portfolio_risk(self, portfolio_id: str = "portfolio-demo") -> dict[str, Any]:
        result = self._provider_execute("portfolio_risk", portfolio_id)
        if result is not _NO_PROVIDER:
            return result
        return self._risk_service().portfolio_risk(portfolio_id)

    def scenario_analysis(self, portfolio_id: str = "portfolio-demo", basis_points: float = 100.0) -> dict[str, Any]:
        result = self._provider_execute("scenario_analysis", portfolio_id, basis_points)
        if result is not _NO_PROVIDER:
            return result
        return self._scenario_service().rate_shock(portfolio_id, basis_points)

    def validate_financial_claims(
        self,
        claim: str,
        ticker: str = "AAPL",
        market: str = "us",
        *,
        context: Any = None,
    ) -> dict[str, Any]:
        result = self._provider_execute("validate_financial_claims", claim, ticker, market, context=context)
        if result is not _NO_PROVIDER:
            return result
        evidence = []
        try:
            document_ids = _document_scope_from_context(context)
            evidence = self._rag_service().search(claim, document_ids=document_ids, limit=3).get("results", [])
            evidence = _filter_results_for_context(evidence, context)
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
        result = self._provider_execute("generate_industry_report", industry, market, tickers)
        if result is not _NO_PROVIDER:
            return result
        from doge.application.contracts.request import GenerateIndustryReportRequest

        response = self._industry_report_use_case().execute(
            GenerateIndustryReportRequest(
                market=market,
                industry=industry,
                tickers=tickers,
            )
        )
        return asdict(response) if is_dataclass(response) else dict(response)

    def lookup_evidence(self, query: str, limit: int = 5, *, context: Any = None) -> dict[str, Any]:
        result = self._provider_execute("lookup_evidence", query, limit, context=context)
        if result is not _NO_PROVIDER:
            return result
        document_ids = _document_scope_from_context(context)
        try:
            rag_result = self._rag_service().search(query, document_ids=document_ids, limit=limit)
            rag_result["results"] = _filter_results_for_context(rag_result.get("results", []), context)
            if rag_result.get("results"):
                return rag_result
        except Exception:
            pass
        if _is_restricted_context(context):
            return {"query": query, "limit": limit, "source": "rag", "results": []}
        rows = self._note_repository().search_notes(query, limit=limit)
        return {"query": query, "limit": limit, "source": "notes", "results": rows[:limit]}

    def request_approval(self, action: str, risk_level: str = "high") -> dict[str, Any]:
        result = self._provider_execute("request_approval", action, risk_level)
        if result is not _NO_PROVIDER:
            return result
        return {"approval_required": True, "action": action, "risk_level": risk_level}

    def get_financial_statements(
        self,
        ticker: str,
        statement_type: str = "income",
        period: str = "annual",
    ) -> dict[str, Any]:
        result = self._provider_execute("get_financial_statements", ticker, statement_type, period)
        if result is not _NO_PROVIDER:
            return result
        return self._financial_statement_repository().get_statement(ticker, statement_type, period)

    def get_company_announcements(self, ticker: str, limit: int = 5) -> dict[str, Any]:
        result = self._provider_execute("get_company_announcements", ticker, limit)
        if result is not _NO_PROVIDER:
            return result
        return self._company_announcement_repository().list_announcements(ticker, limit)

    def calculate_financial_ratios(self, fields: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self._provider_execute("calculate_financial_ratios", fields)
        if result is not _NO_PROVIDER:
            return result
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
        result = self._provider_execute("compare_consensus_estimates", ticker, metric)
        if result is not _NO_PROVIDER:
            return result
        return self._consensus_estimate_repository().compare_estimates(ticker, metric)

    def get_industry_classification(self, ticker: str, market: str = "us") -> dict[str, Any]:
        result = self._provider_execute("get_industry_classification", ticker, market)
        if result is not _NO_PROVIDER:
            return result
        return self._industry_classification_source().classify(ticker, market)

    def run_sql_query(self, sql: str, readonly: bool = True) -> dict[str, Any]:
        result = self._provider_execute("run_sql_query", sql, readonly)
        if result is not _NO_PROVIDER:
            return result
        if not readonly or _looks_mutating_sql(sql):
            return {"ok": False, "error": "Only read-only SELECT/WITH queries are allowed."}
        try:
            frame = self._view_repository().execute(sql, [])
            rows = frame.to_dict(orient="records") if hasattr(frame, "to_dict") else []
            return {"ok": True, "rows": rows[:100], "row_count": len(rows)}
        except Exception:
            return {"ok": False, "error": "SQL query failed."}

    def run_python_analysis(self, code: str, timeout: float = 5.0) -> dict[str, Any]:
        result = self._provider_execute("run_python_analysis", code, timeout)
        if result is not _NO_PROVIDER:
            return result
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
        result = self._provider_execute("screen_compliance_risk", text)
        if result is not _NO_PROVIDER:
            return result
        lowered = text.lower()
        hits = [
            word
            for word in ("guaranteed return", "inside information", "auto trade", "无风险", "内幕")
            if word in lowered
        ]
        return {"risk": "high" if hits else "low", "matches": hits}

    def publish_investment_memo(self, memo_id: str, distribution_list: list[str] | None = None) -> dict[str, Any]:
        result = self._provider_execute("publish_investment_memo", memo_id, distribution_list)
        if result is not _NO_PROVIDER:
            return result
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
        result = self._provider_execute("propose_portfolio_rebalance", portfolio_id, proposed_changes)
        if result is not _NO_PROVIDER:
            return result
        return {
            "approval_required": True,
            "action": f"propose rebalance for portfolio {portfolio_id}",
            "risk_level": "high",
            "portfolio_id": portfolio_id,
            "proposed_changes": proposed_changes or [],
        }
