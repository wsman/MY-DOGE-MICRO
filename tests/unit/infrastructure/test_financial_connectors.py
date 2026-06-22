from doge.infrastructure.finance.local_connectors import (
    LocalNoteAnnouncementRepository,
    StaticIndustryClassificationSource,
    StockOverviewFinancialStatementRepository,
    UnavailableConsensusEstimateRepository,
)


class FakeStockService:
    def overview(self, ticker, market):
        return {"ticker": ticker, "market": market, "revenue": 100.0, "net_income": 10.0}


class EmptyStockService:
    def overview(self, ticker, market):
        return {}


class FakeNotes:
    def search_notes(self, query, limit=50):
        return [{"ticker": query, "title": "Annual report"}]


def test_stock_overview_statement_connector_marks_fallback():
    result = StockOverviewFinancialStatementRepository(FakeStockService()).get_statement("MSFT")

    assert result["provider"] == "local_stock_overview"
    assert result["provider_status"] == "fallback"
    assert result["fields"]["revenue"] == 100.0


def test_statement_connector_marks_unavailable_without_fields():
    result = StockOverviewFinancialStatementRepository(EmptyStockService()).get_statement("MISSING")

    assert result["provider_status"] == "provider_unavailable"
    assert result["fields"] == {}


def test_local_note_announcement_connector_marks_source():
    result = LocalNoteAnnouncementRepository(FakeNotes()).list_announcements("MSFT")

    assert result["provider"] == "local_notes"
    assert result["provider_status"] == "fallback"
    assert result["announcements"][0]["title"] == "Annual report"


def test_consensus_connector_returns_typed_unavailable():
    result = UnavailableConsensusEstimateRepository().compare_estimates("MSFT", "eps")

    assert result["provider_status"] == "provider_unavailable"
    assert result["estimates"] == []


def test_static_industry_classification_returns_known_and_unknown_states():
    source = StaticIndustryClassificationSource()

    assert source.classify("NVDA")["industry"] == "semiconductors"
    assert source.classify("UNKNOWN")["provider_status"] == "provider_unavailable"
