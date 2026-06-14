"""Application-layer contracts — request/response DTOs."""

from doge.application.contracts.request import (
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

__all__ = [
    # requests
    "ScanMarketRequest",
    "GenerateMacroReportRequest",
    "ManageNoteRequest",
    "QueryTickerRequest",
    "GenerateMarketOverviewRequest",
    "GenerateAnomalyReportRequest",
    "GenerateCatalogRequest",
    "PopulateStockNamesRequest",
    "GenerateIndustryReportRequest",
    # responses
    "ScanResultItem",
    "ScanMarketResponse",
    "MacroReportResponse",
    "NoteItem",
    "ManageNoteResponse",
    "TickerPricePoint",
    "TickerMetadata",
    "TickerNoteSummary",
    "QueryTickerResponse",
    "MarketOverviewResponse",
    "AnomalyReportResponse",
    "CatalogResponse",
    "PopulateStockNamesResponse",
    "IndustryReportResponse",
]
