"""Tests for IndustryAnalyzer metadata port migration (S006-005).

Verifies that ``IndustryAnalyzer.get_stock_metadata`` delegates the network
lookup to ``ITickerMetadataSource`` via the composition root instead of calling
yfinance directly. Caching and persistence behavior is preserved.
"""
from unittest.mock import MagicMock

import pytest

from micro.industry_analyzer import IndustryAnalyzer


@pytest.fixture(autouse=True)
def _fake_deepseek_key(monkeypatch):
    """IndustryAnalyzer instantiates MacroConfig, which requires the env key."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake-test-key")


class FakeMetadataSource:
    """In-memory fake for ITickerMetadataSource."""

    def __init__(self, data):
        self._data = data
        self.calls = []

    def get_metadata(self, ticker: str, market: str):
        self.calls.append((ticker, market))
        return self._data.get(ticker)


class TestIndustryAnalyzerMetadataPort:
    def test_get_stock_metadata_delegates_to_metadata_source(self, tmp_path, monkeypatch):
        analyzer = IndustryAnalyzer(metadata_source=FakeMetadataSource({
            "AAPL": {"name": "Apple Inc.", "sector": "Technology"},
        }))
        analyzer.metadata_cache = {}  # isolate from on-disk cache

        name, sector = analyzer.get_stock_metadata("AAPL")

        assert name == "Apple Inc."
        assert sector == "Technology"
        assert analyzer._metadata_source.calls == [("AAPL", "us")]

    def test_get_stock_metadata_caches_result_and_skips_second_call(self, tmp_path, monkeypatch):
        fake = FakeMetadataSource({
            "600000.SH": {"name": "China Test", "sector": "Financials"},
        })
        analyzer = IndustryAnalyzer(metadata_source=fake)
        analyzer.metadata_cache = {}  # isolate from on-disk cache

        name1, sector1 = analyzer.get_stock_metadata("600000.SH")
        name2, sector2 = analyzer.get_stock_metadata("600000.SH")

        assert name1 == name2 == "China Test"
        assert sector1 == sector2 == "Financials"
        # Market inferred from .SH suffix
        assert fake.calls == [("600000.SH", "cn")]

    def test_get_stock_metadata_returns_unknown_when_source_returns_none(self):
        analyzer = IndustryAnalyzer(metadata_source=FakeMetadataSource({}))
        analyzer.metadata_cache = {}  # isolate from on-disk cache
        assert analyzer.get_stock_metadata("MISSING") == ("Unknown", "Unknown")

    def test_get_stock_metadata_defaults_to_composition_root_when_not_injected(self, monkeypatch):
        """When no source is injected, the analyzer builds one from composition.py."""
        analyzer = IndustryAnalyzer()
        analyzer.metadata_cache = {}  # isolate from on-disk cache
        # The source should be lazily built on first use.
        assert analyzer._metadata_source is None

        fake = MagicMock()
        fake.get_metadata.return_value = {"name": "Built", "sector": "Root"}
        monkeypatch.setattr(
            "micro.industry_analyzer.build_metadata_source",
            lambda: fake,
        )

        name, sector = analyzer.get_stock_metadata("TICK")
        assert name == "Built"
        assert sector == "Root"
        fake.get_metadata.assert_called_once_with("TICK", "us")
