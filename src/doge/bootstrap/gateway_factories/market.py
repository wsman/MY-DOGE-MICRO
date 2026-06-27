"""Gateway factory helpers for market-data services and TDX sources."""
from __future__ import annotations
from doge.core.services.anomaly_service import AnomalyService
from doge.core.services.breadth_service import BreadthService
from doge.core.services.ranking_service import RankingService
from doge.core.services.stock_service import StockService
from doge.core.services.view_service import ViewService
from doge.infrastructure.data_source.tdx_file_scanner import TDXFileScanner
from doge.infrastructure.data_source.tdx_server_list import ConfigTDXServerList
from doge.infrastructure.data_source.yfinance_metadata import YFinanceMetadataSource
from doge.bootstrap.gateway_factories.repositories import (
    build_stock_repository,
    build_view_repository,
)


def build_view_service(repo=None):
    return ViewService(repo if repo is not None else build_view_repository())


def build_stock_service(repo=None):
    return StockService(repo if repo is not None else build_stock_repository())


def build_ranking_service(repo=None):
    return RankingService(repo if repo is not None else build_view_repository())


def build_breadth_service(repo=None):
    return BreadthService(repo if repo is not None else build_view_repository())


def build_anomaly_service(repo=None):
    return AnomalyService(repo if repo is not None else build_view_repository())


def build_metadata_source(max_retries: int | None = None, retry_delay: float | None = None):
    return YFinanceMetadataSource(max_retries=max_retries, retry_delay=retry_delay)


def build_tdx_server_list():
    return ConfigTDXServerList()


def build_tdx_data_source(preferred_server: str | None = None):
    from doge.infrastructure.data_source.tdx import TDXDataSource

    return TDXDataSource(preferred_server=preferred_server)


def refresh_views() -> None:
    from doge.infrastructure.database.duckdb import DuckDBConnection

    DuckDBConnection(read_only=False).refresh_views()
