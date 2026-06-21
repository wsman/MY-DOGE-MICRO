from doge.application.contracts.request import GenerateIndustryReportRequest
from doge.application.use_cases.generate_industry_report import GenerateIndustryReportUseCase
from doge.infrastructure.database.claim_repository import SQLiteClaimRepository


class FakeRankingService:
    def rsrs(self, market, top):
        return [{"ticker": "NVDA", "score": 2.1, "industry": "semiconductor"}]


class OfflineLLM:
    def chat(self, *args, **kwargs):
        return None


class FakeStockService:
    def overview(self, ticker, market):
        return {
            "ticker": ticker,
            "name": "Nvidia",
            "sector": "semiconductor",
            "latest_price": 101.5,
        }


class FakeRAGService:
    def search(self, query, limit=5):
        return {
            "query": query,
            "limit": limit,
            "results": [
                {
                    "source": "rag",
                    "document_id": "doc-1",
                    "page_number": 2,
                    "chunk_id": "chk-1",
                    "text": "NVDA leads the semiconductor ranking with ranking score 2.1.",
                    "score": 0.98,
                    "visibility": "local",
                }
            ],
        }


class FakeReportRepository:
    def __init__(self):
        self.saved = []

    def save_research_report(self, *, title, content, tags, analyst):
        self.saved.append({
            "title": title,
            "content": content,
            "tags": tags,
            "analyst": analyst,
        })


def test_generate_industry_report_returns_claims_citations_and_persists(tmp_path):
    report_repo = FakeReportRepository()
    claim_repo = SQLiteClaimRepository(tmp_path / "agent.db")
    use_case = GenerateIndustryReportUseCase(
        FakeRankingService(),
        OfflineLLM(),
        stock_service=FakeStockService(),
        rag_service=FakeRAGService(),
        report_repository=report_repo,
        claim_repository=claim_repo,
    )

    response = use_case.execute(
        GenerateIndustryReportRequest(
            market="us",
            industry="semiconductor",
            tickers=["NVDA"],
        )
    )

    assert response.report_id.startswith("industry-us-semiconductor-")
    assert response.persisted is True
    assert response.rankings[0]["ticker"] == "NVDA"
    assert response.fundamentals[0]["sector"] == "semiconductor"
    assert response.claims
    assert response.claims[0]["status"] == "supported"
    assert response.citations
    assert "Validated Claims" in response.content
    assert report_repo.saved[0]["title"] == response.title
    assert claim_repo.list_claims(response.report_id)
    assert claim_repo.list_citations(report_id=response.report_id)
