"""Centralized configuration — single source of truth for all paths, constants and env vars.

Replaces every scattered `_PROJECT_ROOT`, `_DB_DIR`, `_HERE` and `sys.path` hack.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ── Project root detection ──────────────────────────────────────────────
# This file lives at: src/doge/config/settings.py
# Project root is three levels up.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _env_path(name: str, default: Path) -> Path:
    env = os.environ.get(name)
    return Path(env) if env else default


@dataclass(frozen=True)
class DBConfig:
    """Database paths (override via env vars)."""
    dir: Path = field(default_factory=lambda: _env_path("DOGE_DB_DIR", _PROJECT_ROOT / "data"))
    cn_db: Path = field(init=False)
    us_db: Path = field(init=False)
    research_db: Path = field(init=False)
    duckdb: Path = field(init=False)
    views_sql: Path = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "cn_db", _env_path("DOGE_CN_DB", self.dir / "market_data_cn.db"))
        object.__setattr__(self, "us_db", _env_path("DOGE_US_DB", self.dir / "market_data_us.db"))
        object.__setattr__(self, "research_db", _env_path("DOGE_RESEARCH_DB", self.dir / "research_insights.db"))
        object.__setattr__(self, "duckdb", _env_path("DOGE_DUCKDB_PATH", self.dir / "market.duckdb"))
        object.__setattr__(self, "views_sql", self.dir / "views.sql")


@dataclass(frozen=True)
class TDXConfig:
    """TDX server settings."""
    cn_servers: tuple[str, ...] = (
        "180.153.18.170", "180.153.18.171", "60.191.117.167",
        "115.238.56.198", "218.75.126.9",
    )
    us_servers: tuple[str, ...] = (
        "112.74.214.43", "120.25.218.6", "43.139.173.246",
        "159.75.90.107", "139.9.191.175",
    )
    cn_port: int = 7709
    us_port: int = 7727
    timeout: int = 5


@dataclass(frozen=True)
class MarketConfig:
    """Market-related constants."""
    whitelist: frozenset[str] = frozenset({"cn", "us"})
    cn_min_volume: int = 200_000_000
    us_min_volume: int = 20_000_000
    max_change_pct: int = 400
    rsrs_window: int = 18


@dataclass(frozen=True)
class MCPConfig:
    """MCP server settings."""
    tool_timeout: int = 30
    stdio_transport: str = "stdio"
    sse_host: str = "127.0.0.1"
    sse_port: int = 8902


@dataclass(frozen=True)
class Settings:
    """Application settings container."""
    project_root: Path = _PROJECT_ROOT
    db: DBConfig = field(default_factory=DBConfig)
    tdx: TDXConfig = field(default_factory=TDXConfig)
    market: MarketConfig = field(default_factory=MarketConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)

    # Derived paths
    @property
    def report_dir(self) -> Path:
        return self.project_root / "ai_report"

    @property
    def data_dir(self) -> Path:
        return self.db.dir

    @property
    def stock_names_csv(self) -> Path:
        return self.data_dir / "stock_names_cn.csv"

    @property
    def catalog_json(self) -> Path:
        return self.data_dir / "catalog.json"


# ── Singleton instance ──────────────────────────────────────────────────
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Lazy singleton for application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset singleton (useful for tests)."""
    global _settings
    _settings = None
