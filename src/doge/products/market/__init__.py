"""Market Intelligence facade."""

from doge.application.use_cases.generate_anomaly_report import GenerateAnomalyReportUseCase
from doge.application.use_cases.generate_catalog import GenerateCatalogUseCase
from doge.application.use_cases.generate_market_overview import GenerateMarketOverviewUseCase
from doge.application.use_cases.populate_stock_names import PopulateStockNamesUseCase
from doge.application.use_cases.query_ticker import QueryTickerUseCase
from doge.application.use_cases.scan_market import ScanMarketUseCase
from doge.core.domain.models import (
    BreadthRecord,
    MarketType,
    OHLCV,
    RSRSRecord,
    Stock,
    Ticker,
    VolumeAnomaly,
)
from doge.core.ports.cache import ITickerNameCache
from doge.core.ports.data_source import IMarketDataSource
from doge.core.ports.market_view import IMarketViewRepository
from doge.core.ports.metadata import ITickerMetadataSource
from doge.core.services.anomaly_service import AnomalyService
from doge.core.services.breadth_service import BreadthService
from doge.core.services.ranking_service import RankingService
from doge.core.services.stock_service import StockService
from doge.core.services.view_service import ViewService
from .tools import MarketToolProvider

__all__ = [
    "AnomalyService",
    "BreadthRecord",
    "BreadthService",
    "GenerateAnomalyReportUseCase",
    "GenerateCatalogUseCase",
    "GenerateMarketOverviewUseCase",
    "IMarketDataSource",
    "IMarketViewRepository",
    "ITickerMetadataSource",
    "ITickerNameCache",
    "MarketToolProvider",
    "MarketType",
    "OHLCV",
    "PopulateStockNamesUseCase",
    "QueryTickerUseCase",
    "RSRSRecord",
    "RankingService",
    "ScanMarketUseCase",
    "Stock",
    "StockService",
    "Ticker",
    "ViewService",
    "VolumeAnomaly",
]
