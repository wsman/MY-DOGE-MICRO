"""Regression tests for legacy MarketScanner db_path routing (S007-005).

Verifies that ``MarketScanner.scan_cn_market(db_path, ...)`` and
``scan_us_market(db_path, ...)`` route persistence to the caller-supplied
``db_path`` instead of the centralized settings path.
"""
from pathlib import Path

import pandas as pd
import pytest

import micro.market_scanner as market_scanner


class _FakeUseCase:
    """Stand-in use case that records the request and returns a canned response."""

    def __init__(self):
        self.requests = []

    def execute(self, request, progress_callback=None):
        self.requests.append(request)
        return type(
            "Response",
            (),
            {
                "success_count": 1,
                "total_tickers": 1,
                "failed_count": 0,
            },
        )()


class TestLegacyMarketScannerDbPath:
    def test_scan_cn_market_passes_db_path_to_storage_repo(self, monkeypatch, tmp_path):
        """Regression: scan_cn_market must honor the db_path argument."""
        captured = {}

        def _capture_build(stock_repo=None, **kwargs):
            captured["stock_repo"] = stock_repo
            return _FakeUseCase()

        monkeypatch.setattr(
            market_scanner, "build_scan_market_use_case", _capture_build
        )

        scanner = market_scanner.MarketScanner(str(tmp_path))
        custom_db = str(tmp_path / "custom_cn.db")
        scanner.scan_cn_market(custom_db)

        assert isinstance(
            captured["stock_repo"], market_scanner._LegacyPathStorageRepository
        )
        assert captured["stock_repo"]._db_path == custom_db

    def test_scan_us_market_passes_db_path_to_storage_repo(self, monkeypatch, tmp_path):
        """Regression: scan_us_market must honor the db_path argument."""
        captured = {}

        def _capture_build(stock_repo=None, **kwargs):
            captured["stock_repo"] = stock_repo
            return _FakeUseCase()

        monkeypatch.setattr(
            market_scanner, "build_scan_market_use_case", _capture_build
        )

        scanner = market_scanner.MarketScanner(str(tmp_path))
        custom_db = str(tmp_path / "custom_us.db")
        scanner.scan_us_market(custom_db)

        assert isinstance(
            captured["stock_repo"], market_scanner._LegacyPathStorageRepository
        )
        assert captured["stock_repo"]._db_path == custom_db


class TestLegacyPathStorageRepository:
    def test_ensure_schema_calls_init_db_custom_with_db_path(self, monkeypatch, tmp_path):
        """The adapter must forward ensure_schema to init_db_custom(db_path)."""
        calls = []

        def fake_init_db_custom(db_path):
            calls.append(db_path)

        # Patch the helper that resolves the legacy helpers rather than a
        # specific module path; this keeps the test stable across the two
        # import layouts used in the suite (``import micro.market_scanner``
        # vs legacy ``import market_scanner``).
        monkeypatch.setattr(
            market_scanner,
            "_legacy_db_helpers",
            lambda: (fake_init_db_custom, lambda _data, _db_path, _retention_days=None: None),
        )

        db_path = str(tmp_path / "x.db")
        repo = market_scanner._LegacyPathStorageRepository(db_path)
        repo.ensure_schema("cn")

        assert calls == [db_path]

    def test_save_prices_calls_save_stock_data_custom_with_db_path(
        self, monkeypatch, tmp_path
    ):
        """The adapter must forward save_prices to save_stock_data_custom(frame, db_path)."""
        calls = []

        def fake_save_stock_data_custom(data, db_path, retention_days=None):
            calls.append((db_path, len(data), retention_days))

        monkeypatch.setattr(
            market_scanner,
            "_legacy_db_helpers",
            lambda: (lambda _db_path: None, fake_save_stock_data_custom),
        )

        frame = pd.DataFrame({"ticker": ["A.SZ"], "date": ["2026-01-02"]})
        db_path = str(tmp_path / "y.db")
        repo = market_scanner._LegacyPathStorageRepository(db_path)
        result = repo.save_prices("cn", frame)

        assert result == 1
        assert calls == [(db_path, 1, None)]

    def test_save_prices_surfaces_storage_write_error(self, monkeypatch, tmp_path):
        """A failing legacy write must propagate as StorageWriteError."""
        from doge.core.ports.repository import StorageWriteError

        def fake_save_stock_data_custom(_data, _db_path, _retention_days=None):
            raise StorageWriteError("forced write failure")

        monkeypatch.setattr(
            market_scanner,
            "_legacy_db_helpers",
            lambda: (lambda _db_path: None, fake_save_stock_data_custom),
        )

        frame = pd.DataFrame({"ticker": ["A.SZ"], "date": ["2026-01-02"]})
        repo = market_scanner._LegacyPathStorageRepository(str(tmp_path / "z.db"))

        with pytest.raises(StorageWriteError):
            repo.save_prices("cn", frame)
