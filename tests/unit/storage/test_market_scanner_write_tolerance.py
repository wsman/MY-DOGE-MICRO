"""Unit tests for ScanMarketUseCase per-ticker fault tolerance (S007-005).

These tests target the canonical use case and adapter instead of the legacy
``src/micro/market_scanner`` module. They verify:

- CN/US ticker discovery from a fake local vipdoc tree.
- A single ticker read failure does not abort the scan.
- A single ticker write failure (StorageWriteError) is recorded and does not
  abort the scan.
- Progress callback receives at least the completion event.
"""
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from doge.application.contracts.request import ScanMarketRequest
from doge.application.use_cases.scan_market import ScanMarketUseCase
from doge.core.ports.file_scanner import ITdxFileScanner
from doge.core.ports.repository import IStockRepository, StorageWriteError


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class FakeFileScanner(ITdxFileScanner):
    """Yield pre-canned frames for a list of tickers."""

    def __init__(self, frames_by_ticker):
        self._frames = frames_by_ticker

    def list_tickers(self, market, tdx_path):
        return list(self._frames.keys())

    def scan_local(self, market, tdx_path, progress_callback=None):
        total = len(self._frames)
        for i, (ticker, frame) in enumerate(self._frames.items()):
            if frame is None:
                if progress_callback and (i % 2 == 0 or i == total - 1):
                    progress_callback(50, f"read failed: {ticker}")
                continue
            if progress_callback and (i % 50 == 0 or i == total - 1):
                progress_callback(int((i + 1) / total * 100), f"scanning: {ticker}")
            yield frame
        if progress_callback:
            progress_callback(100, "scan complete")


class FakeStockRepository(IStockRepository):
    """In-memory stock repository that optionally raises on a bad ticker."""

    def __init__(self, fail_tickers=None):
        self._data = []
        self._fail_tickers = set(fail_tickers or [])
        self.ensure_schema_calls = []
        self.save_calls = []

    def ensure_schema(self, market):
        self.ensure_schema_calls.append(market)

    def save_prices(self, market, frame):
        ticker = str(frame["ticker"].iloc[0])
        self.save_calls.append((market, ticker))
        if ticker in self._fail_tickers:
            raise StorageWriteError(f"simulated write failure for {ticker}")
        self._data.append(frame)
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


def _frame(ticker):
    return pd.DataFrame({
        "date": ["2026-01-02"],
        "open": [10.0],
        "high": [11.0],
        "low": [9.0],
        "close": [10.5],
        "volume": [1000],
        "amount": [10000.0],
        "ticker": [ticker],
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestScanMarketUseCase:
    def test_single_write_failure_continues_scan(self):
        """Legacy parity: one ticker's StorageWriteError must not abort the scan."""
        # Arrange
        scanner = FakeFileScanner({
            "GOOD1.SZ": _frame("GOOD1.SZ"),
            "BAD.SZ": _frame("BAD.SZ"),
            "GOOD2.SZ": _frame("GOOD2.SZ"),
        })
        repo = FakeStockRepository(fail_tickers=["BAD.SZ"])
        uc = ScanMarketUseCase(stock_repo=repo, file_scanner=scanner)

        # Act
        resp = uc.execute(
            ScanMarketRequest(market="cn", source="tdx-local", tdx_path="/fake")
        )

        # Assert
        assert resp.total_tickers == 3
        assert resp.success_count == 2
        assert resp.failed_count == 1
        assert repo.save_calls == [
            ("cn", "GOOD1.SZ"),
            ("cn", "BAD.SZ"),
            ("cn", "GOOD2.SZ"),
        ]

    def test_read_failure_continues_scan(self):
        """A ticker whose frame cannot be read is skipped; scan continues."""
        scanner = FakeFileScanner({
            "GOOD.SZ": _frame("GOOD.SZ"),
            "BAD.SZ": None,  # read failure
        })
        repo = FakeStockRepository()
        uc = ScanMarketUseCase(stock_repo=repo, file_scanner=scanner)

        resp = uc.execute(
            ScanMarketRequest(market="cn", source="tdx-local", tdx_path="/fake")
        )

        assert resp.total_tickers == 1
        assert resp.success_count == 1
        assert resp.failed_count == 0
        assert repo.save_calls == [("cn", "GOOD.SZ")]

    def test_progress_callback_receives_completion(self):
        """Progress callback is invoked at least at completion."""
        scanner = FakeFileScanner({
            "A.SZ": _frame("A.SZ"),
            "B.SZ": _frame("B.SZ"),
        })
        repo = FakeStockRepository()
        uc = ScanMarketUseCase(stock_repo=repo, file_scanner=scanner)

        events = []

        def _cb(pct, msg):
            events.append((pct, msg))

        uc.execute(
            ScanMarketRequest(market="cn", source="tdx-local", tdx_path="/fake"),
            progress_callback=_cb,
        )

        assert events
        assert events[-1][0] == 100

    def test_ensure_schema_is_called_once(self):
        scanner = FakeFileScanner({"A.SZ": _frame("A.SZ")})
        repo = FakeStockRepository()
        uc = ScanMarketUseCase(stock_repo=repo, file_scanner=scanner)

        uc.execute(
            ScanMarketRequest(market="us", source="tdx-local", tdx_path="/fake")
        )

        assert repo.ensure_schema_calls == ["us"]


class TestTDXFileScannerDiscovery:
    def test_cn_ticker_discovery_uses_whitelist(self, tmp_path):
        """CN discovery filters codes starting with 00/30/60/68 and len==6."""
        from doge.infrastructure.data_source.tdx_file_scanner import TDXFileScanner

        root = tmp_path / "vipdoc"
        sh_dir = root / "sh" / "lday"
        sh_dir.mkdir(parents=True)
        (sh_dir / "sh600000.day").write_bytes(b"\x00" * 32)
        (sh_dir / "sh900001.day").write_bytes(b"\x00" * 32)  # B-share excluded
        (sh_dir / "sh123.day").write_bytes(b"\x00" * 32)  # bad code

        scanner = TDXFileScanner()
        tickers = scanner.list_tickers("cn", str(root))

        assert tickers == ["600000.SH"]

    def test_us_ticker_discovery_uses_alphabetic_filter(self, tmp_path):
        """US discovery excludes HK and non-alpha codes."""
        from doge.infrastructure.data_source.tdx_file_scanner import TDXFileScanner

        root = tmp_path / "vipdoc"
        ds_dir = root / "ds" / "lday"
        ds_dir.mkdir(parents=True)
        (ds_dir / "74#AAPL.day").write_bytes(b"\x00" * 32)
        (ds_dir / "74#HK0001.day").write_bytes(b"\x00" * 32)
        (ds_dir / "74#123.day").write_bytes(b"\x00" * 32)

        scanner = TDXFileScanner()
        tickers = scanner.list_tickers("us", str(root))

        assert tickers == ["AAPL"]

    def test_autocorrect_appends_vipdoc(self, tmp_path):
        """Passing the parent directory auto-corrects to vipdoc when present."""
        from doge.infrastructure.data_source.tdx_file_scanner import TDXFileScanner

        parent = tmp_path / "tdx"
        vipdoc = parent / "vipdoc"
        sh_dir = vipdoc / "sh" / "lday"
        sh_dir.mkdir(parents=True)
        (sh_dir / "sh000001.day").write_bytes(b"\x00" * 32)

        scanner = TDXFileScanner()
        tickers = scanner.list_tickers("cn", str(parent))

        assert "000001.SH" in tickers


class TestTDXFileScannerParse:
    def test_parse_cn_day_file(self, tmp_path):
        """A single-record CN .day file parses to the expected frame."""
        from doge.infrastructure.data_source.tdx_file_scanner import TDXFileScanner

        # Build one 32-byte CN record.
        # Format: <IIIII fII  => date, open, high, low, close, amount, volume, _
        import struct
        record = struct.pack(
            "<IIIII fII",
            20260102, 1000, 1100, 900, 1050, 10000.0, 1000, 0
        )
        path = tmp_path / "sh000001.day"
        path.write_bytes(record)

        scanner = TDXFileScanner()
        df = scanner._parse_file(str(path), "cn")

        assert not df.empty
        assert df["date"].iloc[0] == "2026-01-02"
        assert df["open"].iloc[0] == 10.0
        assert df["close"].iloc[0] == 10.5

    def test_parse_us_day_file(self, tmp_path):
        """A single-record US .day file parses to the expected frame."""
        from doge.infrastructure.data_source.tdx_file_scanner import TDXFileScanner
        import struct

        # Format: <IfffffII
        record = struct.pack(
            "<IfffffII",
            20260102, 150.0, 155.0, 149.0, 153.0, 1_000_000.0, 5000, 0
        )
        path = tmp_path / "74#AAPL.day"
        path.write_bytes(record)

        scanner = TDXFileScanner()
        df = scanner._parse_file(str(path), "us")

        assert not df.empty
        assert df["close"].iloc[0] == 153.0


# ---------------------------------------------------------------------------
# Legacy module test (kept as a smoke test)
# ---------------------------------------------------------------------------
class TestLegacyMarketScannerShim:
    def test_shim_class_still_importable(self):
        import sys
        from pathlib import Path

        MICRO_DIR = Path(__file__).resolve().parents[3] / "src" / "micro"
        if str(MICRO_DIR) not in sys.path:
            sys.path.insert(0, str(MICRO_DIR))

        import market_scanner as ms
        assert hasattr(ms, "MarketScanner")
        assert hasattr(ms, "_tdx_server_sync")
