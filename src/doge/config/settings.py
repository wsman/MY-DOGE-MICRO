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


def _env_int(name: str, default: int) -> int:
    """Read an integer env var, returning ``default`` on unset/empty string.

    Mirrors the empty-string-is-unset semantics of ``_env_path`` (see
    ``test_settings.py`` contract for ``DOGE_US_DB``: an empty value must fall
    back to the documented default rather than raise).

    Args:
        name: Environment variable name (e.g. ``DOGE_RETENTION_DAYS``).
        default: Value returned when the var is unset or set to an empty
            string. For ``DOGE_RETENTION_DAYS`` the safe default is ``730``:
            it must be ``>= 730`` to satisfy the widest analytical-view window
            (``vw_market_breadth_cn`` uses ``INTERVAL 730 DAYS``). A value
            below 730 silently truncates breadth scans. This knob is
            **DESTRUCTIVE** — every write deletes rows older than N days per
            ticker.

    Returns:
        The integer value of the env var, or ``default``.

    Raises:
        ValueError: if the env var is set to a non-empty, non-integer string.
    """
    env = os.environ.get(name)
    if not env:
        return default
    return int(env)


@dataclass(frozen=True)
class DBConfig:
    """Database paths (override via env vars).

    ``views_sql_tracked`` (S003-005) is the **canonical, version-controlled**
    DuckDB view DDL location, shipped inside the package at
    ``src/doge/infrastructure/database/views.sql``. ``views_sql`` remains the
    data-dir mirror (``data/views.sql``, gitignored) used by the legacy
    ``duckdb data/market.duckdb < data/views.sql`` CLI invocation and as a
    backward-compat fallback. Loaders resolve the DDL via
    :meth:`resolved_views_sql` (tracked-first, data-dir fallback) so the
    version-controlled copy is always preferred when present.
    """
    dir: Path = field(default_factory=lambda: _env_path("DOGE_DB_DIR", _PROJECT_ROOT / "data"))
    cn_db: Path = field(init=False)
    us_db: Path = field(init=False)
    research_db: Path = field(init=False)
    duckdb: Path = field(init=False)
    views_sql: Path = field(init=False)
    views_sql_tracked: Path = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "cn_db", _env_path("DOGE_CN_DB", self.dir / "market_data_cn.db"))
        object.__setattr__(self, "us_db", _env_path("DOGE_US_DB", self.dir / "market_data_us.db"))
        object.__setattr__(self, "research_db", _env_path("DOGE_RESEARCH_DB", self.dir / "research_insights.db"))
        object.__setattr__(self, "duckdb", _env_path("DOGE_DUCKDB_PATH", self.dir / "market.duckdb"))
        object.__setattr__(self, "views_sql", self.dir / "views.sql")
        # Tracked, version-controlled DDL — lives with the package, not under
        # the gitignored data dir. Resolved relative to this settings module
        # (src/doge/config/settings.py -> src/doge/infrastructure/database/).
        _settings_dir = Path(__file__).resolve().parent
        object.__setattr__(
            self,
            "views_sql_tracked",
            _env_path(
                "DOGE_VIEWS_SQL_TRACKED",
                _settings_dir.parent / "infrastructure" / "database" / "views.sql",
            ),
        )

    def resolved_views_sql(self) -> Path:
        """Return the DDL path actually used by refresh loaders.

        Prefers the tracked, version-controlled DDL
        (:attr:`views_sql_tracked`) when it exists on disk; falls back to the
        data-dir mirror (:attr:`views_sql`) for backward compatibility with
        deployments that ship only ``data/views.sql``.

        Returns:
            The path whose contents the refresh path will execute. The path
            may not exist (callers should handle the missing-file case as they
            do today).
        """
        if self.views_sql_tracked.exists():
            return self.views_sql_tracked
        return self.views_sql


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
class YFinanceConfig:
    """yfinance adapter retry / window settings (S005-006 / ADR-0004).

    Canonical source of the yfinance retry policy and lookback window —
    supersedes the ``DEFAULT_MAX_RETRIES`` / ``DEFAULT_RETRY_DELAY`` /
    ``DEFAULT_PERIOD_DAYS`` module constants in
    ``doge.infrastructure.data_source.yfinance``. Those constants are kept
    as fallback defaults on the adapter constructor signature so existing
    callers that construct ``YFinanceDataSource()`` without settings continue
    to work, but the live adapter now reads from
    ``get_settings().yfinance``.

    Defaults mirror ADR-0004 item 3 (3 retries, 5s delay) and the TDX window
    parity (``period_days == 120`` matches ``TDXReader.MAX_DAYS`` so a
    yfinance refresh yields the same row count as a TDX refresh).
    """
    max_retries: int = 3
    retry_delay: float = 5.0
    period_days: int = 120


@dataclass(frozen=True)
class MarketConfig:
    """Market-related constants — the SINGLE SOURCE OF TRUTH for scanner filters.

    ``retention_days`` is the per-ticker destructive prune ceiling applied on
    every OHLCV write. It is sourced from ``DOGE_RETENTION_DAYS`` (default
    730) and MUST be ``>= 730`` to satisfy the widest analytical-view window
    (``vw_market_breadth_cn`` advertises a 730-day horizon in
    ``data/views.sql``). See ADR-0003 (Storage Repository Contract).

    Scanner-filter fields (S002-008 / TR-019): this dataclass is the canonical
    source for the Micro Momentum Scanner (Module #5) filters. The scanner reads
    these values via ``get_settings().market`` and MUST NOT consult
    ``models_config.json`` ``scanner_filters`` (that block was removed; see
    ADR-0002 and ``tests/contract/test_scanner_filter_drift_guard.py``).

    ``us_blacklist`` holds the ~52 leveraged/inverse ETF tickers the US scan
    excludes; the type is ``tuple[str, ...]`` because a frozen dataclass cannot
    hold a mutable ``list`` default. ``cn_universe_prefixes`` are the A-share
    investable-code prefixes.
    """
    whitelist: frozenset[str] = frozenset({"cn", "us"})
    cn_min_volume: int = 200_000_000
    us_min_volume: int = 20_000_000
    max_change_pct: int = 400
    rsrs_window: int = 18
    retention_days: int = field(default_factory=lambda: _env_int("DOGE_RETENTION_DAYS", 730))
    # S002-008: scanner-filter canonical values. us_blacklist is a tuple (frozen
    # dataclass constraint) — converted to a list at the MomentumRanker call
    # site so existing ``.get('us_blacklist')`` reads keep working.
    us_blacklist: tuple[str, ...] = (
        "SQQQ", "TQQQ", "SOXL", "SOXS", "SPXU", "SPXS", "SDS", "SSO", "UPRO",
        "QID", "QLD", "TNA", "TZA", "UVXY", "VIXY", "SVXY", "LABU", "LABD",
        "YANG", "YINN", "FNGU", "FNGD", "WEBL", "WEBS", "KOLD", "BOIL", "TSLY",
        "NVDY", "AMDY", "MSTY", "CONY", "APLY", "GOOY", "MSFY", "AMZY", "FBY",
        "OARK", "XOMO", "JPMO", "DISO", "NFLY", "SQY", "PYPY", "AIYY", "YMAX",
        "YMAG", "ULTY", "SVOL", "TLTW", "HYGW", "LQDW", "BITX",
    )
    # S002-008: A-share investable-code prefixes (CN whitelist root codes).
    cn_universe_prefixes: tuple[str, ...] = ("00", "30", "60", "68")


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
    yfinance: YFinanceConfig = field(default_factory=YFinanceConfig)
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
