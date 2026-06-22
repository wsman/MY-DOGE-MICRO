"""Generate a structured, evidence-aware industry report.

Boundary: this is the compatibility report/tool workflow used by the
`generate_industry_report` deterministic tool and local report generation. New
top-level Research Copilot product workflows should enter through
`IndustryAnalyzerAgentUseCase` and the shared RuntimeKernel.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from doge.application.contracts.request import GenerateIndustryReportRequest
from doge.application.contracts.response import IndustryReportResponse
from doge.application.services.citation_service import CitationService
from doge.application.services.claim_validation_service import ClaimValidationService


RESEARCH_PATH = "compatibility_report_tool"


class GenerateIndustryReportUseCase:
    """Generate a compatibility industry report from deterministic local inputs."""

    def __init__(
        self,
        ranking_service,
        llm_client,
        *,
        stock_service=None,
        rag_service=None,
        report_repository=None,
        claim_repository=None,
        citation_service: CitationService | None = None,
        claim_validation_service: ClaimValidationService | None = None,
    ) -> None:
        """Initialize with injected service and port.

        Args:
            ranking_service: A :class:`~doge.core.services.ranking_service.RankingService`.
            llm_client: An :class:`~doge.core.ports.llm.ILLMClient`.
            stock_service: Optional service exposing ``overview(ticker, market)``.
            rag_service: Optional service exposing ``search(query, limit=...)``.
            report_repository: Optional repository exposing ``save_research_report``.
            claim_repository: Optional repository for claim/citation persistence.
        """
        self._ranking_service = ranking_service
        self._llm_client = llm_client
        self._stock_service = stock_service
        self._rag_service = rag_service
        self._report_repository = report_repository
        self._claim_repository = claim_repository
        self._citation_service = citation_service or CitationService()
        self._claim_validation = claim_validation_service or ClaimValidationService()

    def execute(self, request: GenerateIndustryReportRequest) -> IndustryReportResponse:
        """Run the industry report workflow.

        The workflow is intentionally local-first. Ranking, fundamentals, RAG
        search, LLM synthesis, claim validation, and citation persistence are all
        optional injected seams; when a seam is unavailable the use case returns a
        deterministic report with explicit evidence gaps instead of raising.
        """
        industry = request.industry or "semiconductor"
        report_id = _report_id(request.market, industry, request.tickers or [])
        title = f"{industry.title()} Industry Report ({request.market.upper()})"

        rankings = self._safe_rankings(request.market)
        tickers = _select_tickers(request.tickers, rankings)
        fundamentals = self._safe_fundamentals(tickers, request.market)
        research = self._safe_research(request.research_query or industry, tickers)
        claim_texts = _extract_claims(industry, rankings, fundamentals, research)

        claims = []
        citations = []
        for claim_text in claim_texts:
            evidence_for_claim = self._safe_research(claim_text, tickers)
            claim = self._claim_validation.validate(
                report_id=report_id,
                claim_text=claim_text,
                evidence_results=evidence_for_claim,
                metadata={"industry": industry, "market": request.market},
            )
            claim_citations = self._citation_service.citations_for_claim(claim, evidence_for_claim)
            self._persist_claim_and_citations(claim, claim_citations)
            claims.append(claim.to_dict())
            citations.extend(citation.to_dict() for citation in claim_citations)

        content = self._synthesize_report(
            request=request,
            title=title,
            rankings=rankings,
            fundamentals=fundamentals,
            research=research,
            claims=claims,
            citations=citations,
        )
        persisted = self._persist_report(
            title=title,
            content=content,
            industry=industry,
            analyst=request.analyst_model,
        )
        return IndustryReportResponse(
            market=request.market,
            industry=industry,
            report_id=report_id,
            title=title,
            content=content,
            rankings=rankings,
            fundamentals=fundamentals,
            research=research,
            claims=claims,
            citations=citations,
            persisted=persisted,
        )

    def _safe_rankings(self, market: str) -> list[dict[str, Any]]:
        try:
            return list(self._ranking_service.rsrs(market, 10))
        except Exception:
            return []

    def _safe_fundamentals(self, tickers: list[str], market: str) -> list[dict[str, Any]]:
        if self._stock_service is None:
            return []
        rows = []
        for ticker in tickers[:5]:
            try:
                overview = self._stock_service.overview(ticker, market)
            except Exception:
                overview = {}
            if overview:
                rows.append({"ticker": ticker, **overview})
        return rows

    def _safe_research(self, query: str, tickers: list[str]) -> list[dict[str, Any]]:
        if self._rag_service is None:
            return []
        search_query = " ".join([query, *tickers[:5]]).strip()
        try:
            return list(self._rag_service.search(search_query, limit=5).get("results", []))
        except Exception:
            return []

    def _synthesize_report(
        self,
        *,
        request: GenerateIndustryReportRequest,
        title: str,
        rankings: list[dict[str, Any]],
        fundamentals: list[dict[str, Any]],
        research: list[dict[str, Any]],
        claims: list[dict[str, Any]],
        citations: list[dict[str, Any]],
    ) -> str:
        prompt = _prompt_payload(
            title=title,
            market=request.market,
            industry=request.industry,
            rankings=rankings,
            fundamentals=fundamentals,
            research=research,
            claims=claims,
            citations=citations,
        )
        generated = None
        try:
            generated = self._llm_client.chat(
                "You write concise, evidence-grounded financial industry reports.",
                prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
        except Exception:
            generated = None
        if generated:
            return generated
        return _render_markdown(
            title=title,
            market=request.market,
            rankings=rankings,
            fundamentals=fundamentals,
            research=research,
            claims=claims,
            citations=citations,
        )

    def _persist_report(self, *, title: str, content: str, industry: str, analyst: str) -> bool:
        if self._report_repository is None:
            return False
        try:
            self._report_repository.save_research_report(
                title=title,
                content=content,
                tags=f"Industry,{industry}",
                analyst=analyst,
            )
            return True
        except Exception:
            return False

    def _persist_claim_and_citations(self, claim, citations) -> None:
        if self._claim_repository is None:
            return
        try:
            self._claim_repository.save_claim(claim)
            for citation in citations:
                self._claim_repository.save_citation(citation)
        except Exception:
            return


def _select_tickers(requested: list[str] | None, rankings: list[dict[str, Any]]) -> list[str]:
    if requested:
        return [ticker for ticker in requested if ticker]
    tickers = []
    for row in rankings:
        value = row.get("ticker") or row.get("symbol") or row.get("code")
        if value:
            tickers.append(str(value))
    return tickers[:10]


def _extract_claims(
    industry: str,
    rankings: list[dict[str, Any]],
    fundamentals: list[dict[str, Any]],
    research: list[dict[str, Any]],
) -> list[str]:
    claims: list[str] = []
    if rankings:
        top = rankings[0]
        ticker = top.get("ticker") or top.get("symbol") or top.get("code") or "top constituent"
        score = top.get("rsrs") or top.get("rsrs_z") or top.get("score")
        suffix = f" with ranking score {score}" if score is not None else ""
        claims.append(f"{ticker} leads the {industry} ranking{suffix}.")
    if fundamentals:
        sectors = sorted({str(item.get("sector") or item.get("industry") or "unknown") for item in fundamentals})
        claims.append(f"Tracked fundamentals cover {len(fundamentals)} companies across {', '.join(sectors[:3])}.")
    if research:
        claims.append(f"Local research evidence contains {len(research)} relevant source chunks for {industry}.")
    if not claims:
        claims.append(f"{industry.title()} report has insufficient local evidence for a directional claim.")
    return claims


def _prompt_payload(**payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _render_markdown(
    *,
    title: str,
    market: str,
    rankings: list[dict[str, Any]],
    fundamentals: list[dict[str, Any]],
    research: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    citations: list[dict[str, Any]],
) -> str:
    lines = [
        f"# {title}",
        "",
        f"Market: `{market}`",
        "",
        "## Rankings",
        _table_preview(rankings, ["ticker", "symbol", "score", "rsrs", "rsrs_z"]),
        "",
        "## Fundamentals",
        _table_preview(fundamentals, ["ticker", "name", "sector", "industry", "latest_price"]),
        "",
        "## Research Evidence",
        _evidence_preview(research),
        "",
        "## Validated Claims",
        *[f"- {claim['status']}: {claim['text']}" for claim in claims],
        "",
        "## Citations",
        _citation_preview(citations),
    ]
    return "\n".join(lines)


def _table_preview(rows: list[dict[str, Any]], preferred_keys: list[str]) -> str:
    if not rows:
        return "- No local data available."
    lines = []
    for row in rows[:5]:
        parts = []
        for key in preferred_keys:
            if key in row and row[key] not in (None, ""):
                parts.append(f"{key}={row[key]}")
        if not parts:
            parts = [f"{key}={value}" for key, value in list(row.items())[:4]]
        lines.append("- " + ", ".join(parts))
    return "\n".join(lines)


def _evidence_preview(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "- No local research chunks retrieved."
    return "\n".join(
        f"- {item.get('document_id') or item.get('source') or 'source'}"
        f" p.{item.get('page_number', '?')}: {str(item.get('text', ''))[:180]}"
        for item in rows[:5]
    )


def _citation_preview(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "- No claim-level citations available."
    rendered = []
    for index, item in enumerate(rows[:10], start=1):
        page = f", p. {item['page_number']}" if item.get("page_number") is not None else ""
        rendered.append(f"- [{index}] {item.get('source')}{page}: {item.get('snippet')}")
    return "\n".join(rendered)


def _report_id(market: str, industry: str, tickers: list[str]) -> str:
    digest = hashlib.sha256(
        "|".join([market, industry, *tickers]).encode("utf-8")
    ).hexdigest()[:12]
    slug = re.sub(r"[^a-z0-9]+", "-", industry.lower()).strip("-") or "industry"
    return f"industry-{market}-{slug}-{digest}"
