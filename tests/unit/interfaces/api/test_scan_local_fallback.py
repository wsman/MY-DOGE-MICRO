"""Regression tests for the API scan router local fallback path (S007-005).

These tests directly exercise ``doge.interfaces.api.routers.scan._run_local_scan``
to prove it wires the injected storage repository into
``build_scan_market_use_case`` rather than relying on a stale local variable or
read-only default repository.
"""
from pathlib import Path

import pandas as pd
import pytest

from doge.application.use_cases.scan_market import ScanMarketUseCase
from doge.bootstrap.gateway import GatewayContainer
from doge.core.ports.repository import IStockRepository, StorageWriteError
from doge.interfaces.api.routers import scan as scan_router


class _FakeStorageRepo(IStockRepository):
    """In-memory repo that records ensure_schema/save_prices calls."""

    def __init__(self, fail_tickers=None):
        self._fail = set(fail_tickers or [])
        self.ensure_schema_calls = []
        self.save_calls = []

    def ensure_schema(self, market: str) -> None:
        self.ensure_schema_calls.append(market)

    def save_prices(self, market: str, frame) -> int:
        ticker = str(frame["ticker"].iloc[0])
        self.save_calls.append((market, ticker))
        if ticker in self._fail:
            raise StorageWriteError(f"forced failure for {ticker}")
        return len(frame)

    def get_prices(self, ticker, market, days=20):
        return []

    def get_overview(self, ticker, market):
        return {}

    def get_sync_state(self, tickers):
        return {}

    def get_kline(self, ticker, market, days=120):
        return []

    def list_distinct_tickers(self, market):
        return []


class _FakeFileScanner:
    """Yield canned frames without touching the filesystem."""

    def __init__(self, frames):
        self._frames = frames

    def scan_local(self, market, tdx_path, progress_callback=None):
        for i, frame in enumerate(self._frames):
            if progress_callback and (i % 50 == 0 or i == len(self._frames) - 1):
                progress_callback(int((i + 1) / len(self._frames) * 100), f"scanning")
            yield frame
        if progress_callback:
            progress_callback(100, "scan complete")

    def list_tickers(self, market, tdx_path):
        return []


def test_run_local_scan_wires_injected_storage_repo(monkeypatch, tmp_path):
    """_run_local_scan must use the passed storage repo, not a global."""
    storage = _FakeStorageRepo()
    frames = [
        pd.DataFrame({
            "date": ["2026-01-02"],
            "open": [10.0],
            "high": [11.0],
            "low": [9.0],
            "close": [10.5],
            "volume": [1000],
            "amount": [10000.0],
            "ticker": ["A.SZ"],
        })
    ]

    monkeypatch.setattr(
        GatewayContainer,
        "build_scan_market_use_case",
        lambda self, stock_repo, data_source=None, file_scanner=None, refresh_views_callable=None: (
            ScanMarketUseCase(
                stock_repo=stock_repo,
                file_scanner=_FakeFileScanner(frames),
                data_source=None,
                refresh_views_callable=lambda: None,
            )
        ),
    )

    events = []

    def _cb(pct, msg):
        events.append((pct, msg))

    scan_router._run_local_scan("cn", str(tmp_path), "ignored", _cb, storage)

    assert storage.ensure_schema_calls == ["cn"]
    assert storage.save_calls == [("cn", "A.SZ")]
    assert events[-1][0] == 100


def test_run_local_scan_records_write_failure_without_aborting(monkeypatch, tmp_path):
    """A write failure in one ticker must be recorded and not abort the callback."""
    storage = _FakeStorageRepo(fail_tickers=["BAD.SZ"])
    frames = [
        pd.DataFrame({
            "date": ["2026-01-02"],
            "open": [10.0],
            "high": [11.0],
            "low": [9.0],
            "close": [10.5],
            "volume": [1000],
            "amount": [10000.0],
            "ticker": ["BAD.SZ"],
        }),
        pd.DataFrame({
            "date": ["2026-01-02"],
            "open": [10.0],
            "high": [11.0],
            "low": [9.0],
            "close": [10.5],
            "volume": [1000],
            "amount": [10000.0],
            "ticker": ["GOOD.SZ"],
        }),
    ]

    monkeypatch.setattr(
        GatewayContainer,
        "build_scan_market_use_case",
        lambda self, stock_repo, data_source=None, file_scanner=None, refresh_views_callable=None: (
            ScanMarketUseCase(
                stock_repo=stock_repo,
                file_scanner=_FakeFileScanner(frames),
                data_source=None,
                refresh_views_callable=lambda: None,
            )
        ),
    )

    events = []

    def _cb(pct, msg):
        events.append((pct, msg))

    scan_router._run_local_scan("cn", str(tmp_path), "ignored", _cb, storage)

    assert storage.save_calls == [("cn", "BAD.SZ"), ("cn", "GOOD.SZ")]
    assert events[-1][0] == 100


def test_run_local_scan_skips_when_no_tdx_path():
    """Empty tdx_path emits a skip callback and does not call the repo."""
    storage = _FakeStorageRepo()
    events = []

    def _cb(pct, msg):
        events.append((pct, msg))

    scan_router._run_local_scan("cn", "", "ignored", _cb, storage)

    assert storage.ensure_schema_calls == []
    assert storage.save_calls == []
    assert events == [(0, "no tdx_path provided, skipping local scan")]
