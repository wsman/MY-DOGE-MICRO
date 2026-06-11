# CDD: Runtime Configuration (Module #1)

> **Module**: Runtime Configuration
> **Slug**: `runtime-configuration`
> **Category**: Foundation
> **Priority**: MVP
> **Status**: In Progress (brownfield reverse-documentation)
> **Depends On**: None
> **Depended On By**: `market-data-storage` (#2), `data-sources` (#3), `mcp-server` (#8), `fastapi-service` (#9), `clean-architecture-migration` (#12)
> **Source Truth**: `src/doge/config/settings.py`
> **Governance**: ADR-0002 (centralized-configuration) + ADR-0001 (brownfield-clean-architecture)

---

## 1. Overview

Runtime Configuration is the Foundation module that owns the single source of truth for all paths, environment-variable overrides, database locations, TDX server endpoints, market-analysis constants, and MCP transport settings across MY-DOGE-MICRO. It is implemented as a set of frozen `dataclass` containers in `src/doge/config/settings.py`, exposed through a lazy singleton (`get_settings()`). The module exists to retire the brownfield pattern of every legacy file independently recomputing `_PROJECT_ROOT` via `os.path.dirname` chains and inserting into `sys.path` (see ADR-0001 forbidden_patterns: `sys_path_insert`, `_PROJECT_ROOT_recalculation`). New clean-architecture code under `src/doge/` imports paths only from `doge.config.get_settings()`; legacy modules under `src/micro/`, `src/macro/`, `src/api/routers/`, and `src/interface/` still recalculate their own roots and are documented here as the "Current State (Migration)" track that `clean-architecture-migration` (#12) is responsible for retiring.

---

## 2. User Promise / JTBD

**Job to be done**: As an operator (or as a downstream module author), I need one reliable, predictable place that tells me where every database lives, which environment variable overrides it, and what the configured limits/defaults are — so that I can (a) point the tool at a different data directory, (b) configure TDX endpoints or MCP transport, and (c) write new modules without re-deriving the project root or hardcoding paths.

**Promise the module keeps**:
- Importing `from doge.config import get_settings` and reading `get_settings().db.cn_db` returns the *correct* path in every environment, honoring `DOGE_CN_DB` / `DOGE_DB_DIR` overrides, with no `sys.path` mutation and no per-file root recalculation.
- Every env var the module honors is documented with its default, valid range, and ownership (Section 7).
- The configuration object is immutable (`frozen=True`) and cheap; the singleton is resettable for tests.

**Promise the module does NOT yet keep** (open questions, Section 9):
- It does not yet own LLM/model configuration — `src/macro/config.py` (`MacroConfig`) still reads `models_config.json` + `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` env vars independently.
- It does not yet validate env-var values (e.g. port ranges, path writability); invalid values surface as runtime errors at first use, not at settings construction.

---

## 3. Detailed Behavior

### 3.1 Source of truth

All settings live in **`src/doge/config/settings.py`** (the canonical file for this CDD). Public surface:

- `Settings` — top-level frozen dataclass container.
- `DBConfig`, `TDXConfig`, `MarketConfig`, `MCPConfig` — nested frozen dataclasses grouped by concern.
- `get_settings() -> Settings` — lazy module-level singleton (`src/doge/config/settings.py:107-112`).
- `reset_settings() -> None` — clears the singleton; test-only helper (`src/doge/config/settings.py:115-118`).
- Re-exported from `src/doge/config/__init__.py` as `Settings`, `get_settings`.

### 3.2 Project-root detection (single source)

`_PROJECT_ROOT` is computed once at module import, three parents up from `settings.py` (`src/doge/config/settings.py:15`):

```python
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
```

This is the **only sanctioned** project-root calculation in the new architecture. It is the value of `get_settings().project_root` (`src/doge/config/settings.py:79`). ADR-0001 lists per-file `_PROJECT_ROOT_recalculation` as a forbidden pattern.

### 3.3 Environment override helper

All env-overridable paths funnel through one helper (`src/doge/config/settings.py:18-20`):

```python
def _env_path(name: str, default: Path) -> Path:
    env = os.environ.get(name)
    return Path(env) if env else default
```

Semantics: if the named env var is set and non-empty, `Path(env)` wins (even if that path does not exist — no existence check is performed). Otherwise the default is used.

### 3.4 Database paths (`DBConfig`, `src/doge/config/settings.py:23-38`)

`DBConfig.dir` is resolved first from `DOGE_DB_DIR` (default `<root>/data`), then the four database paths and one SQL file are derived relative to `dir` unless individually overridden:

| Field | Env var | Default (relative to `dir`) |
|-------|---------|------------------------------|
| `dir` | `DOGE_DB_DIR` | `<project_root>/data` |
| `cn_db` | `DOGE_CN_DB` | `<dir>/market_data_cn.db` |
| `us_db` | `DOGE_US_DB` | `<dir>/market_data_us.db` |
| `research_db` | `DOGE_RESEARCH_DB` | `<dir>/research_insights.db` |
| `duckdb` | `DOGE_DUCKDB_PATH` | `<dir>/market.duckdb` |
| `views_sql` | *(none — derived)* | `<dir>/views.sql` |

Because the dataclass is `frozen=True`, the derived fields are set in `__post_init__` via `object.__setattr__` (`src/doge/config/settings.py:33-38`). This means `DOGE_DB_DIR` is consulted once during `DBConfig()` construction; per-file overrides of `DOGE_CN_DB` etc. are resolved *relative to the already-resolved* `self.dir`.

### 3.5 TDX settings (`TDXConfig`, `src/doge/config/settings.py:41-54`)

Hardcoded (not env-overridable) TDX server pools and ports:

- `cn_servers` — tuple of 5 CN TDX host IPs (port 7709).
- `us_servers` — tuple of 5 US TDX host IPs (port 7727).
- `cn_port: int = 7709`, `us_port: int = 7727`.
- `timeout: int = 5` (seconds, per server connection attempt).

### 3.6 Market constants (`MarketConfig`, `src/doge/config/settings.py:57-64`)

- `whitelist: frozenset[str] = {"cn", "us"}` — the only accepted `market` values.
- `cn_min_volume: int = 200_000_000` — CN market-cap/volume floor for screening (RMB).
- `us_min_volume: int = 20_000_000` — US equivalent (USD).
- `max_change_pct: int = 400` — sanity cap on per-bar change percent (used to reject bad ticks).
- `rsrs_window: int = 18` — default RSRS regression window. (The RSRS *formula* itself is owned by `micro-momentum-scanner` #5, `src/micro/momentum_scanner.py:47-71`; this setting only carries the window default.)

### 3.7 MCP settings (`MCPConfig`, `src/doge/config/settings.py:67-73`)

- `tool_timeout: int = 30` — the documented MCP common-query budget (matches `standards/technical-preferences.md` "MCP Tool Latency: within 30 seconds").
- `stdio_transport: str = "stdio"`.
- `sse_host: str = "127.0.0.1"`.
- `sse_port: int = 8902`.

### 3.8 Derived path properties (`Settings`, `src/doge/config/settings.py:86-100`)

- `report_dir` -> `<project_root>/ai_report` (computed, not env-overridable).
- `data_dir` -> alias for `db.dir`.
- `stock_names_csv` -> `<data_dir>/stock_names_cn.csv`.
- `catalog_json` -> `<data_dir>/catalog.json`.

### 3.9 Singleton lifecycle

`get_settings()` constructs `Settings()` exactly once and caches it in the module-global `_settings` (`src/doge/config/settings.py:104-112`). `reset_settings()` nulls the cache so tests can re-instantiate under a different env (`:115-118`). The dataclasses are `frozen=True`, so callers cannot mutate; tests that need different paths must set env vars **before** the first `get_settings()` call (or call `reset_settings()`).

### 3.10 Consumers (clean-architecture side)

These modules already import paths only from `get_settings()` (no local root recalculation):
- `src/doge/interfaces/mcp/server.py:23,34` (logging dir).
- `src/doge/infrastructure/database/sqlite.py:11,18`.
- `src/doge/infrastructure/database/duckdb.py:13,24`.
- `src/doge/infrastructure/database/repositories.py:10,49,87`.
- `src/doge/infrastructure/cache/ticker_cache.py:11,19`.

### 3.11 Current State (Migration): legacy recalculation NOT yet retired

The following files still compute their own `_PROJECT_ROOT` / `project_root` via `os.path.dirname` chains and/or `sys.path.insert`. These are the brownfield offenders ADR-0001 forbids and `clean-architecture-migration` (#12) will retire. Cited for traceability — **do not add new ones**:

| File | Pattern | Lines |
|------|---------|-------|
| `src/micro/tdx_downloader.py` | `_PROJECT_ROOT` + `sys.path.insert` x2 | `:23-26` |
| `src/micro/market_scanner.py` | `_PROJECT_ROOT` + `sys.path.insert` + `current_dir` | `:9, :24-26` |
| `src/micro/momentum_scanner.py` | `current_dir` + `project_root` recalc | `:12-13` |
| `src/micro/industry_analyzer.py` | `current_dir`/`src_dir`/`project_root` + `sys.path.insert` | `:12-17` |
| `src/micro/database.py` | `os.path.join(os.path.dirname(...) x3, 'data', ...)` for `research_insights.db`; `project_root` recalc | `:217, :260, :435-436` |
| `src/api/main.py` | `_PROJECT_ROOT` + `data_dir` join | `:9, :48` |
| `src/api/routers/scan.py` | `_PROJECT_ROOT` (4x dirname) + db/csv joins | `:17, :152, :162` |
| `src/api/routers/macro.py` | `_PROJECT_ROOT` (4x dirname) + db joins x3 | `:13, :26, :42, :59` |
| `src/api/routers/data.py` | `_PROJECT_ROOT` (4x dirname) + db-path dict | `:11, :14-16, :157` |
| `src/api/routers/config.py` | `_PROJECT_ROOT` (4x dirname) + config json joins | `:11, :31, :38, :49` |
| `src/api/routers/analysis.py` | `_PROJECT_ROOT` (4x dirname) + db joins | `:8, :16, :31` |
| `src/macro/config.py` | `current_dir`/`project_root` recalc + `models_config.json` | `:102-105` |
| `src/macro/cli.py` | `sys.path.insert` | `:12` |
| `src/ai_analysis/__init__.py` | `PROJECT_ROOT = Path(__file__).resolve().parents[2]` + duplicated `_env_path` for the same `DOGE_*` env vars | `:21, :24-36` |
| `src/ai_analysis/anomaly_detection.py`, `fetch_names.py`, `catalog_generator.py`, `stock_notes.py`, `market_overview.py` | `sys.path.insert` | `:13/:16/:12/:13/:15` |
| `src/interface/scanner_gui.py` | `interface_dir`/`src_dir`/`project_root` + `sys.path` x2 + db joins | `:11-17, :75, :200, :296` |
| `src/interface/dashboard.py` | `current_dir` + db joins x3 + `sys.path.append` | `:22, :64-76, :125` |
| `src/interface/analysis_gui.py` | `current_dir`/`project_root` + sets `DEEPSEEK_*` env | `:11-12, :31-32` |
| `src/cli.py` | `sys.path.insert` | `:15` |

**Notable dual-implementation**: `src/ai_analysis/__init__.py:24-36` reimplements the *exact same* `_env_path` helper and `DOGE_DB_DIR/DOGE_CN_DB/DOGE_US_DB/DOGE_RESEARCH_DB/DOGE_DUCKDB_PATH` reading as `settings.py`. This is a parallel foundation path that must collapse into `get_settings()` during migration (see open questions).

### 3.12 Current State (Migration): thread-limit env shims

Three modules force `OPENBLAS_NUM_THREADS=1` / `OMP_NUM_THREADS=1` via `os.environ.setdefault(...)` at import time to prevent OOM during pandas/BLAS DataFrame conversions:
- `src/ai_analysis/__init__.py:15-16`
- `src/api/main.py:12-13`
- `src/doge/infrastructure/database/duckdb.py:16-17`

These are process-global side effects, not part of `Settings`. They are documented here but intentionally **not** centralized in `settings.py` (open question: should they be?).

---

## 4. Contracts / Data Model

### 4.1 Public API

```python
# src/doge/config/__init__.py — re-exports ONLY Settings and get_settings
# (verified: __all__ = ["Settings", "get_settings"])
from doge.config import Settings, get_settings          # the supported public import

# reset_settings is NOT re-exported by __init__.py. Import it directly from
# the settings module (test-only helper, src/doge/config/settings.py:115-118):
from doge.config.settings import reset_settings          # test-only; not public surface

# Construction
def get_settings() -> Settings: ...        # lazy singleton
def reset_settings() -> None: ...          # test helper

# Shape (all frozen dataclasses)
@dataclass(frozen=True) class DBConfig:    dir: Path; cn_db: Path; us_db: Path; research_db: Path; duckdb: Path; views_sql: Path
@dataclass(frozen=True) class TDXConfig:   cn_servers: tuple[str,...]; us_servers: tuple[str,...]; cn_port: int; us_port: int; timeout: int
@dataclass(frozen=True) class MarketConfig: whitelist: frozenset[str]; cn_min_volume: int; us_min_volume: int; max_change_pct: int; rsrs_window: int
@dataclass(frozen=True) class MCPConfig:   tool_timeout: int; stdio_transport: str; sse_host: str; sse_port: int
@dataclass(frozen=True) class Settings:    project_root: Path; db: DBConfig; tdx: TDXConfig; market: MarketConfig; mcp: MCPConfig
                                           # + properties: report_dir, data_dir, stock_names_csv, catalog_json
```

### 4.2 Inputs

- Environment variables (Section 7 enumerates all): `DOGE_DB_DIR`, `DOGE_CN_DB`, `DOGE_US_DB`, `DOGE_RESEARCH_DB`, `DOGE_DUCKDB_PATH`.
- No CLI args, no config files read by `settings.py`. (JSON config is a *separate* concern owned by `src/macro/config.py`.)
- **NOTE (Current State — contract caveat)**: the same 5 env vars are read a SECOND time by `src/ai_analysis/__init__.py:24-36` at that module's import (module-global constants resolved at `ai_analysis` import time), while the `settings.py` reader is a lazy singleton resolved at first `get_settings()`. Two parallel `Paths` objects can therefore coexist in one process and **diverge** if env vars are set after one of the two modules is imported. See §3.11 / §9.8 for the migration-collapse plan.

### 4.3 Outputs / return types

- `Path` instances (always concrete `pathlib.Path`, never strings). Callers that need a string must call `str(...)` or `.as_posix()` (e.g. DuckDB `ATTACH` uses `CN_DB.as_posix()` in `src/ai_analysis/__init__.py:80`).
- `int` for ports/timeouts/windows/volumes.
- `tuple[str, ...]` / `frozenset[str]` for immutable collections.

### 4.4 Error behavior

- `settings.py` performs **no validation and no existence checks**. Outcomes on bad input:
  - Env var pointing at a non-existent or non-writable directory -> silent at construction; surfaces as `sqlite3.OperationalError` / `duckdb.IOException` at first DB write.
  - Env var with a syntactically malformed path -> `Path()` accepts almost anything; bad chars surface only when the OS API rejects them.
  - Non-numeric value where an int is expected in `MCPConfig`/`TDXConfig` -> impossible to inject via env (these are hardcoded, not env-bound); only code change can introduce this.
- `get_settings()` never raises under normal env. It can raise `AttributeError` only if a caller tries to mutate a frozen field (by design).

### 4.5 State transitions

- Module-global singleton transitions: `None` -> `Settings(...)` on first `get_settings()`; `Settings(...)` -> `None` on `reset_settings()`. No other transitions. Construction is idempotent given a fixed environment.

### 4.6 Migration contract (Target)

**Target (Migration)**: every module listed in Section 3.11 will, after `clean-architecture-migration` (#12) completes, import paths from `doge.config.get_settings()` and contain zero `Path(__file__)`/`os.path.dirname`/`sys.path.insert` root calculations. Acceptance gate in Section 8.

### 4.7 Registry proposals (BLOCKING per-entry approval deferred to Phase 5)

The following constants/env-vars are proposed for later registration in `docs/registry/entities.yaml` and/or `docs/registry/architecture.yaml`. Not written here.

- **Proposed `entities.yaml` entries** (configuration entities):
  - `config.runtime.env.DOGE_DB_DIR` — default `<root>/data`, owner `runtime-configuration`.
  - `config.runtime.env.DOGE_CN_DB` — default `<DB_DIR>/market_data_cn.db`.
  - `config.runtime.env.DOGE_US_DB` — default `<DB_DIR>/market_data_us.db`.
  - `config.runtime.env.DOGE_RESEARCH_DB` — default `<DB_DIR>/research_insights.db`.
  - `config.runtime.env.DOGE_DUCKDB_PATH` — default `<DB_DIR>/market.duckdb`.
  - `config.runtime.tdx.cn_port` = 7709.
  - `config.runtime.tdx.us_port` = 7727.
  - `config.runtime.tdx.timeout` = 5s.
  - `config.runtime.market.cn_min_volume` = 200_000_000.
  - `config.runtime.market.us_min_volume` = 20_000_000.
  - `config.runtime.market.max_change_pct` = 400.
  - `config.runtime.market.rsrs_window` = 18 (default only; formula owned by `micro-momentum-scanner`).
  - `config.runtime.mcp.tool_timeout` = 30s.
  - `config.runtime.mcp.sse_host` = 127.0.0.1.
  - `config.runtime.mcp.sse_port` = 8902.
- **Proposed `architecture.yaml` entries**:
  - `runtime.settings_singleton` — `get_settings()` lazy singleton, resettable via `reset_settings()`.
  - `runtime.project_root_source` — `Path(__file__).resolve().parents[3]` in `src/doge/config/settings.py:15` (single sanctioned source).

---

## 5. Edge Cases

| Situation | What actually happens |
|-----------|------------------------|
| `DOGE_DB_DIR` set to a path that does not exist | `settings.py` performs no existence check and no `makedirs`. Only the legacy caller `src/micro/database.py:19` calls `os.makedirs(..., exist_ok=True)` before connecting; clean-architecture adapters (`src/doge/infrastructure/database/sqlite.py`, `src/doge/infrastructure/database/duckdb.py`) do NOT, so under the target architecture a missing `DOGE_DB_DIR` surfaces as `sqlite3.OperationalError` / `duckdb.IOException` at first DB open/write. |
| `DOGE_CN_DB` set to a relative path | `Path(env)` is stored as-is (relative). Resolution depends on the process CWD at use time — non-deterministic across launchers. No normalization to absolute. |
| Env var set to empty string `""` | `_env_path` treats empty as unset (`if env:` is falsy for `""`), so the default is used. |
| `get_settings()` called from two threads concurrently on a cold cache | Race: both may construct `Settings()`; last writer wins the singleton. Construction is cheap and idempotent, so the practical impact is two transient instances, not corruption. (Not thread-locked by design.) |
| Caller mutates a frozen field | `dataclasses.FrozenInstanceError` (a `AttributeError` subclass) raised at runtime. |
| Test sets env var after first `get_settings()` | Cached singleton retains old paths. Must call `reset_settings()` first. |
| Process started from a different CWD (e.g. via `scripts/start_mcp_sse.sh`) | `_PROJECT_ROOT` is derived from `__file__`, not CWD, so it is CWD-independent. Scripts that honor `DOGE_DB_DIR` (`scripts/start_mcp_sse.sh:15`, `scripts/start_mcp_sse.bat:13`) override correctly. |
| Legacy module and `get_settings()` disagree on root (e.g. legacy uses 4x `dirname` while in a copied tree) | Both currently assume the canonical `src/doge/config/settings.py` depth and `src/<pkg>/<file>` depth respectively. If the repo tree is restructured, legacy `dirname`-chain math silently breaks while `get_settings().project_root` (anchored to `settings.py`) stays correct. Migration risk tracked in #12. |
| `DOGE_DUCKDB_PATH` overridden but `DOGE_CN_DB`/`DOGE_US_DB` left default | DuckDB will `ATTACH` the *default* sqlite paths (relative to `DOGE_DB_DIR`), not the overridden duckdb location's siblings. Cross-DB views can then resolve to a stale CN/US DB. Operator must override all three together. |
| Non-ASCII path in env var on Windows | `Path()` accepts it; success depends on the underlying C library (`sqlite3`, `duckdb`) handling the encoding. Not validated. |

---

## 6. Dependencies

### 6.1 Upstream (this module depends on)
- **Python stdlib only**: `os`, `pathlib.Path`, `dataclasses`, `typing`. Zero third-party imports (`src/doge/config/settings.py:6-9`). No circular-import risk.

### 6.2 Downstream (depend on this module)
- **Foundation**: `market-data-storage` (#2) — reads `db.cn_db/us_db/research_db/duckdb/views_sql`.
- **Foundation**: `data-sources` (#3) — reads `tdx.cn_servers/us_servers/cn_port/us_port/timeout`, `data_dir`, `stock_names_csv`.
- **Core**: `macro-strategy-engine` (#4), `micro-momentum-scanner` (#5) — read `market.*`, `db.*`.
- **Core**: `research-insight-knowledge-base` (#7) — reads `db.research_db`, `report_dir`.
- **Interface**: `mcp-server` (#8) — reads `mcp.*`, `data_dir` (logging).
- **Interface**: `fastapi-service` (#9) — intended consumer (currently legacy routers recalc their own root; migration target).
- **Operations**: `clean-architecture-migration` (#12) — owns the work of routing Section 3.11 offenders through `get_settings()`.

### 6.3 Bidirectional notes (per design-docs rule)
- The above modules' CDDs MUST list `runtime-configuration` in their Dependencies section.
- `clean-architecture-migration` (#12) is the *mutual* owner of the de-duplication effort: this CDD documents the offenders; #12 executes the migration.

### 6.4 Cross-cutting process env (owned elsewhere, listed for awareness)
- `OPENBLAS_NUM_THREADS` / `OMP_NUM_THREADS` — set by `src/ai_analysis/__init__.py:15-16`, `src/api/main.py:12-13`, `src/doge/infrastructure/database/duckdb.py:16-17`. **Not** owned by settings (open question).
- `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` — owned by `src/macro/config.py:168-172` and set by `src/interface/analysis_gui.py:31-32`. **Not** owned by settings (open question — LLM config consolidation).
- `HTTP_PROXY` / `HTTPS_PROXY` — set transiently by `src/micro/industry_analyzer.py:50-51` and `src/macro/data_loader.py:56-147`. Not owned by settings.

### 6.5 Governance references
- **ADR-0001** (`docs/architecture/adr-0001-brownfield-clean-architecture.md`) — establishes the layering and the forbidden patterns this module satisfies (`sys_path_insert`, `_PROJECT_ROOT_recalculation`, `direct_sqlite_import_in_interface`, `direct_duckdb_connect_in_interface`, `cross_layer_state_write`).
- **ADR-0002** (`docs/architecture/adr-0002-centralized-configuration.md`) — the decision to centralize in `settings.py`.

---

## 7. Configuration Knobs

> This section is the heart of the module. Every knob is enumerated with default, valid range, env ownership, and operational risk.

### 7.1 Environment-overridable paths

| Env var | Default | Valid range / type | Env ownership | Operational risk |
|---------|---------|--------------------|---------------|------------------|
| `DOGE_DB_DIR` | `<project_root>/data` | Any filesystem path; should be writable. Absolute recommended (relative resolves against process CWD). | Operator / deployment. Read once at first `get_settings()`. | **HIGH** — wrong value points all DBs at the wrong tree; stale data, "missing table" errors. Override the per-DB vars *with* this one or paths desync. |
| `DOGE_CN_DB` | `<DOGE_DB_DIR>/market_data_cn.db` | Path to a SQLite file (created on first write). | Operator. | **HIGH** — points A-share reads/writes at a different file; silent data split. |
| `DOGE_US_DB` | `<DOGE_DB_DIR>/market_data_us.db` | Path to a SQLite file. | Operator. | **HIGH** — same as above for US market. |
| `DOGE_RESEARCH_DB` | `<DOGE_DB_DIR>/research_insights.db` | Path to a SQLite file. | Operator. | **MEDIUM** — research notes/insights written to wrong DB; less catastrophic than price DBs. |
| `DOGE_DUCKDB_PATH` | `<DOGE_DB_DIR>/market.duckdb` | Path to a DuckDB file. DuckDB also `ATTACH`es the CN/US sqlite files. | Operator. | **MEDIUM** — analytical views materialize against the wrong DuckDB; must keep CN/US overrides consistent or views attach stale sqlite. |

**Note on env ownership**: all five are process-environment variables (no `.env` loader in `settings.py`). They are read by `os.environ.get` inside `_env_path`. The same vars are independently re-read by `src/ai_analysis/__init__.py:30-34` (parallel implementation, see 3.11).

### 7.2 Hardcoded TDX constants (not env-overridable — open question)

| Constant | Default | Valid range | Operational risk |
|----------|---------|-------------|------------------|
| `tdx.cn_servers` | 5 hardcoded IPs | Reachable TDX host IPs; pool may rot over time. | **MEDIUM** — IPs are not under operator control; dead servers require a code change. Proposed for registry (Section 4.7). |
| `tdx.us_servers` | 5 hardcoded IPs | Same. | **MEDIUM** — same. |
| `tdx.cn_port` | `7709` | TCP port 1-65535. | LOW — TDX protocol-fixed. |
| `tdx.us_port` | `7727` | TCP port 1-65535. | LOW. |
| `tdx.timeout` | `5` (seconds) | Positive int; typical 3-15s. | **MEDIUM** — too low truncates slow servers; too high stalls scans. Operator cannot tune without code change. |

### 7.3 Hardcoded market constants (not env-overridable)

| Constant | Default | Affects | Valid range | Operational risk |
|----------|---------|---------|-------------|------------------|
| `market.whitelist` | `{"cn","us"}` | All market-param validation. | Fixed set; adding a market requires code + data pipeline. | LOW for current scope. |
| `market.cn_min_volume` | `200_000_000` (RMB) | CN liquidity screening floor. | Positive int; tuning-sensitive. | **MEDIUM** — wrong value over/under-filters candidates; should be tunable. |
| `market.us_min_volume` | `20_000_000` (USD) | US liquidity floor. | Positive int. | **MEDIUM** — same. |
| `market.max_change_pct` | `400` (%) | Bad-tick rejection threshold. | Positive int; typically 50-1000. | LOW. |
| `market.rsrs_window` | `18` bars | Default RSRS regression window. | Positive int, typical 10-30 (formula range analysis owned by #5). | **MEDIUM** — affects ranking output; this is a *default*, callers may override per-call. |

### 7.4 Hardcoded MCP constants (not env-overridable)

| Constant | Default | Valid range | Operational risk |
|----------|---------|-------------|------------------|
| `mcp.tool_timeout` | `30` (seconds) | Positive int; matches `standards/technical-preferences.md` budget. | **MEDIUM** — raising risks long stalls for AI clients; lowering risks truncating valid queries. |
| `mcp.stdio_transport` | `"stdio"` | `"stdio"` \| `"sse"`. | LOW. |
| `mcp.sse_host` | `127.0.0.1` | Valid IP/hostname. Bound to loopback by default (local-first). | **MEDIUM** — changing to `0.0.0.0` exposes MCP to LAN; security implication. |
| `mcp.sse_port` | `8902` | TCP port 1-65535, unused. | LOW unless port collides. |

### 7.5 Derived (computed, non-overridable)

| Property | Value | Notes |
|----------|-------|-------|
| `settings.project_root` | `_PROJECT_ROOT` (`settings.py:15`) | Single source. |
| `settings.report_dir` | `<project_root>/ai_report` | Created on demand by callers (`ensure_report_dir`). |
| `settings.data_dir` | `= db.dir` | Alias. |
| `settings.stock_names_csv` | `<data_dir>/stock_names_cn.csv` | CN ticker name map. |
| `settings.catalog_json` | `<data_dir>/catalog.json` | Ticker metadata catalog. |

### 7.6 Defaults vs environments

Per `.claude/rules/config-files.md`, production/staging/test/local defaults must be separated. **Current state**: `settings.py` ships a single local-first default set; there is **no environment-tier separation** (no `prod`/`staging`/`test` profile). Tests are expected to set env vars + call `reset_settings()`. Open question (Section 9): introduce a `DOGE_ENV` profile knob?

### 7.7 Migration / backward-compat risk

Changing any default in this file is a **backward-incompatible config change** per `.claude/rules/config-files.md` and requires migration + release notes. Specifically:
- Renaming an env var silently falls back to the default (legacy value ignored) — breaking.
- Repointing a default path relocates every DB on next run — breaking, with data-loss appearance.
- Tightening validation (e.g. asserting paths exist) can break deployments that create paths lazily.

---

## 8. Acceptance Criteria

Testable pass/fail conditions. Items marked **[GATE]** are blocking for `clean-architecture-migration` (#12) sign-off.

### Contract
- [ ] `from doge.config import get_settings` succeeds with no side effects on `sys.path` and no process-global mutation other than the documented BLAS shims (which are NOT in `settings.py`). **[GATE]**
- [ ] `get_settings()` returns the same `Settings` instance on repeated calls within one process (singleton). Resetting env vars without `reset_settings()` does NOT change returned paths.
- [ ] After `reset_settings()`, setting `DOGE_CN_DB=/tmp/x.db` then calling `get_settings().db.cn_db == Path("/tmp/x.db")`.
- [ ] `DOGE_DB_DIR=/tmp/d` (with no per-DB override) yields `cn_db == Path("/tmp/d/market_data_cn.db")`, `us_db == /tmp/d/market_data_us.db`, `research_db == /tmp/d/research_insights.db`, `duckdb == /tmp/d/market.duckdb`, `views_sql == /tmp/d/views.sql`.
- [ ] Empty-string env vars are treated as unset (default used).
- [ ] `Settings`, `DBConfig`, `TDXConfig`, `MarketConfig`, `MCPConfig` are all `frozen=True`; assigning to any field raises `FrozenInstanceError`.

### Centralization (the load-bearing gate)
- [ ] **No `_PROJECT_ROOT` / `project_root` recalculation outside `settings.py`** in `src/doge/**` (grep returns only `settings.py:15`). **[GATE]**
- [ ] No `sys.path.insert` in `src/doge/**`. **[GATE]**
- [ ] All clean-architecture DB consumers (`src/doge/infrastructure/database/*.py`, `src/doge/interfaces/mcp/*.py`, `src/doge/core/services/*.py`) obtain paths via `get_settings()`, not via `Path(__file__)` math. (Currently true; must remain true.)
- [ ] The Section 3.11 legacy offender list is the authoritative migration backlog for #12; each retired offender is struck through in a future revision of this CDD.

### Defaults / docs
- [ ] Every env var in Section 7.1 has a documented default, valid range, and operational risk (done in this CDD).
- [ ] `docs/MCP_SERVER.md:384-389` env-var table is a SUBSET of Section 7.1 and lists at least `DOGE_DB_DIR`, `DOGE_CN_DB`, `DOGE_US_DB`, `DOGE_RESEARCH_DB` with matching defaults. `DOGE_DUCKDB_PATH` is documented ONLY in this CDD §7.1 today (documented gap: add a `DOGE_DUCKDB_PATH` row to `docs/MCP_SERVER.md`, tracked as open question #9 below).

### Observability
- [ ] `settings.py` does not log; consumers log the *resolved* path at startup (e.g. MCP server logs `data_dir`). Smoke check: launching `src/doge/interfaces/mcp/server.py` prints a path under the resolved `data_dir/logs`.

### Migration (Target, owned by #12)
- [ ] `src/ai_analysis/__init__.py` no longer reimplements `_env_path` / re-reads `DOGE_*`; it imports from `doge.config`.
- [ ] Every `src/api/routers/*.py` `_PROJECT_ROOT` removed in favor of `get_settings()`.
- [ ] `src/micro/database.py:217,260,435-436` and all `src/micro/*.py` root recalculations removed or routed through a documented legacy shim.

---

## 9. Open Questions (aspirational — NOT current behavior)

1. **LLM/model config consolidation**: should `MacroConfig` (`src/macro/config.py`) and its `DEEPSEEK_API_KEY`/`DEEPSEEK_MODEL`/`models_config.json`/`proxy_settings` be folded into `settings.py` (e.g. an `LLMConfig` dataclass)? Today they are a parallel config system. (Affects `ai-industry-analysis` #6 and `macro-strategy-engine` #4.)
2. **Validation**: should `settings.py` validate env values (path writability, port ranges, positive ints) at construction and raise a typed `ConfigError`, instead of deferring to first-use runtime errors?
3. **Thread-limit shims**: should `OPENBLAS_NUM_THREADS`/`OMP_NUM_THREADS` (`setdefault` at import in 3 modules) be centralized in `settings.py` or a dedicated `runtime/env.py`?
4. **Environment profiles**: introduce `DOGE_ENV=local|test|prod` to satisfy `.claude/rules/config-files.md`'s environment-tier separation requirement?
5. **TDX server pools**: should `tdx.cn_servers`/`us_servers` become env-or-registry overridable so dead IPs can be rotated without a code change?
6. **Relative-path normalization**: should `_env_path` call `.resolve()` / make paths absolute against `project_root` to eliminate CWD-dependent resolution?
7. **Thread safety of the singleton**: add a lock around first construction, or accept the benign race documented in Section 5?
8. **Dual foundation path** (`src/ai_analysis/__init__.py`): confirm whether it can be deleted outright once `get_settings()` is adopted, or whether its `get_duckdb_connection`/`normalize_ticker` helpers must move to `src/doge/infrastructure/` first.
9. **`docs/MCP_SERVER.md` env-var table gap**: `docs/MCP_SERVER.md:384-389` documents only 4 of the 5 env vars — it omits `DOGE_DUCKDB_PATH`, which is owned by this module (§7.1). Add a `DOGE_DUCKDB_PATH` row (default `{DB_DIR}/market.duckdb`) so the operator-facing doc matches this CDD. Tracked here because the desync already exists; the §8 acceptance criterion was reworded accordingly.
