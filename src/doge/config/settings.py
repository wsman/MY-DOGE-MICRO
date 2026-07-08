"""Centralized configuration — single source of truth for all paths, constants and env vars.

Replaces every scattered `_PROJECT_ROOT`, `_DB_DIR`, `_HERE` and `sys.path` hack.
"""

import json
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


def _env_float(name: str, default: float) -> float:
    """Read a float env var, treating unset/empty values as ``default``."""
    env = os.environ.get(name)
    if not env:
        return default
    return float(env)


def _env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean env var using common operator-friendly values."""
    env = os.environ.get(name)
    if env is None or env == "":
        return default
    return env.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Read a comma-separated env var as a tuple of non-empty strings."""
    env = os.environ.get(name)
    if not env:
        return default
    return tuple(item.strip() for item in env.split(",") if item.strip())


def parse_slot_trusted_publisher_keys(value: str | None) -> dict[str, str]:
    """Parse ``key_id=base64_public_key`` CSV pairs for slot signature trust."""
    if not value:
        return {}
    parsed: dict[str, str] = {}
    for item in value.split(","):
        raw = item.strip()
        if not raw:
            continue
        if "=" not in raw:
            raise ValueError("slot trusted publisher keys must use key_id=base64_public_key pairs")
        key_id, public_key = raw.split("=", 1)
        key_id = key_id.strip()
        public_key = public_key.strip()
        if not key_id or not public_key:
            raise ValueError("slot trusted publisher keys must use non-empty key ids and values")
        parsed[key_id] = public_key
    return parsed


def _env_slot_trusted_publisher_keys(name: str) -> dict[str, str]:
    """Read slot Ed25519 public keys from an env var."""
    return parse_slot_trusted_publisher_keys(os.environ.get(name))


def _env_json_object(name: str, default: dict) -> dict:
    """Read a JSON-object env var (e.g. HTTP headers), falling back to ``default``."""
    raw = os.environ.get(name)
    if not raw:
        return dict(default)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return dict(default)
    return parsed if isinstance(parsed, dict) else dict(default)


def _env_choice(name: str, default: str, choices: tuple[str, ...]) -> str:
    """Read an env var constrained to a small operator-facing choice set."""
    value = os.environ.get(name) or default
    normalized = value.strip().lower()
    if normalized not in choices:
        joined = ", ".join(choices)
        raise ValueError(f"{name} must be one of: {joined}")
    return normalized


def _env_json_tuple(name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Read a JSON string array env var as a tuple of strings."""
    env = os.environ.get(name)
    if not env:
        return default
    value = json.loads(env)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{name} must be a JSON array of non-empty strings")
    return tuple(value)


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
    agent_db: Path = field(init=False)
    duckdb: Path = field(init=False)
    views_sql: Path = field(init=False)
    views_sql_tracked: Path = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "cn_db", _env_path("DOGE_CN_DB", self.dir / "market_data_cn.db"))
        object.__setattr__(self, "us_db", _env_path("DOGE_US_DB", self.dir / "market_data_us.db"))
        object.__setattr__(self, "research_db", _env_path("DOGE_RESEARCH_DB", self.dir / "research_insights.db"))
        object.__setattr__(self, "agent_db", _env_path("DOGE_AGENT_DB", self.dir / "agent_state.db"))
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
class NetworkConfig:
    """Network proxy settings.

    Replaces the hardcoded ``http://127.0.0.1:7890`` proxy default in the
    legacy ``micro/industry_analyzer.py`` (S007-006). ``None`` means no proxy.
    """
    proxy: Optional[str] = field(
        default_factory=lambda: os.environ.get("DOGE_NETWORK_PROXY") or None
    )


@dataclass(frozen=True)
class DeepSeekConfig:
    """DeepSeek LLM settings.

    Mirrors the legacy ``macro/config.py`` defaults and the ``DEEPSEEK_API_KEY``
    environment migration from S002-013. All values can be overridden via env
    vars so operators do not need to edit source files.
    """
    api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("DEEPSEEK_API_KEY") or None
    )
    base_url: str = field(
        default_factory=lambda: os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1"
    )
    model: str = field(
        default_factory=lambda: os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat"
    )


@dataclass(frozen=True)
class LLMConfig:
    """Default provider selection for legacy text-only report paths."""

    text_provider: str = field(
        default_factory=lambda: os.environ.get("DOGE_TEXT_LLM_PROVIDER") or "kimi"
    )


@dataclass(frozen=True)
class KimiConfig:
    """Kimi / Moonshot agent model settings."""

    api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("MOONSHOT_API_KEY") or None
    )
    base_url: str = field(
        default_factory=lambda: os.environ.get("KIMI_BASE_URL") or "https://api.moonshot.ai/v1"
    )
    general_model: str = field(
        default_factory=lambda: os.environ.get("KIMI_GENERAL_MODEL") or "kimi-k2.6"
    )
    code_model: str = field(
        default_factory=lambda: os.environ.get("KIMI_CODE_MODEL") or "kimi-k2.7-code"
    )
    max_retries: int = field(default_factory=lambda: _env_int("KIMI_MAX_RETRIES", 2))
    retry_delay: float = field(default_factory=lambda: _env_float("KIMI_RETRY_DELAY", 1.0))
    max_completion_tokens: int = field(default_factory=lambda: _env_int("KIMI_MAX_COMPLETION_TOKENS", 16384))
    timeout_seconds: float = field(default_factory=lambda: _env_float("KIMI_TIMEOUT_SECONDS", 60.0))
    backoff_base_seconds: float = field(default_factory=lambda: _env_float("KIMI_BACKOFF_BASE_SECONDS", 1.0))
    backoff_max_seconds: float = field(default_factory=lambda: _env_float("KIMI_BACKOFF_MAX_SECONDS", 60.0))
    cost_tracking_enabled: bool = field(
        default_factory=lambda: os.environ.get("KIMI_COST_TRACKING_ENABLED", "true").lower()
        not in {"0", "false", "no", "off"}
    )
    prompt_cache_enabled: bool = field(
        default_factory=lambda: os.environ.get("KIMI_PROMPT_CACHE_ENABLED", "false").lower()
        in {"1", "true", "yes", "on"}
    )
    monthly_budget_usd: float = field(default_factory=lambda: _env_float("KIMI_MONTHLY_BUDGET_USD", 0.0))
    run_budget_usd: float = field(default_factory=lambda: _env_float("KIMI_RUN_BUDGET_USD", 0.0))
    # Kimi "For Coding" endpoint support. The coding endpoint
    # (https://api.kimi.com/coding/v1) gates on a recognized coding-agent
    # User-Agent, so coding mode also defaults the UA. Per-field env overrides
    # always win; see effective_base_url() and default_http_headers().
    base_url_explicit: bool = field(default_factory=lambda: bool(os.environ.get("KIMI_BASE_URL")))
    client_user_agent: str = field(default_factory=lambda: os.environ.get("KIMI_CLIENT_USER_AGENT") or "")
    extra_headers: dict[str, str] = field(default_factory=lambda: _env_json_object("KIMI_EXTRA_HEADERS", {}))
    coding_mode: bool = field(
        default_factory=lambda: (
            os.environ.get("KIMI_CODING_MODE", "").lower() in {"1", "true", "yes", "on"}
            or os.environ.get("DOGE_TEXT_LLM_PROVIDER", "").lower() == "kimi-coding"
        )
    )
    coding_base_url: str = field(
        default_factory=lambda: os.environ.get("KIMI_CODING_BASE_URL") or "https://api.kimi.com/coding/v1"
    )
    coding_user_agent: str = field(
        default_factory=lambda: os.environ.get("KIMI_CODING_USER_AGENT") or "claude-code/0.1.0"
    )

    def effective_base_url(self) -> str:
        """Resolve the Kimi base URL honoring explicit override > coding mode > default."""
        if self.base_url_explicit:
            return self.base_url
        if self.coding_mode:
            return self.coding_base_url
        return self.base_url

    def default_http_headers(self) -> dict[str, str]:
        """Build the OpenAI client default_headers dict (User-Agent + extras)."""
        headers: dict[str, str] = {}
        user_agent = self.client_user_agent or (self.coding_user_agent if self.coding_mode else "")
        if user_agent:
            headers["User-Agent"] = user_agent
        headers.update(self.extra_headers)
        return headers


@dataclass(frozen=True)
class DocumentConfig:
    """Uploaded document storage and validation settings."""

    storage_dir: Path = field(
        default_factory=lambda: _env_path(
            "DOGE_DOCUMENT_STORAGE_DIR",
            _env_path("DOGE_DB_DIR", _PROJECT_ROOT / "data") / "documents",
        )
    )
    max_file_bytes: int = field(
        default_factory=lambda: _env_int("DOGE_DOCUMENT_MAX_BYTES", 100 * 1024 * 1024)
    )


@dataclass(frozen=True)
class AuthConfig:
    """Enterprise authentication settings.

    ``local_demo`` preserves the existing loopback/header-driven workflow.
    ``enterprise`` fails closed unless a bearer provider is configured. The
    static bearer fields are a local fixture path only; production OIDC/JWKS is
    tracked in S017 and must replace it before declaring enterprise readiness.
    """

    mode: str = field(
        default_factory=lambda: (os.environ.get("DOGE_AUTH_MODE") or "local_demo").strip().lower()
    )
    oidc_issuer: Optional[str] = field(default_factory=lambda: os.environ.get("DOGE_AUTH_OIDC_ISSUER") or None)
    oidc_audience: Optional[str] = field(default_factory=lambda: os.environ.get("DOGE_AUTH_OIDC_AUDIENCE") or None)
    oidc_jwks_url: Optional[str] = field(default_factory=lambda: os.environ.get("DOGE_AUTH_OIDC_JWKS_URL") or None)
    oidc_algorithms: tuple[str, ...] = field(
        default_factory=lambda: _env_csv("DOGE_AUTH_OIDC_ALGORITHMS", ("RS256",))
    )
    clock_skew_seconds: int = field(default_factory=lambda: _env_int("DOGE_AUTH_CLOCK_SKEW_SECONDS", 60))
    subject_claim: str = field(default_factory=lambda: os.environ.get("DOGE_AUTH_SUBJECT_CLAIM") or "sub")
    tenant_claim: str = field(default_factory=lambda: os.environ.get("DOGE_AUTH_TENANT_CLAIM") or "tenant_id")
    roles_claim: str = field(default_factory=lambda: os.environ.get("DOGE_AUTH_ROLES_CLAIM") or "roles")
    entitlements_claim: str = field(
        default_factory=lambda: os.environ.get("DOGE_AUTH_ENTITLEMENTS_CLAIM") or "entitlements"
    )
    approval_authority_claim: str = field(
        default_factory=lambda: os.environ.get("DOGE_AUTH_APPROVAL_AUTHORITY_CLAIM") or "approval_authority"
    )
    project_claim: str = field(default_factory=lambda: os.environ.get("DOGE_AUTH_PROJECT_CLAIM") or "project_id")
    static_bearer_token: Optional[str] = field(
        default_factory=lambda: os.environ.get("DOGE_AUTH_STATIC_BEARER_TOKEN") or None
    )
    static_subject: str = field(default_factory=lambda: os.environ.get("DOGE_AUTH_STATIC_SUBJECT") or "local-subject")
    static_tenant_id: str = field(default_factory=lambda: os.environ.get("DOGE_AUTH_STATIC_TENANT_ID") or "local")
    static_roles: tuple[str, ...] = field(default_factory=lambda: _env_csv("DOGE_AUTH_STATIC_ROLES", ("analyst",)))
    static_entitlements: tuple[str, ...] = field(default_factory=lambda: _env_csv("DOGE_AUTH_STATIC_ENTITLEMENTS"))
    static_document_acl: tuple[str, ...] = field(default_factory=lambda: _env_csv("DOGE_AUTH_STATIC_DOCUMENT_ACL"))
    static_portfolio_permission: tuple[str, ...] = field(
        default_factory=lambda: _env_csv("DOGE_AUTH_STATIC_PORTFOLIO_PERMISSION")
    )
    static_approval_authority: tuple[str, ...] = field(
        default_factory=lambda: _env_csv("DOGE_AUTH_STATIC_APPROVAL_AUTHORITY")
    )
    static_data_classification: str = field(
        default_factory=lambda: os.environ.get("DOGE_AUTH_STATIC_DATA_CLASSIFICATION") or "internal"
    )
    static_project_id: str = field(default_factory=lambda: os.environ.get("DOGE_AUTH_STATIC_PROJECT_ID") or "doge-dev")


@dataclass(frozen=True)
class APIConfig:
    """API bind and CORS posture.

    The default remains loopback-only with permissive CORS. Non-loopback bind is
    a deliberate promotion gate and requires enterprise auth, explicit CORS
    origins, and TLS termination acknowledgement. Legacy ``/api/*`` business
    routers are local-demo compatibility surfaces only; enterprise and
    non-loopback deployments fail closed by not mounting them.
    """

    bind_host: str = field(default_factory=lambda: os.environ.get("DOGE_BIND_HOST") or "127.0.0.1")
    cors_allow_origins: tuple[str, ...] = field(
        default_factory=lambda: _env_csv("DOGE_CORS_ALLOW_ORIGINS", ("*",))
    )
    allow_remote_bind: bool = field(default_factory=lambda: _env_bool("DOGE_ALLOW_REMOTE_BIND", False))
    tls_termination_required: bool = field(
        default_factory=lambda: _env_bool("DOGE_API_TLS_TERMINATION_REQUIRED", False)
    )
    enterprise_disable_legacy: bool = field(
        default_factory=lambda: _env_bool("DOGE_API_ENTERPRISE_DISABLE_LEGACY", True)
    )


@dataclass(frozen=True)
class DaemonConfig:
    """Loopback daemon gateway defaults."""

    port: int = field(default_factory=lambda: _env_int("DOGE_DAEMON_PORT", 8901))
    process_role: str = field(default_factory=lambda: _env_choice("DOGE_PROCESS_ROLE", "all", ("api", "worker", "all")))


@dataclass(frozen=True)
class AuditConfig:
    """Enterprise audit retention settings.

    The local SQLite implementation enforces retention per tenant through the
    audit administration API. Production deployments still need an external
    operational review before audit controls can be considered complete.
    """

    retention_days: int = field(default_factory=lambda: _env_int("DOGE_AUDIT_RETENTION_DAYS", 365))


@dataclass(frozen=True)
class SecretConfig:
    """Secret provider selection.

    ``env`` preserves local-first defaults. ``process`` is the production
    integration boundary for an operator-managed KMS, Vault, cloud secret
    manager, or sidecar wrapper without embedding cloud SDK dependencies in the
    application.
    """

    provider: str = field(
        default_factory=lambda: (os.environ.get("DOGE_SECRET_PROVIDER") or "env").strip().lower()
    )
    process_command: tuple[str, ...] = field(
        default_factory=lambda: _env_json_tuple("DOGE_SECRET_PROCESS_COMMAND_JSON")
    )
    process_timeout_seconds: float = field(
        default_factory=lambda: _env_float("DOGE_SECRET_PROCESS_TIMEOUT_SECONDS", 5.0)
    )
    allowed_names: tuple[str, ...] = field(
        default_factory=lambda: _env_csv(
            "DOGE_SECRET_ALLOWED_NAMES",
            (
                "kimi.api_key",
                "deepseek.api_key",
                "auth.static_bearer_token",
                "slot.trusted_publisher_keys",
            ),
        )
    )


@dataclass(frozen=True)
class FeatureLifecycle:
    """Lifecycle metadata for migration feature flags."""

    env_var: str
    introduced: str
    current_default: bool
    target_default_on: str
    target_removal: str
    replacement_behavior: str
    regression_commands: tuple[str, ...]
    rollback_criterion: str


FEATURE_LIFECYCLES: dict[str, FeatureLifecycle] = {
    "run_summary_api": FeatureLifecycle(
        env_var="DOGE_FEATURE_RUN_SUMMARY_API",
        introduced="platformization Phase B; docs/progress/platformization-consolidation-baseline.md",
        current_default=False,
        target_default_on="after ADR-0017 evidence and citation/eval API regressions are green",
        target_removal="one release cycle after default-on with approved API/SDK compatibility removal story",
        replacement_behavior="/v1/runs/{run_id}/summary, claims, citations, and eval are always available",
        regression_commands=(
            "python -m pytest tests/contract/test_run_summary_api.py tests/contract/test_v1_api.py -q",
        ),
        rollback_criterion="restore default False if run-summary contract tests fail or consumers report API breakage",
    ),
    "platform_objects": FeatureLifecycle(
        env_var="DOGE_FEATURE_PLATFORM_OBJECTS",
        introduced="platformization Phase B; docs/progress/platformization-consolidation-baseline.md",
        current_default=False,
        target_default_on="after ADR-0016 evidence and platform object contract regressions are green",
        target_removal="one release cycle after default-on with approved legacy workspace compatibility removal story",
        replacement_behavior="workspace, project, research-case, and case-run APIs are always available",
        regression_commands=(
            "python -m pytest tests/contract/test_platform_api.py tests/contract/test_python_sdk.py -q",
        ),
        rollback_criterion="restore default False if platform object contracts fail or existing consumers break",
    ),
    "workflow_templates": FeatureLifecycle(
        env_var="DOGE_FEATURE_WORKFLOW_TEMPLATES",
        introduced="platformization Phase B; docs/progress/platformization-consolidation-baseline.md",
        current_default=True,
        target_default_on="after ADR-0018 preflight and template-created run regressions are green",
        target_removal="one release cycle after default-on with approved workflow-template compatibility removal story",
        replacement_behavior="workflow template listing, creation, lookup, and case-run creation are always available",
        regression_commands=(
            "python -m pytest tests/contract/test_platform_api.py tests/unit/infrastructure/test_platform_repository.py -q",
        ),
        rollback_criterion="restore default False if template APIs or template-created run flows regress",
    ),
    "capability_registry": FeatureLifecycle(
        env_var="DOGE_FEATURE_CAPABILITY_REGISTRY",
        introduced="platformization Phase C; docs/archive/audits/platformization-consolidation-phase-c-2026-06-23.md",
        current_default=False,
        target_default_on="first defaultization candidate after ADR-0019 review and capability regressions are green",
        target_removal="one release cycle after default-on with approved provider-registry compatibility removal story",
        replacement_behavior="capability discovery and provider-backed tool execution are always registry-backed",
        regression_commands=(
            "python -m pytest tests/unit/use_cases/test_capability_registry.py tests/contract/test_platform_api.py tests/unit/capabilities -q",
        ),
        rollback_criterion="restore default False if capability discovery, redaction, or provider parity regresses",
    ),
    "runtime_outbox_publisher": FeatureLifecycle(
        env_var="DOGE_FEATURE_RUNTIME_OUTBOX_PUBLISHER",
        introduced="P0-03 runtime transaction/outbox remediation; C:\\Users\\Aby\\.claude\\plans\\my-doge-micro-main-2ffdb66-piped-donut.md",
        current_default=False,
        target_default_on="after P0-05 replaces in-process EventBus correctness with cross-process subscriber coverage",
        target_removal="one release cycle after SSE and daemon event delivery no longer depend on immediate publish",
        replacement_behavior="runtime events are delivered from the transactional outbox publisher by default",
        regression_commands=(
            "python -m pytest tests/unit/agent/test_runtime_transaction.py tests/integration/test_agent_sse_stream.py -q",
        ),
        rollback_criterion="restore default False if event delivery duplicates or misses runtime events",
    ),
    "python_analysis_enabled": FeatureLifecycle(
        env_var="DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED",
        introduced="P0-07 Python analysis executor boundary; C:\\Users\\Aby\\.claude\\plans\\my-doge-micro-main-2ffdb66-piped-donut.md",
        current_default=False,
        target_default_on="never for enterprise deployments without a hardened non-subprocess executor",
        target_removal="after Python analysis is replaced by a hardened container or WASM executor with approval workflow evidence",
        replacement_behavior="Python analysis tools execute only through an operator-selected hardened code executor",
        regression_commands=(
            "python -m pytest tests/unit/capabilities/test_code_executor.py tests/unit/agent/test_tool_registry.py tests/unit/use_cases/test_capability_registry.py -q",
        ),
        rollback_criterion="restore default False and disabled executor if Python analysis can execute without explicit operator enablement",
    ),
    "slot_platform": FeatureLifecycle(
        env_var="DOGE_FEATURE_SLOT_PLATFORM",
        introduced="Sprint 033 Slot Platform Foundation; docs/architecture/adr-0042-slot-platform.md",
        current_default=True,
        target_default_on="after ADR-0042 parity evidence and full regression are green",
        target_removal="one release cycle after slot-backed tool registration is byte-equivalent to the legacy path with an approved removal story",
        replacement_behavior="built-in tool/model slots register their contributions through the SlotRegistry",
        regression_commands=(
            "python -m pytest tests/unit/platform/slots tests/unit/architecture/test_slot_boundary.py tests/cli/test_cli_slots.py tests/contract/test_tool_registry_slot_parity.py -q",
        ),
        rollback_criterion="restore default False if /v1/tools payload or tool execution differs from the flag-off baseline",
    ),
    "slot_governance": FeatureLifecycle(
        env_var="DOGE_FEATURE_SLOT_GOVERNANCE",
        introduced="Sprint 037 Governance Slot Consumer; docs/architecture/adr-0046-governance-slot-consumer.md",
        current_default=True,
        target_default_on="after governance-slot entitlement parity and enterprise tool-governance regressions are green",
        target_removal="one release cycle after governance slot policy composition is always-on with an approved removal story",
        replacement_behavior="tool entitlement and approval policies are always composed through governance slots",
        regression_commands=(
            "python -m pytest tests/unit/platform/slots/test_builtin_governance_slot.py tests/contract/test_governance_slot_parity.py tests/contract/test_tool_registry_slot_parity.py -q",
        ),
        rollback_criterion="restore default False if tool schema redaction, approval metadata, or execution permissions differ unexpectedly",
    ),
    "slot_watcher": FeatureLifecycle(
        env_var="DOGE_FEATURE_SLOT_WATCHER",
        introduced="Sprint 038 Watcher Slot Consumer; docs/architecture/adr-0047-watcher-slot-consumer.md",
        current_default=True,
        target_default_on="after watcher-slot event parity and runtime rollback regressions are green",
        target_removal="one release cycle after watcher middleware is always-on with an approved removal story",
        replacement_behavior="runtime events are always observed by slot-contributed watcher middleware",
        regression_commands=(
            "python -m pytest tests/unit/platform/slots/test_builtin_watcher_slot.py tests/contract/test_watcher_slot_parity.py tests/unit/agent/test_transition_recorder.py -q",
        ),
        rollback_criterion="restore default False if runtime event persistence, outbox staging, or publishing differs unexpectedly",
    ),
    "slot_ui": FeatureLifecycle(
        env_var="DOGE_FEATURE_SLOT_UI",
        introduced="Sprint 044 UI Slot Consumer; docs/architecture/adr-0053-ui-slot-consumer.md",
        current_default=False,
        target_default_on="after ResearchAgentView panel-registry parity and web regressions are green",
        target_removal="one release cycle after UI panel slot metadata is always-on with an approved static-layout removal story",
        replacement_behavior="Research workspace panels are always described by UI slot contributions",
        regression_commands=(
            "python -m pytest tests/unit/platform/slots/test_builtin_ui_slot.py tests/contract/test_slot_ui_registry.py tests/contract/test_slot_api.py -q",
            "cd web && npm run test -- src/views/panelRegistry.spec.ts src/views/ResearchAgentView.spec.ts src/stores/platform.spec.ts",
        ),
        rollback_criterion="restore default False if ResearchAgentView panel visibility, ordering, accessibility, or build output regresses",
    ),
    "slot_enforcement": FeatureLifecycle(
        env_var="DOGE_FEATURE_SLOT_ENFORCEMENT",
        introduced="Sprint 045 Runtime Permission and Health Enforcement; docs/architecture/adr-0055-slot-enforcement.md",
        current_default=False,
        target_default_on="after slot permission/health enforcement parity and denied-slot regressions are green",
        target_removal="one release cycle after slot permission and health enforcement is always-on with an approved removal story",
        replacement_behavior="slot permissions and active health probes are always enforced by SlotKernel before contribution resolve/start",
        regression_commands=(
            "python -m pytest tests/unit/platform/slots/test_slot_enforcement.py tests/unit/platform/slots/test_slot_kernel.py tests/contract/test_tool_registry_slot_parity.py -q",
        ),
        rollback_criterion="restore default False if slot resolution, tool registration, or health diagnostics differ unexpectedly",
    ),
    "slot_runtime_interception": FeatureLifecycle(
        env_var="DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION",
        introduced="P4 Slot Runtime Permission Interception; docs/architecture/adr-0063-slot-runtime-permission-interception.md",
        current_default=False,
        target_default_on="after in-process db/secret/network guard parity and violation-audit regressions are green",
        target_removal="after slot runtime resource mediation is always-on or replaced by a hardened P5 sandbox executor",
        replacement_behavior="built-in slot calls run with in-process db, secret, and network guards derived from SlotPermissions",
        regression_commands=(
            "python -m pytest tests/unit/platform/slots/test_slot_runtime_access.py tests/unit/capabilities/test_code_executor.py tests/test_settings.py tests/unit/use_cases/test_capability_registry.py -q",
        ),
        rollback_criterion="restore default False if built-in slot execution, audit emission, or legacy no-context execution regresses",
    ),
    "slot_loader": FeatureLifecycle(
        env_var="DOGE_FEATURE_SLOT_LOADER",
        introduced="Sprint 046 SlotLoader and Bundle Activation; docs/architecture/adr-0056-slot-loader-bundle-activation.md",
        current_default=True,
        target_default_on="after disk manifest loading and bundle activation parity regressions are green",
        target_removal="one release cycle after JSON slot manifest loading and bundle activation are always-on with an approved removal story",
        replacement_behavior="validated JSON slot manifests and persisted active bundle policy overlays are available through SlotKernel",
        regression_commands=(
            "python -m pytest tests/unit/platform/slots/test_slot_loader.py tests/unit/platform/slots/test_slot_activation.py tests/unit/infrastructure/test_slot_activation_repository.py tests/integration/test_slot_bundle_activation_persistence.py tests/contract/test_slot_kernel_bundle_rows.py tests/contract/test_slot_api.py tests/cli/test_cli_slots.py -q",
        ),
        rollback_criterion="restore default False if slot discovery, bundle activation, or built-in slot parity differs unexpectedly",
    ),
    "slot_install": FeatureLifecycle(
        env_var="DOGE_FEATURE_SLOT_INSTALL",
        introduced="Sprint 047 Third-party Slot Install Preview; docs/architecture/adr-0057-third-party-slot-install-preview.md",
        current_default=False,
        target_default_on="after manifest install, Ed25519 signature, revocation, and enterprise allowlist regressions are green",
        target_removal="one release cycle after local slot install preview is always-on with an approved removal story",
        replacement_behavior="validated third-party slot manifests can be installed as manifest-only local slots",
        regression_commands=(
            "python -m pytest tests/unit/platform/slots/test_slot_install.py tests/cli/test_cli_slots.py -q",
        ),
        rollback_criterion="restore default False if local install writes, cryptographic signature checks, revocation, or enterprise allowlist behavior differ unexpectedly",
    ),
    "slot_provider_execution": FeatureLifecycle(
        env_var="DOGE_FEATURE_SLOT_PROVIDER_EXECUTION",
        introduced="P5 Slot Provider Execution; docs/architecture/adr-0064-slot-provider-execution.md",
        current_default=False,
        target_default_on="never before trusted-provider execution has external security review, hardened isolation, and full operator rollback evidence",
        target_removal="after provider execution is replaced by or promoted behind a hardened container/WASM/OS sandbox with approved production gates",
        replacement_behavior="installed trusted-publisher slots may import an in-process ISlot entrypoint only after all local alpha gates pass",
        regression_commands=(
            "python -m pytest tests/unit/platform/slots/test_slot_provider_execution.py tests/test_settings.py tests/unit/use_cases/test_capability_registry.py tests/cli/test_cli_slots.py tests/contract/test_slot_api.py -q",
        ),
        rollback_criterion="restore default False and unregister InstalledProviderSlot if any untrusted, unsigned, revoked, non-intercepted, or restricted-facet provider can execute",
    ),
}


@dataclass(frozen=True)
class FeatureConfig:
    """Feature flags for experimental platformization surfaces."""

    run_summary_api: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_RUN_SUMMARY_API", False)
    )
    platform_objects: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_PLATFORM_OBJECTS", False)
    )
    workflow_templates: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_WORKFLOW_TEMPLATES", True)
    )
    capability_registry: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_CAPABILITY_REGISTRY", False)
    )
    runtime_outbox_publisher: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_RUNTIME_OUTBOX_PUBLISHER", False)
    )
    python_analysis_enabled: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED", False)
    )
    slot_platform: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_SLOT_PLATFORM", True)
    )
    slot_governance: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_SLOT_GOVERNANCE", True)
    )
    slot_watcher: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_SLOT_WATCHER", True)
    )
    slot_ui: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_SLOT_UI", False)
    )
    slot_enforcement: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_SLOT_ENFORCEMENT", False)
    )
    slot_runtime_interception: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION", False)
    )
    slot_loader: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_SLOT_LOADER", True)
    )
    slot_install: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_SLOT_INSTALL", False)
    )
    slot_provider_execution: bool = field(
        default_factory=lambda: _env_bool("DOGE_FEATURE_SLOT_PROVIDER_EXECUTION", False)
    )
    python_analysis_executor: str = field(
        default_factory=lambda: (os.environ.get("DOGE_PYTHON_ANALYSIS_EXECUTOR") or "disabled").strip().lower()
    )


@dataclass(frozen=True)
class SlotConfig:
    """Slot Platform local manifest configuration."""

    manifest_dirs: tuple[Path, ...] = field(
        default_factory=lambda: tuple(Path(item) for item in _env_csv("DOGE_SLOT_MANIFEST_DIRS"))
    )
    install_dir: Path = field(
        default_factory=lambda: _env_path("DOGE_SLOT_INSTALL_DIR", _PROJECT_ROOT / "data" / "slots")
    )
    enterprise_allowlist: tuple[str, ...] = field(
        default_factory=lambda: _env_csv("DOGE_SLOT_ENTERPRISE_ALLOWLIST")
    )
    trusted_signers: tuple[str, ...] = field(
        default_factory=lambda: _env_csv("DOGE_SLOT_TRUSTED_SIGNERS")
    )
    trusted_publisher_keys: dict[str, str] = field(
        default_factory=lambda: _env_slot_trusted_publisher_keys("DOGE_SLOT_TRUSTED_PUBLISHER_KEYS")
    )
    allow_unsigned_local: bool = field(
        default_factory=lambda: _env_bool("DOGE_SLOT_ALLOW_UNSIGNED_LOCAL", True)
    )


@dataclass(frozen=True)
class Settings:
    """Application settings container."""
    project_root: Path = _PROJECT_ROOT
    db: DBConfig = field(default_factory=DBConfig)
    tdx: TDXConfig = field(default_factory=TDXConfig)
    yfinance: YFinanceConfig = field(default_factory=YFinanceConfig)
    market: MarketConfig = field(default_factory=MarketConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    deepseek: DeepSeekConfig = field(default_factory=DeepSeekConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    kimi: KimiConfig = field(default_factory=KimiConfig)
    documents: DocumentConfig = field(default_factory=DocumentConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    api: APIConfig = field(default_factory=APIConfig)
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    secrets: SecretConfig = field(default_factory=SecretConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    slots: SlotConfig = field(default_factory=SlotConfig)

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
