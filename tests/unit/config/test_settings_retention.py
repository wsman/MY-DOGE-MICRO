"""Unit tests for the retention_days knob on MarketConfig (TR-006 / S002-007).

Pins the safe-default invariant that closes the silent-truncation bug between
``save_stock_data_custom``'s retention prune and the widest analytical-view
window (``vw_market_breadth_cn``, ``INTERVAL 730 DAYS``).

Scenarios (from the S002-007 spec ``testsToAdd``):
- field exists on Settings().market.retention_days as an int >= 730
- field is frozen (setattr raises FrozenInstanceError)
- default is exactly 730 (a careless future edit fails loudly)
- DOGE_RETENTION_DAYS env override is honored
- empty-string DOGE_RETENTION_DAYS falls back to the default (parity with the
  DOGE_US_DB empty-string contract in test_settings.py:107-113)
"""
import dataclasses
import sys
from pathlib import Path

# Test shim: put src/ on sys.path (the documented exception, see test_settings.py:17-18).
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

import pytest

from doge.config import get_settings
from doge.config.settings import MarketConfig, reset_settings


@pytest.fixture(autouse=True)
def _clean_env_and_cache(monkeypatch):
    """Strip DOGE_RETENTION_DAYS and reset the singleton around every test."""
    monkeypatch.delenv("DOGE_RETENTION_DAYS", raising=False)
    reset_settings()
    yield
    reset_settings()


class TestRetentionField:
    def test_retention_field_exists_on_settings(self):
        # Arrange / Act
        retention = get_settings().market.retention_days
        # Assert — int, and >= 730 (the widest view window, vw_market_breadth_cn)
        assert isinstance(retention, int)
        assert retention >= 730

    def test_retention_field_is_frozen(self):
        # Arrange
        settings = get_settings()
        # Act / Assert — frozen dataclass: mutating raises
        with pytest.raises(dataclasses.FrozenInstanceError):
            settings.market.retention_days = 180  # type: ignore[misc]

    def test_marketconfig_class_is_frozen(self):
        # Arrange / Act / Assert
        assert getattr(MarketConfig, "__dataclass_params__").frozen is True

    def test_retention_default_is_730(self):
        # Arrange / Act
        retention = get_settings().market.retention_days
        # Assert — exact value pinned so a careless edit fails loudly.
        # 730 satisfies the widest view window (vw_market_breadth_cn, views.sql:23).
        assert retention == 730


class TestRetentionEnvOverride:
    def test_doge_retention_days_env_override_honored(self, monkeypatch):
        # Arrange — mirrors test_settings.py:75-82 DOGE_CN_DB override pattern
        monkeypatch.setenv("DOGE_RETENTION_DAYS", "900")
        reset_settings()
        # Act
        retention = get_settings().market.retention_days
        # Assert
        assert retention == 900

    def test_doge_retention_days_override_can_exceed_730(self, monkeypatch):
        # Arrange — operators on storage-constrained setups keep override power
        monkeypatch.setenv("DOGE_RETENTION_DAYS", "1095")
        reset_settings()
        # Act / Assert
        assert get_settings().market.retention_days == 1095

    def test_empty_string_doge_retention_days_falls_back_to_default(self, monkeypatch):
        # Arrange — parity with test_settings.py:107-113 empty-string contract
        monkeypatch.setenv("DOGE_RETENTION_DAYS", "")
        reset_settings()
        # Act
        retention = get_settings().market.retention_days
        # Assert
        assert retention == 730

    def test_unset_doge_retention_days_uses_default(self, monkeypatch):
        # Arrange — env var absent entirely (the production default case)
        monkeypatch.delenv("DOGE_RETENTION_DAYS", raising=False)
        reset_settings()
        # Act / Assert
        assert get_settings().market.retention_days == 730
