"""Unit tests for ``YFinanceMetadataSource`` (S006-004).

These tests mock the ``yfinance`` module so they are fast, deterministic, and
network-free. They verify suffix remapping, retry behavior, and degraded ``None``
return on exhaustion.
"""
from unittest.mock import MagicMock

import pytest

from doge.core.ports.metadata import ITickerMetadataSource
from doge.infrastructure.data_source.yfinance_metadata import YFinanceMetadataSource


class TestYFinanceMetadataSourceImplementsPort:
    def test_is_iticker_metadata_source(self):
        assert isinstance(YFinanceMetadataSource(), ITickerMetadataSource)


class TestYFinanceMetadataSourceSuffixRemap:
    def test_cn_shanghai_remapped_to_ss(self, monkeypatch):
        """.SH canonical tickers are remapped to yfinance ``.SS``."""
        source = YFinanceMetadataSource(max_retries=1, retry_delay=0)
        yf_mock = MagicMock()
        yf_mock.Ticker.return_value.info = {
            "shortName": "China Test",
            "sector": "Financials",
        }
        monkeypatch.setattr(source, "_fetch_info_with_retry", lambda _, ticker: yf_mock.Ticker(ticker).info)

        result = source.get_metadata("600000.SH", "cn")

        assert result == {"name": "China Test", "sector": "Financials"}
        yf_mock.Ticker.assert_called_once_with("600000.SS")

    def test_us_ticker_passes_through(self, monkeypatch):
        yf_mock = MagicMock()
        yf_mock.Ticker.return_value.info = {"longName": "Apple Inc.", "sector": "Technology"}
        source = YFinanceMetadataSource(max_retries=1, retry_delay=0)
        monkeypatch.setattr(source, "_fetch_info_with_retry", lambda _, ticker: yf_mock.Ticker(ticker).info)

        result = source.get_metadata("AAPL", "us")

        assert result == {"name": "Apple Inc.", "sector": "Technology"}
        yf_mock.Ticker.assert_called_once_with("AAPL")


class TestYFinanceMetadataSourceResultShape:
    def test_prefers_short_name_over_long_name(self, monkeypatch):
        source = YFinanceMetadataSource(max_retries=1, retry_delay=0)
        monkeypatch.setattr(
            source,
            "_fetch_info_with_retry",
            lambda _yf, _t: {"shortName": "Short", "longName": "Long", "sector": "Tech"},
        )
        assert source.get_metadata("T", "us") == {"name": "Short", "sector": "Tech"}

    def test_falls_back_to_long_name(self, monkeypatch):
        source = YFinanceMetadataSource(max_retries=1, retry_delay=0)
        monkeypatch.setattr(
            source,
            "_fetch_info_with_retry",
            lambda _yf, _t: {"longName": "Long Only", "sector": "Health Care"},
        )
        assert source.get_metadata("T", "us") == {"name": "Long Only", "sector": "Health Care"}

    def test_falls_back_to_industry_when_sector_missing(self, monkeypatch):
        source = YFinanceMetadataSource(max_retries=1, retry_delay=0)
        monkeypatch.setattr(
            source,
            "_fetch_info_with_retry",
            lambda _yf, _t: {"shortName": "Name", "industry": "Software"},
        )
        assert source.get_metadata("T", "us") == {"name": "Name", "sector": "Software"}

    def test_returns_none_when_name_unavailable(self, monkeypatch):
        source = YFinanceMetadataSource(max_retries=1, retry_delay=0)
        monkeypatch.setattr(
            source,
            "_fetch_info_with_retry",
            lambda _yf, _t: {"sector": "Unknown"},
        )
        assert source.get_metadata("T", "us") is None

    def test_returns_none_on_empty_info(self, monkeypatch):
        source = YFinanceMetadataSource(max_retries=1, retry_delay=0)
        monkeypatch.setattr(source, "_fetch_info_with_retry", lambda _yf, _t: {})
        assert source.get_metadata("T", "us") is None


class TestYFinanceMetadataSourceRetryAndDegradation:
    def test_returns_none_when_fetch_exhausts_retries(self, monkeypatch):
        source = YFinanceMetadataSource(max_retries=2, retry_delay=0)
        monkeypatch.setattr(source, "_fetch_info_with_retry", lambda _yf, _t: None)
        assert source.get_metadata("T", "us") is None

    def test_unsupported_market_returns_none(self):
        source = YFinanceMetadataSource(max_retries=1, retry_delay=0)
        assert source.get_metadata("T", "xx") is None

    def test_fetch_with_retry_uses_yfinance_ticker_info(self, monkeypatch):
        """Sanity: the default fetcher calls yfinance.Ticker(ticker).info."""
        source = YFinanceMetadataSource(max_retries=1, retry_delay=0)
        yf_mock = MagicMock()
        yf_mock.Ticker.return_value.info = {"shortName": "Test", "sector": "X"}
        result = source._fetch_info_with_retry(yf_mock, "AAPL")
        assert result == {"shortName": "Test", "sector": "X"}
        yf_mock.Ticker.assert_called_once_with("AAPL")

    def test_fetch_with_retry_returns_none_on_empty_info(self, monkeypatch):
        source = YFinanceMetadataSource(max_retries=1, retry_delay=0)
        yf_mock = MagicMock()
        yf_mock.Ticker.return_value.info = {}
        result = source._fetch_info_with_retry(yf_mock, "AAPL")
        assert result is None

    def test_fetch_with_retry_retries_on_exception(self, monkeypatch):
        source = YFinanceMetadataSource(max_retries=3, retry_delay=0)
        yf_mock = MagicMock()
        call_count = {"n": 0}

        def _failing_then_success(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise RuntimeError("transient")
            mock_ticker = MagicMock()
            mock_ticker.info = {"shortName": "Test", "sector": "X"}
            return mock_ticker

        yf_mock.Ticker.side_effect = _failing_then_success
        result = source._fetch_info_with_retry(yf_mock, "AAPL")
        assert result == {"shortName": "Test", "sector": "X"}
        assert call_count["n"] == 3
