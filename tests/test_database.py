"""Tests for src/ai_analysis database layer."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from ai_analysis import normalize_ticker


class TestNormalizeTicker:
    def test_cn_6xxx_to_sh(self):
        assert normalize_ticker("601777", "cn") == "601777.SH"

    def test_cn_0xxx_to_sz(self):
        assert normalize_ticker("000001", "cn") == "000001.SZ"

    def test_cn_3xxx_to_sz(self):
        assert normalize_ticker("300001", "cn") == "300001.SZ"

    def test_cn_4xxx_to_bj(self):
        assert normalize_ticker("430047", "cn") == "430047.BJ"

    def test_cn_8xxx_to_bj(self):
        assert normalize_ticker("830899", "cn") == "830899.BJ"

    def test_already_suffixed(self):
        assert normalize_ticker("AAPL", "cn") == "AAPL"
        assert normalize_ticker("601777.SH", "cn") == "601777.SH"

    def test_us_market_passthrough(self):
        assert normalize_ticker("AAPL", "us") == "AAPL"
        assert normalize_ticker("BRK-B", "us") == "BRK-B"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            normalize_ticker("", "cn")
        with pytest.raises(ValueError, match="empty"):
            normalize_ticker("   ", "cn")

    def test_invalid_characters(self):
        with pytest.raises(ValueError, match="invalid characters"):
            normalize_ticker("1; DROP TABLE", "cn")
        with pytest.raises(ValueError, match="invalid characters"):
            normalize_ticker("../etc/passwd", "cn")
        with pytest.raises(ValueError, match="invalid characters"):
            normalize_ticker("test' OR '1'='1", "cn")

    def test_too_long(self):
        with pytest.raises(ValueError, match="too long"):
            normalize_ticker("A" * 21, "cn")

    def test_non_string_raises(self):
        with pytest.raises(ValueError, match="string"):
            normalize_ticker(12345, "cn")
