"""Research evidence tool execution provider.

Compatibility implementation; canonical facade is `doge.products.research.tools`.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from doge.application.capabilities.tool_utils import (
    ServiceFactory,
    claim_matches_evidence,
    claim_matches_rows,
    document_scope_from_context,
    filter_results_for_context,
    is_restricted_context,
    resolve,
)
from doge.core.domain.tool_descriptor import ToolDescriptor
from doge.core.domain.tool_policy import ToolCategory


class ResearchToolProvider:
    """Executes claim validation, evidence lookup, and report generation tools."""

    def __init__(
        self,
        *,
        stock_service_factory: ServiceFactory | None = None,
        rag_service_factory: ServiceFactory | None = None,
        note_repository_factory: ServiceFactory | None = None,
        industry_report_use_case_factory: ServiceFactory | None = None,
    ) -> None:
        self._stock_service_factory = stock_service_factory
        self._rag_service_factory = rag_service_factory
        self._note_repository_factory = note_repository_factory
        self._industry_report_use_case_factory = industry_report_use_case_factory

    def tool_methods(self) -> dict[str, Any]:
        return {
            "validate_financial_claims": self.validate_financial_claims,
            "generate_industry_report": self.generate_industry_report,
            "lookup_evidence": self.lookup_evidence,
        }

    def tool_descriptors(self) -> tuple[ToolDescriptor, ...]:
        return (
            ToolDescriptor(
                name="validate_financial_claims",
                description="Validate a material financial claim.",
                properties={
                    "claim": {"type": "string"},
                    "ticker": {"type": "string"},
                    "market": {"type": "string", "enum": ["cn", "us"]},
                },
                required=("claim", "ticker"),
                category=ToolCategory.ANALYTICAL,
            ),
            ToolDescriptor(
                name="generate_industry_report",
                description="Generate an evidence-aware industry report.",
                properties={
                    "industry": {"type": "string"},
                    "market": {"type": "string", "enum": ["cn", "us"]},
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                category=ToolCategory.GENERATIVE,
            ),
            ToolDescriptor(
                name="lookup_evidence",
                description="Look up source evidence snippets.",
                properties={
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                required=("query",),
                category=ToolCategory.READ_ONLY,
            ),
        )

    def validate_financial_claims(
        self,
        claim: str,
        ticker: str = "AAPL",
        market: str = "us",
        *,
        context: Any = None,
    ) -> dict[str, Any]:
        evidence = []
        try:
            document_ids = document_scope_from_context(context)
            evidence = self._rag_service().search(claim, document_ids=document_ids, limit=3).get("results", [])
            evidence = filter_results_for_context(evidence, context)
        except Exception:
            evidence = []
        rows = self._stock_service().query(ticker, market, 5)
        status = "data_unavailable"
        if evidence:
            status = "supported" if claim_matches_evidence(claim, evidence) else "insufficient_evidence"
        elif rows:
            status = "supported" if claim_matches_rows(claim, rows) else "contradicted"
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
        document_ids = document_scope_from_context(context)
        try:
            rag_result = self._rag_service().search(query, document_ids=document_ids, limit=limit)
            rag_result["results"] = filter_results_for_context(rag_result.get("results", []), context)
            if rag_result.get("results"):
                return rag_result
        except Exception:
            pass
        if is_restricted_context(context):
            return {"query": query, "limit": limit, "source": "rag", "results": []}
        rows = self._note_repository().search_notes(query, limit=limit)
        return {"query": query, "limit": limit, "source": "notes", "results": rows[:limit]}

    def _stock_service(self):
        return resolve(self._stock_service_factory, "stock_service")

    def _rag_service(self):
        return resolve(self._rag_service_factory, "rag_service")

    def _note_repository(self):
        return resolve(self._note_repository_factory, "note_repository")

    def _industry_report_use_case(self):
        return resolve(self._industry_report_use_case_factory, "industry_report_use_case")
