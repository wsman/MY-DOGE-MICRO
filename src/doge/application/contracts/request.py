"""Application-layer request DTOs.

All DTOs are frozen dataclasses with stdlib-only imports. They carry no
business logic — only validated, type-annotated inputs for use cases.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ScanMarketRequest:
    """Input for :class:`~doge.application.use_cases.scan_market.ScanMarketUseCase`."""
    market: str = "cn"
    source: str = "tdx"
    tickers: Optional[list[str]] = None
    max_workers: int = 4
    batch_size: int = 50


@dataclass(frozen=True)
class GenerateMacroReportRequest:
    """Input for :class:`~doge.application.use_cases.generate_macro_report.GenerateMacroReportUseCase`."""
    analyst_model: str = "deepseek-chat"
    max_tokens: int = 4096
    temperature: float = 0.7
    custom_prompt: Optional[str] = None


@dataclass(frozen=True)
class ManageNoteRequest:
    """Input for :class:`~doge.application.use_cases.manage_notes.ManageNotesUseCase`."""
    operation: str = "list_recent"
    ticker: Optional[str] = None
    market: str = "cn"
    note_id: Optional[int] = None
    note_text: Optional[str] = None
    note_type: str = "comment"
    title: Optional[str] = None
    tags: Optional[str] = None
    price_at_note: Optional[float] = None
    source: Optional[str] = None
    sentiment: Optional[str] = None
    keyword: Optional[str] = None
    days: int = 7
    limit: int = 50


@dataclass(frozen=True)
class QueryTickerRequest:
    """Input for :class:`~doge.application.use_cases.query_ticker.QueryTickerUseCase`."""
    ticker: str
    market: str = "cn"
    days: int = 20
    include_notes: bool = True
    include_metadata: bool = True
    max_notes: int = 5


@dataclass(frozen=True)
class GenerateMarketOverviewRequest:
    """Input for :class:`~doge.application.use_cases.generate_market_overview.GenerateMarketOverviewUseCase`."""
    market: str = "cn"
    top: int = 20
    days: int = 10


@dataclass(frozen=True)
class GenerateAnomalyReportRequest:
    """Input for :class:`~doge.application.use_cases.generate_anomaly_report.GenerateAnomalyReportUseCase`."""
    market: str = "cn"
    min_ratio: float = 3.0
    top: int = 20


@dataclass(frozen=True)
class GenerateCatalogRequest:
    """Input for :class:`~doge.application.use_cases.generate_catalog.GenerateCatalogUseCase`."""
    market: str = "cn"


@dataclass(frozen=True)
class PopulateStockNamesRequest:
    """Input for :class:`~doge.application.use_cases.populate_stock_names.PopulateStockNamesUseCase`."""
    market: str = "cn"
    tickers: Optional[list[str]] = None
    delay: float = 0.3
    batch_size: int = 50


@dataclass(frozen=True)
class GenerateIndustryReportRequest:
    """Input for :class:`~doge.application.use_cases.generate_industry_report.GenerateIndustryReportUseCase`."""
    market: str = "cn"
    tickers: Optional[list[str]] = None
    analyst_model: str = "deepseek-chat"
    max_tokens: int = 4096
    temperature: float = 0.7
