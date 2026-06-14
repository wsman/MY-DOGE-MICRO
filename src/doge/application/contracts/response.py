"""Application-layer response DTOs.

All DTOs are frozen dataclasses with stdlib-only imports. They carry no
business logic — only structured, type-annotated outputs from use cases.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class ScanResultItem:
    """Per-ticker result inside :class:`ScanMarketResponse`."""
    ticker: str
    status: str = "success"
    rows_appended: int = 0
    message: Optional[str] = None


@dataclass(frozen=True)
class ScanMarketResponse:
    """Output from :class:`~doge.application.use_cases.scan_market.ScanMarketUseCase`."""
    market: str = ""
    total_tickers: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    results: List[ScanResultItem] = field(default_factory=list)
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class MacroReportResponse:
    """Output from :class:`~doge.application.use_cases.generate_macro_report.GenerateMacroReportUseCase`."""
    report_id: Optional[int] = None
    content: str = ""
    risk_signal: str = "neutral"
    volatility: str = "low"
    tags: str = ""
    analyst: str = ""
    generated_at: Optional[str] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class NoteItem:
    """Single note record inside :class:`ManageNoteResponse`."""
    note_id: int = 0
    ticker: str = ""
    market: str = ""
    created_at: str = ""
    note_type: str = "comment"
    title: Optional[str] = None
    content: str = ""
    tags: Optional[str] = None
    price_at_note: Optional[float] = None
    source: Optional[str] = None


@dataclass(frozen=True)
class ManageNoteResponse:
    """Output from :class:`~doge.application.use_cases.manage_notes.ManageNotesUseCase`."""
    operation: str = ""
    success: bool = False
    note_id: Optional[int] = None
    notes: List[NoteItem] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    count: int = 0
    message: str = ""


@dataclass(frozen=True)
class TickerPricePoint:
    """Single OHLCV price point inside :class:`QueryTickerResponse`."""
    date: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    amount: Optional[float] = None
    ma_5: Optional[float] = None
    ma_10: Optional[float] = None
    ma_20: Optional[float] = None
    ma_60: Optional[float] = None
    atr_14: Optional[float] = None


@dataclass(frozen=True)
class TickerMetadata:
    """Ticker metadata block inside :class:`QueryTickerResponse`."""
    name: Optional[str] = None
    name_en: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None


@dataclass(frozen=True)
class TickerNoteSummary:
    """Note summary block inside :class:`QueryTickerResponse`."""
    count_total: int = 0
    recent_notes: List[NoteItem] = field(default_factory=list)


@dataclass(frozen=True)
class QueryTickerResponse:
    """Output from :class:`~doge.application.use_cases.query_ticker.QueryTickerUseCase`."""
    ticker: str = ""
    market: str = ""
    metadata: TickerMetadata = field(default_factory=TickerMetadata)
    prices: List[TickerPricePoint] = field(default_factory=list)
    notes: TickerNoteSummary = field(default_factory=TickerNoteSummary)
    latest_close: Optional[float] = None
    change_pct: Optional[float] = None


@dataclass(frozen=True)
class MarketOverviewResponse:
    """Output from :class:`~doge.application.use_cases.generate_market_overview.GenerateMarketOverviewUseCase`."""
    market: str = ""
    markdown: str = ""


@dataclass(frozen=True)
class AnomalyReportResponse:
    """Output from :class:`~doge.application.use_cases.generate_anomaly_report.GenerateAnomalyReportUseCase`."""
    market: str = ""
    markdown: str = ""


@dataclass(frozen=True)
class CatalogResponse:
    """Output from :class:`~doge.application.use_cases.generate_catalog.GenerateCatalogUseCase`."""
    path: str = ""
    entry_count: int = 0


@dataclass(frozen=True)
class PopulateStockNamesResponse:
    """Output from :class:`~doge.application.use_cases.populate_stock_names.PopulateStockNamesUseCase`."""
    market: str = ""
    fetched: int = 0
    saved: int = 0
    failed: int = 0


@dataclass(frozen=True)
class IndustryReportResponse:
    """Output from :class:`~doge.application.use_cases.generate_industry_report.GenerateIndustryReportUseCase`."""
    market: str = ""
    content: str = ""
    error: Optional[str] = None
