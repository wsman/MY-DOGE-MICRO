"""Scan market use case — orchestrates data-source fetch + persistence + view refresh.

Supports two sources:

- ``tdx-server``: uses an injected ``IMarketDataSource`` to download tickers one
  by one and persist them.
- ``tdx-local``: uses an injected ``ITdxFileScanner`` to read local .day files
  and persist them.

The use case owns the single-logical-writer seam: it calls
``stock_repo.ensure_schema()`` once, then iterates over the ticker stream and
calls ``stock_repo.save_prices()`` per frame. Per-ticker read/write failures are
recorded but do **not** abort the scan (parity with the legacy
``src/micro/market_scanner`` contract).
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from doge.application.contracts.request import ScanMarketRequest
from doge.application.contracts.response import ScanMarketResponse, ScanResultItem
from doge.core.ports.data_source import IMarketDataSource
from doge.core.ports.file_scanner import ITdxFileScanner, ProgressCallback
from doge.core.ports.repository import IStockRepository, StorageWriteError


class ScanMarketUseCase:
    """Orchestrate a full-market data refresh."""

    def __init__(
        self,
        stock_repo: IStockRepository,
        data_source: Optional[IMarketDataSource] = None,
        file_scanner: Optional[ITdxFileScanner] = None,
        refresh_views_callable: Optional[Callable[[], None]] = None,
    ) -> None:
        """Initialize with injected ports.

        Args:
            stock_repo: Read/write market-price repository.
            data_source: Remote data source (used for ``source="tdx-server"``).
            file_scanner: Local .day scanner (used for ``source="tdx-local"``).
            refresh_views_callable: Callable that materializes DuckDB views.
        """
        self._stock_repo = stock_repo
        self._data_source = data_source
        self._file_scanner = file_scanner
        self._refresh_views = refresh_views_callable

    def execute(
        self,
        request: ScanMarketRequest,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ScanMarketResponse:
        """Run the scan workflow."""
        start_time = time.time()
        self._stock_repo.ensure_schema(request.market)

        if request.is_local():
            results = self._scan_local(request, progress_callback)
        else:
            results = self._scan_remote(request, progress_callback)

        if self._refresh_views is not None:
            try:
                self._refresh_views()
            except Exception:
                # Refresh failure is best-effort; scan still completes.
                pass

        success_count = sum(1 for r in results if r.status == "success")
        failed_count = sum(1 for r in results if r.status == "failed")
        skipped_count = sum(1 for r in results if r.status == "skipped")

        return ScanMarketResponse(
            market=request.market,
            total_tickers=len(results),
            success_count=success_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            results=results,
            duration_seconds=round(time.time() - start_time, 3),
        )

    def _scan_local(
        self,
        request: ScanMarketRequest,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> list[ScanResultItem]:
        """Scan local .day files and persist each frame."""
        if self._file_scanner is None:
            return []
        if not request.tdx_path:
            return []

        results: list[ScanResultItem] = []
        for frame in self._file_scanner.scan_local(
            request.market, request.tdx_path, progress_callback=progress_callback
        ):
            ticker = str(frame["ticker"].iloc[0]) if "ticker" in frame.columns else ""
            try:
                self._stock_repo.save_prices(request.market, frame)
                results.append(ScanResultItem(ticker=ticker, status="success"))
            except StorageWriteError as e:
                results.append(
                    ScanResultItem(
                        ticker=ticker,
                        status="failed",
                        message=str(e),
                    )
                )
        return results

    def _scan_remote(
        self,
        request: ScanMarketRequest,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> list[ScanResultItem]:
        """Download tickers from a remote source and persist each frame.

        This is a minimal placeholder for the full server-download orchestration
        (incremental fetches, reconnection, batching) which remains in
        ``micro.tdx_downloader`` for Sprint 007. The use case still provides the
        persistence loop and error handling seam.
        """
        if self._data_source is None:
            return []

        tickers = request.tickers or []
        if not tickers:
            tickers = self._stock_repo.list_distinct_tickers(request.market)

        if not tickers:
            return []

        if not self._data_source.is_connected():
            self._data_source.connect(request.market)

        results: list[ScanResultItem] = []
        for ticker in tickers:
            try:
                frame = self._data_source.download_kline(ticker, request.market)
                if frame is None or frame.empty:
                    results.append(
                        ScanResultItem(ticker=ticker, status="skipped", message="empty")
                    )
                    continue
                frame["ticker"] = ticker
                self._stock_repo.save_prices(request.market, frame)
                results.append(ScanResultItem(ticker=ticker, status="success"))
            except StorageWriteError as e:
                results.append(
                    ScanResultItem(ticker=ticker, status="failed", message=str(e))
                )
            except Exception as e:
                results.append(
                    ScanResultItem(ticker=ticker, status="failed", message=str(e))
                )

            if progress_callback:
                progress_callback(
                    int((len(results) / len(tickers)) * 100),
                    f"downloaded: {ticker}",
                )

        return results
