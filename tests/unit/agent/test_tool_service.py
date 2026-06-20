import pytest

from doge.application.agent.tool_service import ToolApplicationService


class FailingStockService:
    def query(self, ticker, market, days):
        raise RuntimeError("service unavailable")


class EmptyNotes:
    def search_notes(self, query, limit=50):
        return []


class StockRows:
    def query(self, ticker, market, days):
        return [{"ticker": ticker, "close": 101.5, "volume": 1000}]


def test_query_stock_propagates_service_error():
    service = ToolApplicationService(stock_service_factory=lambda: FailingStockService())

    with pytest.raises(RuntimeError, match="service unavailable"):
        service.query_stock("AAPL", "us", 5)


def test_lookup_evidence_returns_empty_when_no_notes(monkeypatch):
    from doge.application import composition

    monkeypatch.setattr(composition, "build_note_repository", lambda: EmptyNotes())
    service = ToolApplicationService()

    result = service.lookup_evidence("earnings", limit=1)

    assert result["results"] == []


def test_validate_financial_claims_requires_matching_number():
    service = ToolApplicationService(stock_service_factory=lambda: StockRows())

    validated = service.validate_financial_claims("AAPL close was 101.5", "AAPL", "us")
    unverified = service.validate_financial_claims("AAPL close was 88.0", "AAPL", "us")

    assert validated["status"] == "validated"
    assert unverified["status"] == "unverified"
