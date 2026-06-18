"""Deprecated market scanner — forwards to ``ScanMarketUseCase``.

``src/micro/market_scanner.py`` is kept as a backwards-compatible shim for
Sprint 007. The canonical local-file scanning logic now lives in
``doge.infrastructure.data_source.tdx_file_scanner`` and is orchestrated by
``doge.application.use_cases.scan_market``. This module re-exports the legacy
``MarketScanner`` class so existing callers keep working. It will be removed in
Sprint 008.
"""
import glob
import logging
import os
import re
import warnings

import pandas as pd

warnings.warn(
    "micro.market_scanner is deprecated; use doge.application.use_cases.scan_market instead",
    DeprecationWarning,
    stacklevel=2,
)

from doge.application.composition import build_scan_market_use_case
from doge.application.contracts.request import ScanMarketRequest
from doge.core.ports.repository import IStockRepository


logger = logging.getLogger(__name__)


def _legacy_db_helpers():
    """Resolve legacy database helpers under either import layout.

    ``src/micro`` may be on ``sys.path`` directly (legacy
    ``import market_scanner``) or ``src`` may be on ``sys.path`` (canonical
    ``import micro.market_scanner``). This helper avoids hard-coding either
    layout while preferring the canonical package form.
    """
    try:
        from micro.database import init_db_custom, save_stock_data_custom
    except ImportError:  # pragma: no cover - legacy direct-path import
        from database import init_db_custom, save_stock_data_custom
    return init_db_custom, save_stock_data_custom


class _LegacyPathStorageRepository(IStockRepository):
    """Write-only repository honoring the caller-supplied ``db_path``.

    ``MarketScanner.scan_cn_market(db_path, ...)`` and
    ``scan_us_market(db_path, ...)`` historically wrote to ``db_path``. The
    canonical ``SQLiteStorageRepository`` writes to the centralized settings
    path, which would silently ignore the caller's ``db_path``. This adapter
    restores the legacy contract by routing ``ensure_schema`` / ``save_prices``
    to the legacy ``init_db_custom`` / ``save_stock_data_custom`` helpers with
    the supplied path. Read methods are unsupported because the shim only
    writes; they return empty values.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path

    def ensure_schema(self, market: str) -> None:
        init_db_custom, _ = _legacy_db_helpers()
        init_db_custom(self._db_path)

    def save_prices(self, market: str, frame) -> int:
        _, save_stock_data_custom = _legacy_db_helpers()
        save_stock_data_custom(frame, self._db_path)
        return len(frame)

    def get_prices(self, ticker: str, market: str, days: int = 20):
        return []

    def get_overview(self, ticker: str, market: str) -> dict:
        return {}

    def get_sync_state(self, tickers):
        return {}

    def get_kline(self, ticker: str, market: str, days: int = 120):
        return []

    def list_distinct_tickers(self, market: str):
        return []


class MarketScanner:
    """Backwards-compatible scanner that delegates to ``ScanMarketUseCase``."""

    def __init__(self, tdx_root):
        # Auto-correct path: if directory lacks vipdoc but has a vipdoc subdir,
        # append it (legacy behavior preserved).
        if os.path.basename(tdx_root) != "vipdoc":
            potential = os.path.join(tdx_root, "vipdoc")
            if os.path.exists(potential):
                tdx_root = potential
                print(f"[OK] auto-corrected TDX path: {tdx_root}")
        self.tdx_root = tdx_root

    def scan_cn_market(self, db_path, progress_callback=None, use_server=True):
        """Scan A-share local .day files.

        Note: ``use_server=True`` is no longer implemented in the shim; the
        canonical server path is ``ScanMarketRequest(source='tdx-server')``.
        This shim always scans local files to preserve the legacy fallback
        contract.
        """
        print(f"[SCAN] A-share scan -> {db_path}")
        repo = _LegacyPathStorageRepository(db_path)
        uc = build_scan_market_use_case(
            stock_repo=repo,
            data_source=None,
            refresh_views_callable=lambda: None,
        )
        resp = uc.execute(
            ScanMarketRequest(
                market="cn",
                source="tdx-local",
                tdx_path=self.tdx_root,
            ),
            progress_callback=progress_callback,
        )
        print(
            "[OK] CN local scan complete: {}/{} success, {} failed".format(
                resp.success_count, resp.total_tickers, resp.failed_count
            )
        )
        _refresh_duckdb_views()

    def scan_us_market(self, db_path, progress_callback=None, use_server=True):
        """Scan US local .day files."""
        print(f"[SCAN] US market scan -> {db_path}")
        repo = _LegacyPathStorageRepository(db_path)
        uc = build_scan_market_use_case(
            stock_repo=repo,
            data_source=None,
            refresh_views_callable=lambda: None,
        )
        resp = uc.execute(
            ScanMarketRequest(
                market="us",
                source="tdx-local",
                tdx_path=self.tdx_root,
            ),
            progress_callback=progress_callback,
        )
        print(
            "[OK] US local scan complete: {}/{} success, {} failed".format(
                resp.success_count, resp.total_tickers, resp.failed_count
            )
        )
        _refresh_duckdb_views()


def _refresh_duckdb_views():
    """数据导入后刷新 DuckDB 分析视图"""
    from doge.infrastructure.database.duckdb import DuckDBConnection
    try:
        DuckDBConnection(read_only=False).refresh_views()
        print("[OK] DuckDB analysis views refreshed")
    except Exception as e:
        print("[WARN] DuckDB views refresh failed (non-fatal): {}".format(e))


def _tdx_server_sync(db_path, market="cn", tickers=None, progress_callback=None):
    """Deprecated server sync helper — always returns False and logs degradation."""
    print("  opentdx not available, falling back to local files")
    return False
