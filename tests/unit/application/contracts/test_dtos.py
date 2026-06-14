"""Tests for Sprint 007-001 application-layer request/response DTOs."""

from dataclasses import FrozenInstanceError

import pytest

from doge.application.contracts import (
    GenerateAnomalyReportRequest,
    GenerateCatalogRequest,
    GenerateIndustryReportRequest,
    GenerateMacroReportRequest,
    GenerateMarketOverviewRequest,
    ManageNoteRequest,
    PopulateStockNamesRequest,
    QueryTickerRequest,
    ScanMarketRequest,
)
from doge.application.contracts.response import (
    AnomalyReportResponse,
    CatalogResponse,
    IndustryReportResponse,
    MacroReportResponse,
    ManageNoteResponse,
    MarketOverviewResponse,
    NoteItem,
    PopulateStockNamesResponse,
    QueryTickerResponse,
    ScanMarketResponse,
    ScanResultItem,
    TickerMetadata,
    TickerNoteSummary,
    TickerPricePoint,
)


# ── Request DTOs ──

class TestRequestDtos:
    def test_scan_market_request_defaults(self):
        req = ScanMarketRequest()
        assert req.market == "cn"
        assert req.source == "tdx"
        assert req.tickers is None
        assert req.max_workers == 4
        assert req.batch_size == 50

    def test_scan_market_request_frozen(self):
        req = ScanMarketRequest(market="us")
        with pytest.raises(FrozenInstanceError):
            req.market = "cn"

    def test_generate_macro_report_request_defaults(self):
        req = GenerateMacroReportRequest()
        assert req.analyst_model == "deepseek-chat"
        assert req.max_tokens == 4096
        assert req.temperature == 0.7
        assert req.custom_prompt is None

    def test_manage_note_request_defaults(self):
        req = ManageNoteRequest()
        assert req.operation == "list_recent"
        assert req.market == "cn"
        assert req.note_type == "comment"
        assert req.days == 7
        assert req.limit == 50

    def test_manage_note_request_frozen(self):
        req = ManageNoteRequest(operation="create")
        with pytest.raises(FrozenInstanceError):
            req.operation = "delete"

    def test_query_ticker_request_requires_ticker(self):
        with pytest.raises(TypeError):
            QueryTickerRequest()  # type: ignore[call-arg]

    def test_query_ticker_request_defaults(self):
        req = QueryTickerRequest(ticker="000001.SZ")
        assert req.market == "cn"
        assert req.days == 20
        assert req.include_notes is True
        assert req.include_metadata is True
        assert req.max_notes == 5

    def test_generate_market_overview_request_defaults(self):
        req = GenerateMarketOverviewRequest()
        assert req.market == "cn"
        assert req.top == 20
        assert req.days == 10

    def test_generate_anomaly_report_request_defaults(self):
        req = GenerateAnomalyReportRequest()
        assert req.market == "cn"
        assert req.min_ratio == 3.0
        assert req.top == 20

    def test_generate_catalog_request_defaults(self):
        req = GenerateCatalogRequest()
        assert req.market == "cn"

    def test_populate_stock_names_request_defaults(self):
        req = PopulateStockNamesRequest()
        assert req.market == "cn"
        assert req.tickers is None
        assert req.delay == 0.3
        assert req.batch_size == 50

    def test_generate_industry_report_request_defaults(self):
        req = GenerateIndustryReportRequest()
        assert req.market == "cn"
        assert req.tickers is None
        assert req.analyst_model == "deepseek-chat"


# ── Response DTOs ──

class TestResponseDtos:
    def test_scan_market_response_defaults(self):
        resp = ScanMarketResponse(market="cn")
        assert resp.total_tickers == 0
        assert resp.results == []

    def test_scan_market_response_frozen(self):
        resp = ScanMarketResponse(market="cn")
        with pytest.raises(FrozenInstanceError):
            resp.market = "us"

    def test_scan_result_item_defaults(self):
        item = ScanResultItem(ticker="AAPL")
        assert item.status == "success"
        assert item.rows_appended == 0

    def test_macro_report_response_defaults(self):
        resp = MacroReportResponse()
        assert resp.risk_signal == "neutral"
        assert resp.volatility == "low"

    def test_note_item_defaults(self):
        item = NoteItem(note_id=1, ticker="AAPL", content="note")
        assert item.market == ""
        assert item.note_type == "comment"

    def test_manage_note_response_defaults(self):
        resp = ManageNoteResponse()
        assert resp.notes == []
        assert resp.success is False

    def test_ticker_price_point_defaults(self):
        point = TickerPricePoint(date="2024-01-01")
        assert point.open == 0.0
        assert point.volume == 0

    def test_ticker_metadata_defaults(self):
        meta = TickerMetadata()
        assert meta.name is None

    def test_ticker_note_summary_defaults(self):
        summary = TickerNoteSummary()
        assert summary.count_total == 0
        assert summary.recent_notes == []

    def test_query_ticker_response_defaults(self):
        resp = QueryTickerResponse(ticker="AAPL")
        assert resp.market == ""
        assert resp.prices == []

    def test_market_overview_response_defaults(self):
        resp = MarketOverviewResponse()
        assert resp.markdown == ""

    def test_anomaly_report_response_defaults(self):
        resp = AnomalyReportResponse()
        assert resp.markdown == ""

    def test_catalog_response_defaults(self):
        resp = CatalogResponse()
        assert resp.entry_count == 0

    def test_populate_stock_names_response_defaults(self):
        resp = PopulateStockNamesResponse()
        assert resp.fetched == 0

    def test_industry_report_response_defaults(self):
        resp = IndustryReportResponse()
        assert resp.content == ""
        assert resp.error is None


# ── Stubs / no-external-deps ──

class TestContractModulePurity:
    def test_request_module_imports_only_stdlib(self):
        """Request DTOs must not import pandas, numpy, framework, or infrastructure."""
        import doge.application.contracts.request as request_module

        source = request_module.__file__
        with open(source, encoding="utf-8") as f:
            text = f.read()
        forbidden = ["pandas", "numpy", "doge.infrastructure", "fastapi", "mcp"]
        for name in forbidden:
            assert name not in text, f"{name} found in request.py"

    def test_response_module_imports_only_stdlib(self):
        """Response DTOs must not import pandas, numpy, framework, or infrastructure."""
        import doge.application.contracts.response as response_module

        source = response_module.__file__
        with open(source, encoding="utf-8") as f:
            text = f.read()
        forbidden = ["pandas", "numpy", "doge.infrastructure", "fastapi", "mcp"]
        for name in forbidden:
            assert name not in text, f"{name} found in response.py"
