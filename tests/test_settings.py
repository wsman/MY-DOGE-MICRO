"""Tests for src/doge/config/settings.py (Runtime Configuration, Module #1).

Validates the centralization contract from ADR-0002 and the CDD
`runtime-configuration` acceptance criteria:
- singleton identity and reset seam
- env override of DOGE_DB_DIR / DOGE_CN_DB / ...
- empty-string env treated as unset
- frozen dataclass immutability
- derived DB paths resolve relative to DOGE_DB_DIR
"""
import dataclasses
import os
import sys
from pathlib import Path

# Bootstrap src/ onto sys.path without relying on the legacy sys.path hacks
# this module is meant to police. This is the documented test-shim exception.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from doge.config import get_settings
from doge.config.settings import (
    DBConfig,
    FEATURE_LIFECYCLES,
    FeatureConfig,
    FeatureLifecycle,
    MCPConfig,
    MarketConfig,
    Settings,
    TDXConfig,
    reset_settings,
)


# Keys this module is contractually allowed to read via _env_path.
DOGE_PATH_VARS = [
    "DOGE_DB_DIR",
    "DOGE_CN_DB",
    "DOGE_US_DB",
    "DOGE_RESEARCH_DB",
    "DOGE_DUCKDB_PATH",
    "DOGE_VIEWS_SQL_TRACKED",
]

DOGE_FEATURE_VARS = [
    "DOGE_FEATURE_RUN_SUMMARY_API",
    "DOGE_FEATURE_PLATFORM_OBJECTS",
    "DOGE_FEATURE_WORKFLOW_TEMPLATES",
    "DOGE_FEATURE_CAPABILITY_REGISTRY",
    "DOGE_FEATURE_RUNTIME_OUTBOX_PUBLISHER",
    "DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED",
    "DOGE_FEATURE_SLOT_PLATFORM",
    "DOGE_PYTHON_ANALYSIS_EXECUTOR",
]

DOGE_DAEMON_VARS = [
    "DOGE_DAEMON_PORT",
    "DOGE_PROCESS_ROLE",
]


@pytest.fixture(autouse=True)
def _clean_env_and_cache(monkeypatch):
    """Strip DOGE_* path vars and reset the singleton before every test."""
    for var in DOGE_PATH_VARS + DOGE_FEATURE_VARS + DOGE_DAEMON_VARS:
        monkeypatch.delenv(var, raising=False)
    reset_settings()
    yield
    reset_settings()


class TestSingleton:
    def test_get_settings_returns_same_instance_within_process(self):
        # Arrange / Act
        first = get_settings()
        second = get_settings()
        # Assert
        assert first is second

    def test_reset_settings_clears_singleton(self):
        # Arrange
        first = get_settings()
        # Act
        reset_settings()
        second = get_settings()
        # Assert
        assert first is not second

    def test_env_change_without_reset_keeps_cached_value(self, monkeypatch):
        # Arrange
        original = get_settings()
        # Act — mutate env but do NOT reset
        monkeypatch.setenv("DOGE_CN_DB", "/tmp/should_be_ignored.db")
        cached = get_settings()
        # Assert
        assert cached is original
        assert cached.db.cn_db == original.db.cn_db


class TestEnvOverrides:
    def test_doge_cn_db_override_honored(self, monkeypatch):
        # Arrange
        monkeypatch.setenv("DOGE_CN_DB", "/tmp/custom_cn.db")
        # Act
        settings = get_settings()
        # Assert
        assert settings.db.cn_db == Path("/tmp/custom_cn.db")

    def test_doge_db_dir_propagates_to_derived_defaults(self, monkeypatch, tmp_path):
        # Arrange
        monkeypatch.setenv("DOGE_DB_DIR", str(tmp_path))
        # Act
        db = get_settings().db
        # Assert
        assert db.dir == tmp_path
        assert db.cn_db == tmp_path / "market_data_cn.db"
        assert db.us_db == tmp_path / "market_data_us.db"
        assert db.research_db == tmp_path / "research_insights.db"
        assert db.duckdb == tmp_path / "market.duckdb"
        assert db.views_sql == tmp_path / "views.sql"

    def test_per_db_override_beats_doge_db_dir_default(self, monkeypatch, tmp_path):
        # Arrange
        monkeypatch.setenv("DOGE_DB_DIR", str(tmp_path))
        monkeypatch.setenv("DOGE_CN_DB", str(tmp_path / "elsewhere.db"))
        # Act
        db = get_settings().db
        # Assert
        assert db.cn_db == tmp_path / "elsewhere.db"
        # Non-overridden siblings still derive from DOGE_DB_DIR
        assert db.us_db == tmp_path / "market_data_us.db"

    def test_empty_string_env_treated_as_unset(self, monkeypatch):
        # Arrange — empty string must fall back to the default
        monkeypatch.setenv("DOGE_US_DB", "")
        # Act
        settings = get_settings()
        # Assert
        assert settings.db.us_db == settings.db.dir / "market_data_us.db"


class TestImmutability:
    def test_all_configs_are_frozen(self):
        # Arrange / Act / Assert
        for cls in (Settings, DBConfig, TDXConfig, MarketConfig, MCPConfig, FeatureConfig, FeatureLifecycle):
            assert getattr(cls, "__dataclass_params__").frozen is True, f"{cls.__name__} must be frozen"

    def test_setting_a_db_field_raises(self):
        # Arrange
        settings = get_settings()
        # Act / Assert
        with pytest.raises(dataclasses.FrozenInstanceError):
            settings.db.cn_db = Path("/tmp/x.db")  # type: ignore[misc]

    def test_setting_a_top_level_field_raises(self):
        # Arrange
        settings = get_settings()
        # Act / Assert
        with pytest.raises(dataclasses.FrozenInstanceError):
            settings.project_root = Path("/tmp")  # type: ignore[misc]


class TestDerivedProperties:
    def test_report_dir_under_project_root(self):
        # Arrange
        settings = get_settings()
        # Act / Assert
        assert settings.report_dir == settings.project_root / "ai_report"

    def test_data_dir_aliases_db_dir(self):
        # Arrange
        settings = get_settings()
        # Act / Assert
        assert settings.data_dir == settings.db.dir

    def test_stock_names_csv_and_catalog_under_data_dir(self):
        # Arrange
        settings = get_settings()
        # Act / Assert
        assert settings.stock_names_csv == settings.data_dir / "stock_names_cn.csv"
        assert settings.catalog_json == settings.data_dir / "catalog.json"


class TestViewsSqlTrackedResolution:
    """S003-005: the DuckDB view DDL is version-controlled inside the package.

    ``views_sql_tracked`` points at src/doge/infrastructure/database/views.sql
    (shipped in the repo); ``views_sql`` remains the data-dir mirror
    (data/views.sql, gitignored). ``resolved_views_sql()`` prefers the tracked
    copy and falls back to the data-dir mirror for backward compat.
    """

    def test_views_sql_tracked_points_inside_package(self):
        # Arrange / Act
        settings = get_settings()
        # Assert — the tracked DDL lives with the database infrastructure layer.
        assert settings.db.views_sql_tracked.name == "views.sql"
        assert "infrastructure" in settings.db.views_sql_tracked.parts
        assert "doge" in settings.db.views_sql_tracked.parts

    def test_views_sql_mirror_still_derives_from_db_dir(self, monkeypatch, tmp_path):
        # Arrange — DOGE_DB_DIR override must still propagate to the mirror path.
        monkeypatch.setenv("DOGE_DB_DIR", str(tmp_path))
        reset_settings()
        # Act
        db = get_settings().db
        # Assert
        assert db.views_sql == tmp_path / "views.sql"

    def test_resolved_views_sql_prefers_tracked_when_present(self):
        # Arrange — the tracked DDL ships with the repo, so it exists in this
        # checkout. resolved_views_sql() must return it (not the data mirror).
        settings = get_settings()
        # Act / Assert
        assert settings.db.views_sql_tracked.exists(), (
            "tracked views.sql missing — the version-controlled DDL must ship "
            "at src/doge/infrastructure/database/views.sql"
        )
        assert settings.db.resolved_views_sql() == settings.db.views_sql_tracked

    def test_resolved_views_sql_falls_back_to_data_mirror_when_tracked_absent(
        self, monkeypatch, tmp_path
    ):
        # Arrange — point the tracked path at a nonexistent file and confirm
        # the resolver falls back to the data-dir mirror.
        monkeypatch.setenv("DOGE_VIEWS_SQL_TRACKED", str(tmp_path / "nope.sql"))
        reset_settings()
        db = get_settings().db
        # Act / Assert
        assert not db.views_sql_tracked.exists()
        assert db.resolved_views_sql() == db.views_sql


class TestKnownConstants:
    def test_market_whitelist_is_cn_us(self):
        assert get_settings().market.whitelist == frozenset({"cn", "us"})

    def test_mcp_defaults_match_documented_budget(self):
        mcp = get_settings().mcp
        assert mcp.tool_timeout == 30
        assert mcp.sse_host == "127.0.0.1"
        assert mcp.sse_port == 8902
        assert mcp.stdio_transport == "stdio"

    def test_tdx_ports_match_protocol(self):
        tdx = get_settings().tdx
        assert tdx.cn_port == 7709
        assert tdx.us_port == 7727
        assert tdx.timeout == 5
        assert len(tdx.cn_servers) >= 1 and len(tdx.us_servers) >= 1

    def test_yfinance_config_defaults(self):
        """YFinanceConfig (S005-006) carries the retry/period defaults that
        previously were module-level constants in yfinance.py."""
        yf = get_settings().yfinance
        assert yf.max_retries == 3
        assert yf.retry_delay == 5.0
        assert yf.period_days == 120

    def test_daemon_process_role_defaults_to_all(self):
        assert get_settings().daemon.process_role == "all"

    def test_daemon_process_role_accepts_explicit_api(self, monkeypatch):
        monkeypatch.setenv("DOGE_PROCESS_ROLE", "api")
        reset_settings()

        try:
            assert get_settings().daemon.process_role == "api"
        finally:
            reset_settings()

    def test_daemon_process_role_rejects_unknown_value(self, monkeypatch):
        monkeypatch.setenv("DOGE_PROCESS_ROLE", "scheduler")
        reset_settings()

        try:
            with pytest.raises(ValueError, match="DOGE_PROCESS_ROLE"):
                get_settings()
        finally:
            reset_settings()


class TestFeatureLifecycle:
    def test_platformization_flags_default_off(self):
        features = get_settings().features

        assert features.run_summary_api is False
        assert features.platform_objects is False
        assert features.workflow_templates is False
        assert features.capability_registry is False
        assert features.runtime_outbox_publisher is False
        assert features.python_analysis_enabled is False
        assert features.slot_platform is False
        assert features.python_analysis_executor == "disabled"

    def test_feature_lifecycle_metadata_covers_all_python_flags(self):
        assert set(FEATURE_LIFECYCLES) == {
            "run_summary_api",
            "platform_objects",
            "workflow_templates",
            "capability_registry",
            "runtime_outbox_publisher",
            "python_analysis_enabled",
            "slot_platform",
        }
        assert {
            lifecycle.env_var for lifecycle in FEATURE_LIFECYCLES.values()
        } == set(DOGE_FEATURE_VARS) - {"DOGE_PYTHON_ANALYSIS_EXECUTOR"}

        for lifecycle in FEATURE_LIFECYCLES.values():
            assert lifecycle.current_default is False
            assert lifecycle.introduced
            assert lifecycle.target_default_on
            assert lifecycle.target_removal
            assert lifecycle.replacement_behavior
            assert lifecycle.regression_commands
            assert lifecycle.rollback_criterion
