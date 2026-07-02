from doge.products.research.tools import ResearchToolProvider
from doge.core.domain.enterprise_context import EnterpriseContext


class StockService:
    def query(self, ticker, market, days):
        return [{"ticker": ticker, "close": 101.5}]


class RAGService:
    def search(self, query, document_ids=None, limit=5):
        return {
            "query": query,
            "limit": limit,
            "results": [
                {"document_id": "doc-allowed", "chunk_id": "chk-1", "text": "earnings quality improved"},
                {"document_id": "doc-denied", "chunk_id": "chk-2", "text": "denied evidence"},
            ],
        }


class Notes:
    def search_notes(self, query, limit=50):
        return [{"source": "note", "text": query}]


class ReportUseCase:
    def execute(self, request):
        return {"market": request.market, "industry": request.industry, "tickers": request.tickers or []}


def test_research_provider_filters_evidence_by_enterprise_context():
    provider = ResearchToolProvider(
        stock_service_factory=lambda: StockService(),
        rag_service_factory=lambda: RAGService(),
        note_repository_factory=lambda: Notes(),
        industry_report_use_case_factory=lambda: ReportUseCase(),
    )
    context = EnterpriseContext(
        tenant_id="tenant-a",
        user_hash="user-a",
        document_acl=frozenset({"doc-allowed"}),
    )

    validated = provider.validate_financial_claims("earnings quality improved", "AAPL", "us", context=context)
    evidence = provider.lookup_evidence("earnings", 2, context=context)
    report = provider.generate_industry_report("software", "us", ["MSFT"])

    assert validated["status"] == "supported"
    assert [item["document_id"] for item in validated["evidence"]] == ["doc-allowed"]
    assert [item["document_id"] for item in evidence["results"]] == ["doc-allowed"]
    assert report == {"market": "us", "industry": "software", "tickers": ["MSFT"]}


def test_research_provider_denies_unscoped_enterprise_notes_fallback():
    provider = ResearchToolProvider(
        stock_service_factory=lambda: StockService(),
        rag_service_factory=lambda: RAGService(),
        note_repository_factory=lambda: Notes(),
    )
    context = EnterpriseContext(tenant_id="tenant-a", user_hash="user-a")

    result = provider.lookup_evidence("earnings", 2, context=context)

    assert result == {"query": "earnings", "limit": 2, "source": "rag", "results": []}
