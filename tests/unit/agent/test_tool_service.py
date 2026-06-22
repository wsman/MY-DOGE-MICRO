import pytest
from pathlib import Path

from doge.application.agent.tool_service import ToolApplicationService
from doge.core.domain.enterprise_context import EnterpriseContext


class FailingStockService:
    def query(self, ticker, market, days):
        raise RuntimeError("service unavailable")


class EmptyNotes:
    def search_notes(self, query, limit=50):
        return []


class EmptyRAG:
    def search(self, query, document_ids=None, limit=5):
        return {"query": query, "limit": limit, "results": []}


class FilledRAG:
    def search(self, query, document_ids=None, limit=5):
        return {
            "query": query,
            "limit": limit,
            "results": [{"source": "rag", "chunk_id": "chk-1", "text": "earnings quality improved"}],
        }


class ScopedRAG:
    def __init__(self):
        self.document_ids = None

    def search(self, query, document_ids=None, limit=5):
        self.document_ids = document_ids
        return {
            "query": query,
            "limit": limit,
            "results": [
                {"source": "rag", "document_id": "doc-allowed", "chunk_id": "chk-1", "text": "allowed evidence"},
                {"source": "rag", "document_id": "doc-denied", "chunk_id": "chk-2", "text": "denied evidence"},
                {"source": "rag", "chunk_id": "chk-3", "text": "unscoped evidence"},
            ],
        }


class StockRows:
    def query(self, ticker, market, days):
        return [{"ticker": ticker, "close": 101.5, "volume": 1000}]


class FakeFinancialStatements:
    def get_statement(self, ticker, statement_type="income", period="annual"):
        return {
            "ticker": ticker,
            "statement_type": statement_type,
            "period": period,
            "provider": "fake",
            "provider_status": "fallback",
            "fields": {"revenue": 100.0},
        }


class FakeAnnouncements:
    def list_announcements(self, ticker, limit=5):
        return {
            "ticker": ticker,
            "provider": "fake",
            "provider_status": "fallback",
            "announcements": [{"title": "Q1 report"}],
        }


class FakeConsensus:
    def compare_estimates(self, ticker, metric="eps"):
        return {"ticker": ticker, "metric": metric, "provider_status": "provider_unavailable"}


class FakeIndustry:
    def classify(self, ticker, market="us"):
        return {"ticker": ticker, "market": market, "sector": "technology", "industry": "software"}


def test_query_stock_propagates_service_error():
    service = ToolApplicationService(stock_service_factory=lambda: FailingStockService())

    with pytest.raises(RuntimeError, match="service unavailable"):
        service.query_stock("AAPL", "us", 5)


def test_lookup_evidence_returns_empty_when_no_notes():
    service = ToolApplicationService(
        rag_service_factory=lambda: EmptyRAG(),
        note_repository_factory=lambda: EmptyNotes(),
    )

    result = service.lookup_evidence("earnings", limit=1)

    assert result["results"] == []


def test_lookup_evidence_prefers_rag_results():
    service = ToolApplicationService(
        rag_service_factory=lambda: FilledRAG(),
        note_repository_factory=lambda: EmptyNotes(),
    )

    result = service.lookup_evidence("earnings", limit=1)

    assert result["results"] == [{"source": "rag", "chunk_id": "chk-1", "text": "earnings quality improved"}]


def test_lookup_evidence_scopes_enterprise_context_to_allowed_documents():
    rag = ScopedRAG()
    service = ToolApplicationService(
        rag_service_factory=lambda: rag,
        note_repository_factory=lambda: EmptyNotes(),
    )
    context = EnterpriseContext(
        tenant_id="tenant-a",
        user_hash="user-a",
        document_acl=frozenset({"doc-allowed"}),
    )

    result = service.lookup_evidence("evidence", limit=5, context=context)

    assert rag.document_ids == ["doc-allowed"]
    assert [item["document_id"] for item in result["results"]] == ["doc-allowed"]


def test_lookup_evidence_denies_enterprise_context_without_document_acl():
    service = ToolApplicationService(
        rag_service_factory=lambda: ScopedRAG(),
        note_repository_factory=lambda: EmptyNotes(),
    )
    context = EnterpriseContext(tenant_id="tenant-a", user_hash="user-a")

    result = service.lookup_evidence("evidence", limit=5, context=context)

    assert result["source"] == "rag"
    assert result["results"] == []


def test_validate_financial_claims_requires_matching_number():
    service = ToolApplicationService(stock_service_factory=lambda: StockRows())

    validated = service.validate_financial_claims("AAPL close was 101.5", "AAPL", "us")
    contradicted = service.validate_financial_claims("AAPL close was 88.0", "AAPL", "us")

    assert validated["status"] == "supported"
    assert contradicted["status"] == "contradicted"


def test_validate_financial_claims_uses_rag_evidence():
    service = ToolApplicationService(
        stock_service_factory=lambda: StockRows(),
        rag_service_factory=lambda: FilledRAG(),
    )

    result = service.validate_financial_claims("earnings quality improved", "AAPL", "us")

    assert result["status"] == "supported"
    assert result["evidence"] == [{"source": "rag", "chunk_id": "chk-1", "text": "earnings quality improved"}]


def test_validate_financial_claims_filters_enterprise_evidence():
    service = ToolApplicationService(
        stock_service_factory=lambda: StockRows(),
        rag_service_factory=lambda: ScopedRAG(),
    )
    context = EnterpriseContext(
        tenant_id="tenant-a",
        user_hash="user-a",
        document_acl=frozenset({"doc-allowed"}),
    )

    result = service.validate_financial_claims("allowed evidence", "AAPL", "us", context=context)

    assert result["status"] == "supported"
    assert [item["document_id"] for item in result["evidence"]] == ["doc-allowed"]


def test_financial_connector_tools_return_provider_status():
    service = ToolApplicationService(
        financial_statement_repository_factory=lambda: FakeFinancialStatements(),
        company_announcement_repository_factory=lambda: FakeAnnouncements(),
        consensus_estimate_repository_factory=lambda: FakeConsensus(),
        industry_classification_source_factory=lambda: FakeIndustry(),
    )

    statements = service.get_financial_statements("MSFT")
    announcements = service.get_company_announcements("MSFT")
    consensus = service.compare_consensus_estimates("MSFT")
    classification = service.get_industry_classification("MSFT")

    assert statements["provider_status"] == "fallback"
    assert announcements["provider_status"] == "fallback"
    assert consensus["provider_status"] == "provider_unavailable"
    assert classification["industry"] == "software"


def test_tool_application_service_does_not_import_composition():
    source = Path("src/doge/application/agent/tool_service.py").read_text(encoding="utf-8")

    assert "doge.application import composition" not in source
    assert "doge.application.composition" not in source
