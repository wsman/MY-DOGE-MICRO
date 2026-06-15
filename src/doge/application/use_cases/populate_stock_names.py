"""Populate stock names use case — batch-fetch metadata and persist names.

Replaces ``src/ai_analysis/fetch_names.py`` with a port-backed implementation.
The use case orchestrates:

- Reading distinct tickers from :class:`~doge.core.ports.repository.IStockRepository`
- Reading/writing cached names via :class:`~doge.core.ports.repository.IStockNameRepository`
- Fetching metadata from :class:`~doge.core.ports.metadata.ITickerMetadataSource`
"""

import json
import time
from pathlib import Path
from typing import Optional

from doge.application.contracts.request import PopulateStockNamesRequest
from doge.application.contracts.response import PopulateStockNamesResponse
from doge.config import get_settings
from doge.core.ports.metadata import ITickerMetadataSource
from doge.core.ports.repository import IStockNameRepository, IStockRepository


class PopulateStockNamesUseCase:
    """Batch-fetch stock names from a metadata source and persist them."""

    def __init__(
        self,
        stock_repo: IStockRepository,
        name_repo: IStockNameRepository,
        metadata_source: ITickerMetadataSource,
    ) -> None:
        """Initialize with injected ports.

        Args:
            stock_repo: Source of distinct market tickers.
            name_repo: Read/write cache for stock names.
            metadata_source: Adapter that fetches ticker metadata.
        """
        self._stock_repo = stock_repo
        self._name_repo = name_repo
        self._metadata_source = metadata_source

    def execute(self, request: PopulateStockNamesRequest) -> PopulateStockNamesResponse:
        """Run the populate workflow."""
        if request.source == "meta_cache":
            return self._from_cache(request)
        return self._from_metadata_source(request)

    def _from_metadata_source(self, request: PopulateStockNamesRequest) -> PopulateStockNamesResponse:
        tickers = request.tickers
        if tickers is None:
            tickers = self._stock_repo.list_distinct_tickers(request.market)

        existing = self._name_repo.get_existing_names()
        to_fetch = [t for t in tickers if t not in existing or not existing[t]]

        if not to_fetch:
            return PopulateStockNamesResponse(
                market=request.market, fetched=0, saved=0, failed=0
            )

        success = 0
        failed = 0
        for i in range(0, len(to_fetch), request.batch_size):
            batch = to_fetch[i : i + request.batch_size]
            for ticker in batch:
                try:
                    meta = self._metadata_source.get_metadata(ticker, request.market)
                    if meta:
                        name = meta.get("name", "")
                        sector = meta.get("sector", "")
                        self._name_repo.save_name(
                            ticker, name, name, request.market, sector, ""
                        )
                        success += 1
                    else:
                        self._name_repo.save_name(
                            ticker, ticker, "", request.market, "", ""
                        )
                        failed += 1
                except Exception:
                    self._name_repo.save_name(
                        ticker, ticker, "", request.market, "", ""
                    )
                    failed += 1
                time.sleep(request.delay)

        return PopulateStockNamesResponse(
            market=request.market,
            fetched=len(to_fetch),
            saved=success,
            failed=failed,
        )

    def _from_cache(self, request: PopulateStockNamesRequest) -> PopulateStockNamesResponse:
        """Import names from the local ``meta_cache.json`` file."""
        cache_path = (
            Path(request.cache_path)
            if request.cache_path
            else get_settings().db.dir / "meta_cache.json"
        )
        if not cache_path.exists():
            return PopulateStockNamesResponse(
                market=request.market, fetched=0, saved=0, failed=0
            )

        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)

        existing = self._name_repo.get_existing_names()
        saved = 0
        for ticker, info in cache.items():
            if ticker not in existing or not existing[ticker]:
                name = info.get("name", "") if isinstance(info, dict) else ""
                sector = info.get("sector", "") if isinstance(info, dict) else ""
                market = "cn" if "." in ticker else "us"
                self._name_repo.save_name(ticker, name, name, market, sector, "")
                saved += 1

        return PopulateStockNamesResponse(
            market=request.market, fetched=len(cache), saved=saved, failed=0
        )
