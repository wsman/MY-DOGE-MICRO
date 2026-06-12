# Module 12: Clean Architecture Migration

> **Slug**: `clean-architecture-migration`
> **Category**: Operations
> **Priority**: MVP
> **Status**: In Progress (brownfield migration)
> **Governing ADR**: [ADR-0001: Brownfield Clean Architecture Migration](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) (Accepted)
> **Last Verified**: 2026-06-11

---

## 1. Overview

The Clean Architecture Migration module is the governance and execution track that
moves MY-DOGE-MICRO from a legacy flat layout — where business logic, database
access, path discovery, and interface wiring are tangled across `src/micro`,
`src/api`, `src/ai_analysis`, root scripts, and the retired legacy MCP monolith — onto a layered
Ports & Adapters structure under `src/doge/` (config / core / infrastructure /
interfaces). The migration is **incremental and brownfield**: existing working
entrypoints stay live while each workflow is re-routed through shared services
and infrastructure adapters, validated by tests, and only then does the legacy
path get removed. This CDD reverse-documents the *current* state (legacy code
that still runs and the untracked-but-present `src/doge/` target tree) and
records the gap between them as explicit acceptance criteria. ADR-0001 already
owns the architectural decision; this CDD owns the operational migration
contract.

---

## 2. User Promise / JTBD

**Operator's job (operator = developer maintaining the platform):** Add a new
analysis feature, wire it to a new MCP tool / API route / UI button, and have it
behave identically across all surfaces — without copy-pasting SQL, recomputing
the project root, or opening a database connection inside an interface module.

**Promise the module must keep:**

- One place owns runtime configuration: `src/doge/config/settings.py`. No module
  outside that file should recompute `_PROJECT_ROOT` or insert into `sys.path`
  for its own use.
- Business rules live in `src/doge/core/services/*` and depend only on ports
  (`src/doge/core/ports/*`), never on `sqlite3`, `duckdb`, or interface
  frameworks.
- All database/network access lives in `src/doge/infrastructure/*` adapters that
  *implement* the ports.
- Every interface (MCP / FastAPI / CLI / GUI / Web) reaches the data through a
  service, not by importing a database driver.
- During migration, working workflows stay live while each surface moves to the
  layered implementation. For MCP, Wave 4 completed the handoff:
  `doge_mcp.py -> src/doge/interfaces/mcp/server.py` is the only live root
  entrypoint.

---

## 3. Detailed Behavior

This is an Operations module: it has no end-user-facing API of its own. Its
"behavior" is the **dependency-rule enforcement** and the **migration batches**
that reshape every other module. Both states are documented below as observed in
the source tree on 2026-06-11.

### 3.1 Current State — Legacy Layout (still live, untracked in part)

The legacy layer is the running implementation for several workflows. The
anti-patterns ADR-0001 forbids are *currently present* here and are the migration
backlog.

- **Retired root MCP monolith (`mcp_server.py`, deleted in Wave 4)** — opened DuckDB
  directly via `from ai_analysis import get_duckdb_connection` (mcp_server.py:38)
  and SQLite directly via a module-level `import sqlite3` (mcp_server.py:23),
  used inside `stock_overview` via `sqlite3.connect(...)` at mcp_server.py:304
  and mcp_server.py:340. Bootstraps the path with
  `sys.path.insert(0, str(_HERE / "src"))` (mcp_server.py:33) and
  recomputes `_HERE = Path(__file__).resolve().parent` (mcp_server.py:32).
  Tools (`query_stock`, `stock_overview`, `rsrs_ranking`, `market_breadth`,
  `volume_anomalies`, `list_views`) embed raw SQL inline; the six `@mcp.tool()`
  decorators land at mcp_server.py:266, :294, :363, :376, :389, :406 (inline SQL
  spans roughly mcp_server.py:266-413).
- **`src/ai_analysis/__init__.py`** — the legacy "god package": owns path
  constants (`PROJECT_ROOT` at ai_analysis/__init__.py:21; `DB_DIR`, `CN_DB`,
  `US_DB`, `RESEARCH_DB`, `DUCKDB_PATH` env-derived at
  ai_analysis/__init__.py:30-34; `VIEWS_SQL` at :35; `REPORT_DIR` at :36 — the
  full constants block runs ai_analysis/__init__.py:21-36), connection
  factories (`get_duckdb_connection`, `connect_duckdb`), and
  `normalize_ticker`. Every legacy module imports from here.
- **`src/api/routers/*.py`** — FastAPI routers. Each recomputes
  `_PROJECT_ROOT` (scan.py:17, macro.py:13, data.py:11, config.py:11,
  analysis.py:11), and several open SQLite/DuckDB directly:
  `data.py:7 import sqlite3`, `data.py:110-111 from src.ai_analysis import
  connect_duckdb`, `scan.py:210-211 from src.ai_analysis import connect_duckdb,
  run_views_sql`.
- **`src/micro/*.py`** — scanners and downloader. Each module bootstraps its own
  path: `tdx_downloader.py:23-26` (double `sys.path.insert`), `market_scanner.py:24-26`,
  `industry_analyzer.py:17`. `tdx_downloader.py` recomputes `_PROJECT_ROOT` and
  joins `"data"` paths at :499, :546.
- **`src/cli.py`, `src/macro/cli.py`, `src/interface/scanner_gui.py`,
  `src/ai_analysis/{stock_notes,market_overview,fetch_names,catalog_generator,
  anomaly_detection}.py`** — each contains its own `sys.path.insert`
  (confirmed by grep across `src/`).
- **Circular dependencies** (per `docs/MODULARIZATION_PLAN.md:18-23`):
  `cli → ai_analysis (connect_duckdb)`;
  `api/routers/scan → micro/tdx_downloader → ai_analysis (run_views_sql)`;
  `micro/market_scanner → ai_analysis (connect_duckdb)`;
  `macro/strategist ↔ micro/industry_analyzer`.

### 3.2 Target (Migration) — `src/doge/` Clean Architecture

The target tree exists on disk (untracked as of 2026-06-11) and is partially
wired. The dependency rule (ADR-0001:86-103, MODULARIZATION_PLAN.md:91-106) is:

```
interfaces/ ──→ core/services/ ──→ core/ports/ 〈── infrastructure/ 〈── SQLite/DuckDB/TDX/yfinance/cache
```

Layers must not point inward; `core` imports no framework; `infrastructure`
implements `core/ports`; `interfaces` depends only on `core/services`.

**`src/doge/config/`** — single source of truth for paths/settings.
- `settings.py` defines `_PROJECT_ROOT = Path(__file__).resolve().parents[3]`
  (settings.py:15), frozen dataclasses `DBConfig` (class at settings.py:24),
  `TDXConfig` (:42), `MarketConfig` (:58), `MCPConfig` (:68), `Settings` (:77)
  (the `@dataclass(frozen=True)` block spans settings.py:23-83), env overrides
  (`DOGE_DB_DIR` at settings.py:26; `DOGE_CN_DB`/`DOGE_US_DB`/
  `DOGE_RESEARCH_DB`/`DOGE_DUCKDB_PATH` at settings.py:34-37), and a lazy
  singleton `get_settings()` / `reset_settings()` (settings.py:107/115).
  `__init__.py` re-exports `Settings, get_settings`.

**`src/doge/core/domain/models.py`** — pure dataclasses (`MarketType`, `Ticker`,
`OHLCV`, `Stock`, `RSRSRecord`, `BreadthRecord`, `VolumeAnomaly`) with zero
external imports. This is the canonical place domain records live; legacy code
still uses raw dicts.

**`src/doge/core/ports/`** — abstract base classes (ABCs):
- `repository.py`: `IStockRepository` (get_prices / get_overview / get_sync_state),
  `IReportRepository` (list_macro_reports / get_macro_report / save_macro_report
  / save_research_report / add_note / search_notes / list_stock_names).
- `data_source.py`: `IMarketDataSource` (connect / disconnect / download_kline
  / get_latest_market_date / is_connected).
- `cache.py`: `ITickerNameCache` (get / load / clear).

**`src/doge/core/services/`** — business services, take ports via constructor
injection:
- `StockService(IStockRepository)` — `query()`, `overview()`.
- `RankingService(IMarketViewRepository)` — `rsrs(market, top)`.
- `BreadthService(IMarketViewRepository)` — `breadth(market, days)`.
- `AnomalyService(IMarketViewRepository)` — `anomalies(min_ratio, top)`.
- `ViewService(IMarketViewRepository)` — `list_views()`.
- `composition.py` — factory functions `build_view_service()` /
  `build_ranking_service()` / `build_breadth_service()` /
  `build_anomaly_service()` that construct a `DuckDBMarketViewRepository` and
  inject it. This module is the **single site** under `core/services/` that
  imports `doge.infrastructure` (per ADR-0010).

> **Resolved (2026-06-12, ADR-0010 / story S002-004 / TR-041):** the four
> view-backed services were previously a known deviation — they accepted the
> concrete `DuckDBConnection` adapter directly rather than a port. They now
> depend on the `IMarketViewRepository` port (single `execute(sql, params) ->
> DataFrame` method covering all four read-only view services), with default
> adapter construction moved to the composition root. The four service modules
> now import no infrastructure, satisfying AC-2. See ADR-0010.

**`src/doge/infrastructure/`** — adapters implementing the ports:
- `database/duckdb.py` — `DuckDBConnection` context manager that auto-attaches
  the cn/us SQLite DBs (duckdb.py:30-49), plus legacy compat shims
  `get_duckdb_connection()` / `connect_duckdb()` (duckdb.py:87-96) that wrap it.
- `database/sqlite.py` — `SQLiteConnection` with `connect()`, `execute()`,
  `execute_one()`, `execute_scalar()`; defaults to `research_db`
  (sqlite.py:22-25).
- `database/repositories.py` — `DuckDBStockRepository(IStockRepository)` and
  `SQLiteReportRepository(IReportRepository)`; concrete SQL lives here, never in
  services or interfaces.
- `data_source/tdx.py` — `TDXDataSource(IMarketDataSource)` **stub**:
  `download_kline` / `get_latest_market_date` raise `NotImplementedError`
  (tdx.py:32, tdx.py:35). TDX logic still lives in legacy
  `src/micro/tdx_downloader.py`.
- `cache/ticker_cache.py` — `JSONTickerNameCache(ITickerNameCache)`:
  thread-safe (`threading.Lock`), lazy file-backed, replaces the old global
  `_ticker_names_cache` dict.

**`src/doge/interfaces/mcp/`** — the modular interface surface:
- `server.py` — `create_mcp_server()` factory wiring 6 tools through services
  (server.py:141-234); each tool module
  (`tools/query_stock.py`, `tools/ranking.py`, `tools/anomaly.py`,
  `tools/views.py`) constructs a service and delegates. `main()`
  (server.py:238-272) supports `--transport stdio|sse`.
- **Critically**: `server.py` imports **no** `sqlite3`/`duckdb` directly at the
  tool level — it goes through `DuckDBConnection` (imported inside the tool at
  server.py:149/214, used via `DuckDBConnection(...).connect()` at server.py:150
  and :215) and the tool modules go through services/repositories. This is the
  target shape every other interface must reach.

### 3.3 Migration Path (batched; live entrypoints preserved)

Per `docs/MODULARIZATION_PLAN.md:108-144` and ADR-0001:200-209. Each batch is
gated by tests before the next begins:

| Batch | Scope | Evidence on disk | Status |
|-------|-------|------------------|--------|
| 1 | `pyproject.toml` (editable install `pip install -e .`), `src/doge/config/settings.py`, eliminate `sys.path.insert` | `pyproject.toml` exists (packages find at `src/`, pythonpath `["src"]`); settings.py exists; legacy `sys.path.insert` **still present in 13 distinct legacy files** (14 insert sites — `tdx_downloader.py` has two) | Partial — package install exists, legacy bootstraps remain |
| 2 | Repository ports + DuckDB/SQLite adapters + repositories | `ports/repository.py`, `infrastructure/database/{duckdb,sqlite,repositories}.py` all exist | Implemented (read paths); write-path coverage partial |
| 3 | TDX data source adapter | `data_source/tdx.py` is a stub raising `NotImplementedError` | Not started — logic still in `micro/tdx_downloader.py` |
| 4 | Core services | All 5 services exist; all now take ports — `StockService` uses `IStockRepository`, the 4 view-backed services use `IMarketViewRepository` (ADR-0010) | Implemented (port-injected; composition root owns infra wiring) |
| 5 | Interface rewire (MCP/CLI/API/GUI) | MCP done (`interfaces/mcp/`); `src/api/routers/*` still legacy; `src/cli.py` still legacy | MCP complete; API/CLI/GUI pending |
| 6 | Cleanup + full test pass | MCP monolith deleted; broader legacy API/CLI/GUI code still present | MCP cleanup complete; broader cleanup pending |

**MCP entrypoint status (Wave 4):**
- `doge_mcp.py` is the canonical repo-root entrypoint and contains no
  `sys.path.insert` fallback.
- `scripts/mcp_stdio.bat`, `scripts/mcp_stdio.sh`, and the SSE scripts launch
  `doge_mcp.py`.
- The legacy `mcp_server.py` monolith was deleted after modular parity evidence;
  the old layer-gate carve-out is gone.

---

## 4. Contracts / Data Model

This module's "contracts" are the layer boundaries and the port/service
inventory. Method-level signatures are owned by each feature module's CDD; this
CDD pins the **inventory and dependency direction**.

### 4.1 Port inventory (verbatim from ADR-0001:108-123 and source)

Repository ports (`src/doge/core/ports/repository.py`):
- **`StockRepository`** — stock price data access. *(Source class name:
  `IStockRepository`.)*
- **`ReportRepository`** — research report / note data access. *(Source class
  name: `IReportRepository`.)*
- **`NoteRepository`** — note-specific operations. *(Currently folded into
  `IReportRepository.add_note`/`search_notes`; a standalone `NoteRepository`
  port is the target split.)*

Data source ports (`src/doge/core/ports/data_source.py`):
- **`MarketDataSource`** — market data download (TDX / yfinance). *(Source class
  name: `IMarketDataSource`.)*

Plus the **two distinct ticker-metadata ports** (resolved by ADR-0009):
- **`ITickerNameCache`** (`src/doge/core/ports/cache.py`) — local-JSON ticker
  name lookup (get / load / clear; returns a name string). Adapter:
  `JSONTickerNameCache` (file-backed). This is ADR-0001's `Cache` concept.
- **`ITickerMetadataSource`** (`src/doge/core/ports/metadata.py`) — remote
  yfinance `.info` metadata lookup (`get_metadata(ticker, market) -> Optional[dict]`
  returning `{'name': ..., 'sector': ...}`). Adapter:
  `YFinanceMetadataSource` (stub, raises `NotImplementedError` pending the
  `industry_analyzer.py:190` migration). This is ADR-0001's `TickerMetadataSource`.

> **Resolved (2026-06-12, ADR-0009 / story S002-003 / TR-042 / OQ-2):** the
> "mutually-exclusive candidate names" framing is withdrawn — `ITickerNameCache`
> (local file, name string) and `ITickerMetadataSource` (network, name+sector
> dict) are **two distinct ports**, differing by data source and returned shape.
> ADR-0001:115's `TickerMetadataSource` line is read as refined by ADR-0009
> (un-prefixed `TickerMetadataSource` -> `ITickerMetadataSource`; `Cache` ->
> `ITickerNameCache`).

Read-only view port (`src/doge/core/ports/market_view.py`):
- **`IMarketViewRepository`** — single `execute(sql, params) -> DataFrame`
  method covering all four read-only view-backed services. Adapter:
  `DuckDBMarketViewRepository`. (ADR-0010 / TR-041 / OQ-5.)

> **Naming note (AC-10/OQ-2, resolved):** ADR-0001 lists the canonical names
> without the `I` prefix (`StockRepository`, `TickerMetadataSource`, …); source
> code uses `I`-prefixed ABC names (`IStockRepository`, `ITickerMetadataSource`,
> …). Per ADR-0009 the **I-prefix is kept** and the registry records the alias
> map; no existing ABC is renamed.

### 4.2 Core service inventory (verbatim from ADR-0001:117-123, updated by ADR-0010)

- **`StockService`** — `src/doge/core/services/stock_service.py`. Constructed
  with `IStockRepository`. Methods: `query(ticker, market, days)`,
  `overview(ticker, market)`.
- **`RankingService`** — `ranking_service.py`. Constructed with
  `IMarketViewRepository` (ADR-0010). Method: `rsrs(market, top)`.
- **`BreadthService`** — `breadth_service.py`. Constructed with
  `IMarketViewRepository` (ADR-0010). Method: `breadth(market, days)`.
- **`AnomalyService`** — `anomaly_service.py`. Constructed with
  `IMarketViewRepository` (ADR-0010). Method: `anomalies(min_ratio, top)`.
- **`ViewService`** — `view_service.py`. Constructed with
  `IMarketViewRepository` (ADR-0010). Method: `list_views()`.
- **`composition.py`** — `src/doge/core/services/composition.py`. Factory
  functions `build_view_service()` / `build_ranking_service()` /
  `build_breadth_service()` / `build_anomaly_service()`; the single
  infrastructure-import site for the view-backed services (ADR-0010).

### 4.3 Layer dependency contract (enforced rule)

| Layer | May import | May NOT import |
|-------|-----------|----------------|
| `interfaces/*` | `core.services`, `infrastructure` (for DI wiring only), `config` | `sqlite3`, `duckdb`, `ai_analysis`, `micro`, `sys.path` mutation |
| `core.services/*` | `core.ports`, `core.domain` | `sqlite3`, `duckdb`, `infrastructure`, any interface/framework |
| `core.ports/*` | stdlib, `core.domain` (optional) | any infrastructure, any framework |
| `infrastructure/*` | `core.ports` (to implement), `config`, drivers (`sqlite3`/`duckdb`/`opentdx`) | `core.services`, `interfaces` |
| `config/*` | stdlib only | any other layer |

### 4.4 Forbidden patterns (ADR-0001 forbidden_patterns registry)

These are the lint/invariant rules the migration eliminates:
- `direct_sqlite_import_in_interface` — e.g. `src/api/routers/data.py:7`.
- `direct_duckdb_connect_in_interface` — e.g. `scan.py:210-211`.
- `sys_path_insert` — remaining legacy insert sites are under `src/micro`, `src/api`, `src/ai_analysis`, `src/cli.py`, `src/macro/cli.py`, and `src/interface/scanner_gui.py`; `doge_mcp.py` has no shim.
- `_PROJECT_ROOT_recalculation` — 7+ legacy occurrences (`tdx_downloader.py:23`, `market_scanner.py:24`, all 5 `api/routers/*.py`, `api/main.py:9`, `ai_analysis/__init__.py:21`).
- `cross_layer_state_write` — interface modules writing shared module-level DB state (e.g. legacy `ai_analysis` connection globals).

### 4.5 Entrypoint contract

| Entrypoint | Transports | Imports legacy `ai_analysis`? | Status |
|-----------|-----------|-------------------------------|--------|
| `doge_mcp.py` → `doge.interfaces.mcp.server.main` | stdio, sse | No (only `doge.*`) | Canonical, live |
| `src/api/main.py` (FastAPI) | http | Indirectly via routers | Legacy routers, pending rewire |
| `src/cli.py` | CLI | Yes | Legacy, pending rewire |

### 4.6 Integration Requirements

This Operations/migration module owns no external data or API integration of its
own, but it is the **contract owner for how every interface integrates with
services** — it defines the integration surface that the feature modules'
interfaces must conform to. The enforced integration surface is:

- **MCP transport contract** (owned in detail by **Module #8 — MCP Server**):
  `doge_mcp.py` / `doge.interfaces.mcp.server` must expose stdio and SSE
  transports with identical tool semantics, the same `_timed` 30 s timeout
  (TOOL_TIMEOUT), and the same validation rules
  (`_validate_market` / `_validate_ticker` / `_validate_int` / `_validate_float`).
  Cross-ref: Module #8 (`mcp-server`).
- **HTTP/FastAPI contract** (owned in detail by **Module #9 — FastAPI Service**):
  routers under `src/api/routers/*` must, post-migration, obtain data via injected
  services rather than opening DB connections or recomputing the project root.
  Cross-ref: Module #9 (`fastapi-service`).
- **Entrypoint concurrency guarantee**: the MCP entrypoint and the FastAPI app
  may run concurrently against the same DuckDB file; queries open DuckDB
  `read_only=True` so concurrent readers do not lock, and the modular MCP server
  only logs orphaned sibling PIDs rather than killing them (see §5).
- **Health/metrics integration surface**: the modular server's `/health` and
  `/metrics` routes are the monitoring integration points (AC-14).

This module defers all transport-level *protocol* details (MCP framing, FastAPI
schema, request/response shapes) to Modules #8 and #9; it owns only the
**dependency-rule invariant** that those transports reach data through services,
never through a database driver.

### 4.7 Registry proposals (for later Phase-5 approval — do NOT write yet)

- `docs/registry/entities.yaml` proposed entries:
  - Port: `StockRepository` (class `IStockRepository`)
  - Port: `ReportRepository` (class `IReportRepository`)
  - Port: `NoteRepository` (split target of report port note methods)
  - Port: `MarketDataSource` (class `IMarketDataSource`)
  - Port: **one of** `TickerMetadataSource` **or** `Cache` (class
    `ITickerNameCache`) — these are mutually-exclusive candidate canonical names
    for the *same* port/adapter pair; exactly one will be chosen at Phase-5
    registry approval (OQ-2), not both. Do NOT record both as concurrent ports.
  - Service: `StockService`, `RankingService`, `BreadthService`,
    `AnomalyService`, `ViewService`
- `docs/registry/architecture.yaml` proposed entries:
  - Layer rule: `interfaces → services → ports ← infrastructure`
  - Forbidden pattern set: `direct_sqlite_import_in_interface`,
    `direct_duckdb_connect_in_interface`, `sys_path_insert`,
    `_PROJECT_ROOT_recalculation`, `cross_layer_state_write`
  - Migration batch graph (6 batches, dependencies as in §3.3)

---

## 5. Edge Cases

Stated behavior — what *actually happens* today or is contractually required.

- **MCP + FastAPI run concurrently.** An operator may start `doge_mcp.py` and
  the FastAPI app at once. DuckDB is opened `read_only=True` for queries, so
  concurrent readers do not lock. The MCP server detects orphaned sibling PIDs
  via a PID file and only logs a warning; it does not kill them.
- **Editable install not present.** `doge_mcp.py` no longer has a `sys.path`
  fallback. If the project is not importable through the package/editable
  layout, the MCP server should fail fast and the environment should be fixed.
- **`views.sql` missing or a single view statement fails.** `DuckDBConnection.
  refresh_views()` (duckdb.py:58-83) swallows per-statement exceptions and
  continues; a missing `views.sql` returns silently. Behavior: best-effort,
  partial view set is acceptable.
- **Ticker name file missing.** `JSONTickerNameCache._load_from_disk` returns
  `{}` on missing file or JSON parse error (ticker_cache.py:26-34); `get()`
  then returns `None` for every ticker. Downstream, `stock_overview` simply
  omits the name line (query_stock.py:66-68).
- **Invalid market / ticker / numeric arg.** Validated in both entrypoints via
  `_validate_market` (whitelist `{cn, us}`), `_validate_ticker`
  (regex `^[A-Za-z0-9.\-]+$`, CN suffix rules), `_validate_int` /
  `_validate_float` (range-checked). On violation: `ValueError`, which the
  `_timed` decorator catches and returns as `"Error: …"` string (never an
  uncaught exception, never an HTTP 500 in SSE).
- **Tool exceeds 30 s.** `_timed` wraps each tool in
  `asyncio.wait_for(timeout=TOOL_TIMEOUT)` (TOOL_TIMEOUT=30, server.py) and
  returns `"Error: <tool> timed out after 30s"`. ADR-0001
  MCP latency budget (Under 30 s, ADR-0001:194) is enforced by this same
  constant.
- **TDX adapter called before migration.** `TDXDataSource.download_kline` /
  `get_latest_market_date` raise `NotImplementedError` (tdx.py:32,35). Any
  service or interface that tries to use it before Batch 3 must surface this
  clearly; today nothing in `src/doge/` calls it (TDX sync still routes through
  legacy `micro/tdx_downloader.py`).
- **Partial migration rollback.** Per ADR-0001:209: if a migrated service breaks
  a workflow, route that interface back to the legacy implementation while the
  service contract is fixed. For MCP, Wave 4 already passed the replacement
  gate: tests target the modular server and the legacy monolith is deleted.
- **Config drift between legacy and new path sources.** Legacy
  `ai_analysis/__init__.py:30-36` and `doge/config/settings.py:26-38` define the
  *same* env var names (`DOGE_DB_DIR`, `DOGE_CN_DB`, `DOGE_US_DB`,
  `DOGE_RESEARCH_DB`, `DOGE_DUCKDB_PATH`) with the *same* defaults, so a single
  environment drives both. If they ever diverge, the migration is the
  single-source owner going forward (AC-3).
- **`sys.path.insert` reintroduced under pressure.** Stated rule: any new
  interface code that introduces scattered `sys.path.insert` or repeated
  project-root discovery fails review (ADR-0001:217). The `_PROJECT_ROOT` in
  `settings.py:15` is the *one* sanctioned calculation.

---

## 6. Dependencies

### 6.1 Governing document

- **ADR-0001** (`docs/architecture/adr-0001-brownfield-clean-architecture.md`) —
  Accepted 2026-06-11. Owns the architecture decision; this CDD does **not**
  create a new ADR. References ADR-0001 for: layer boundaries (:86-103), port
  inventory (:108-123), migration plan (:200-209), validation criteria
  (:212-217), performance budget (:192-197).

### 6.2 Upstream (this module depends on)

- **#1 Runtime Configuration** (`runtime-configuration`) — `src/doge/config/
  settings.py` is the foundation the migration centralizes on. All other
  `src/doge/` layers import `get_settings()`. Migration cannot proceed without
  Module #1's env contract (env var names above).
- **#2 Market Data Storage** (`market-data-storage`) — defines the SQLite/DuckDB
  schemas and views (`vw_daily_enriched_cn`, `vw_rsrs_ranking_*`,
  `vw_market_breadth_*`, `vw_volume_anomalies_cn`) that the repositories and
  view-backed services query. Repository SQL in `repositories.py` and service
  SQL in `*_service.py` is bound to those view/table names.

### 6.3 Downstream (depend on this module)

- **#3 Data Sources** — TDX/yfinance adapters will live in
  `src/doge/infrastructure/data_source/` and implement `IMarketDataSource`
  (currently a stub, see §3.2).
- **#4 Macro Strategy Engine**, **#5 Micro Momentum Scanner** — business logic
  migrates into `src/doge/core/services/`; RSRS formula (`src/micro/
  momentum_scanner.py:47-71`, `calculate_rsrs(series, window=18)` =
  R² × sign(slope) via `scipy.stats.linregress`) must remain canonical and be
  referenced, not redefined, by any new service location.
- **#6 AI Industry Analysis**, **#7 Research Insight Knowledge Base** — use
  `IReportRepository` / `SQLiteReportRepository` for report and note persistence.
- **#8 MCP Server** — modular server (`src/doge/interfaces/mcp/server.py`) is
  the reference implementation of a correctly-wired interface; `doge_mcp.py`
  is the canonical root entrypoint.
- **#9 FastAPI Service** — routers under `src/api/routers/` must be re-routed
  through services (Batch 5, currently legacy).
- **#10 PyQt Desktop Dashboard**, **#11 Vue Web Console** — presentation layers
  must reach data via services/API only; no direct DB access.

### 6.4 Packages / tooling

- `pyproject.toml` (setuptools, packages found at `src/`, pythonpath `["src"]`,
  pytest `asyncio_mode = "strict"`).
- `duckdb==1.4.4`, `pandas`, `scipy`, `pytest==9.0.1`, `pytest-asyncio==1.3.0`,
  `fastapi==0.123.8`, `mcp==1.25.0` (versions per `pyproject.toml` and
  `standards/technical-preferences.md`).
- `opentdx` / `akshare` (optional extras `tdx`, `cn`) for the not-yet-migrated
  TDX adapter.

### 6.5 Related docs

- `docs/MODULARIZATION_PLAN.md` (source migration plan, batch definitions).
- `docs/imports/my-doge-micro/current-state-2026-06-11.md`,
  `docs/imports/my-doge-micro/git-snapshot-2026-06-11.md` (frozen state
  referenced by ADR-0001).
- `design/cdd/module-index.md` (Module #12 row).

---

## 7. Configuration Knobs

Migration-relevant knobs. Domain knobs (RSRS window, breadth days, etc.) are
owned by their feature module CDDs; listed here only where they intersect
migration boundaries.

| Knob | Source | Default | Valid range | Env owner | Migration role / risk |
|------|--------|---------|-------------|-----------|-----------------------|
| `DOGE_DB_DIR` | settings.py:26 | `<root>/data` | absolute dir path | operator shell / `.env` | Single source for data dir; legacy `ai_analysis` reads same name — drift = dual source of truth (risk: MEDIUM) |
| `DOGE_CN_DB` | settings.py:34 | `<dir>/market_data_cn.db` | absolute file path | operator | Read by both `DuckDBStockRepository` and legacy `ai_analysis` |
| `DOGE_US_DB` | settings.py:35 | `<dir>/market_data_us.db` | absolute file path | operator | Same dual-read concern |
| `DOGE_RESEARCH_DB` | settings.py:36 | `<dir>/research_insights.db` | absolute file path | operator | `SQLiteReportRepository` default (sqlite.py:24-25) |
| `DOGE_DUCKDB_PATH` | settings.py:37 | `<dir>/market.duckdb` | absolute file path | operator | DuckDB file; opened read_only for queries, read-write for `refresh_views` |
| `OPENBLAS_NUM_THREADS` / `OMP_NUM_THREADS` | duckdb.py:16-17, ai_analysis/__init__.py:15-16 | `"1"` | `"1"` recommended | runtime (setdefault) | OOM guard during pandas `.df()` conversion; duplicated in legacy and new — must dedupe post-migration |
| DuckDB `threads` | duckdb.py:39 | `4` | 1–8 | hardcoded in adapter | Adapter-owned; not operator-configurable yet (open question OQ-3). **Rationale for 1–8:** bounded by the local single-operator workload (one desktop, no concurrent heavy queries) and the same peak-memory concern that pins `OPENBLAS_NUM_THREADS=1` (duckdb.py:16-17) — DuckDB result rows are materialized to pandas via `.df()`, so more DuckDB threads fan out more concurrent conversion work and raise peak RSS. **Operational risk:** raising `threads` increases peak memory during `.df()` conversion and interacts with the `OPENBLAS_NUM_THREADS=1` OOM guard; a value near the upper bound (8) risks OOM on large result sets on a constrained local machine. **Rollout:** until OQ-3 resolves, this knob cannot be tuned at runtime without editing `duckdb.py:39` (`con.execute("SET threads=4")`). |
| MCP `TOOL_TIMEOUT` | server.py | `30` (s) | 1–120 | hardcoded | Matches ADR-0001 MCP latency budget; mirrors `MCPConfig.tool_timeout` |
| MCP SSE host/port | settings.py (`MCPConfig` fields `tool_timeout`/`stdio_transport`/`sse_host`/`sse_port`) | `127.0.0.1:8902` | valid host:port | `MCPConfig` dataclass (scripts also accept env overrides) | `doge_mcp.py` / modular server are the live path |
| `pytest` `asyncio_mode` | pyproject.toml:38 | `"strict"` | `strict`/`auto` | pyproject | Migration tests rely on explicit async markers |

**Operational risk summary:** The chief migration risk is the *temporary dual
source of truth* for paths/constants (legacy `ai_analysis/__init__.py` vs
`doge/config/settings.py`). They agree today; if a developer edits only one,
legacy API/CLI paths can diverge from the clean architecture path. Mitigation:
AC-3 and AC-8 (delete legacy constants once all imports move).

---

## 8. Acceptance Criteria

Testable pass/fail. Each criterion names the artifact or grep that proves it.

**Layer-rule enforcement**
- [x] **AC-1.** No file under `src/doge/interfaces/` contains
  `import sqlite3`, `import duckdb`, or `from ai_analysis` (grep must return 0
  hits). `doge_mcp.py` contains no `sys.path` fallback.
- [ ] **AC-2.** No file under `src/doge/core/services/` imports `sqlite3`,
  `duckdb`, `ai_analysis`, `micro`, or any interface framework (`fastapi`,
  `mcp`, `PyQt6`), nor `from doge.infrastructure`. (Resolved 2026-06-12 by
  ADR-0010: `ranking/breadth/anomaly/view_service.py` now import only the
  `IMarketViewRepository` port; the single infrastructure import lives in the
  `composition.py` composition root.)
- [ ] **AC-3.** Path/DB constants in legacy `src/ai_analysis/__init__.py` and
  `src/doge/config/settings.py` resolve to identical values for the same
  environment (parity test passes for all 5 env vars).
- [ ] **AC-4.** A test asserts that every `src/doge/core/ports/*` ABC has at
  least one implementation in `src/doge/infrastructure/*` (port→adapter
  coverage). Today: `IMarketDataSource` has only a stub (AC-5 blocks its
  deletion, not its existence).

**Migration completion gates**
- [ ] **AC-5.** `TDXDataSource.download_kline` and `get_latest_market_date`
  (tdx.py:32,35) no longer raise `NotImplementedError` — logic migrated from
  `src/micro/tdx_downloader.py`, verified by a **unit test at
  `tests/unit/infrastructure/test_tdx_data_source.py`** using a **recorded TDX
  protocol fixture under `tests/fixtures/tdx/`** (no live network — isolation per
  `coding-standards.md` and the testing-standards "no network-dependent tests
  without isolation/fixtures" rule). Pass/fail: the test exercises both methods
  against the recorded fixture and asserts the returned kline rows and market
  date without raising; a QA tester can locate the file and run it offline.
- [ ] **AC-6.** `src/api/routers/*.py` contain no `_PROJECT_ROOT` recomputation
  and no direct `import sqlite3` / `connect_duckdb`; routers obtain data via
  injected services.
- [ ] **AC-7.** `src/cli.py` reaches data through services, with no
  `sys.path.insert` and no direct DB import.
- [ ] **AC-8.** After all interfaces migrate, `src/ai_analysis/__init__.py` is
  either deleted or reduced to a thin re-export shim of `doge.config` /
  `doge.infrastructure.database.duckdb` legacy-name aliases, and the
  `ai_analysis` god-package path constants are removed.

**Interim-shape reconciliation (recorded open question → AC)**
- [x] **AC-9.** **RESOLVED (2026-06-12, ADR-0010 / story S002-004 / TR-041 /
  OQ-5).** The four view-backed services are converted to depend on the
  `IMarketViewRepository` port (single `execute(sql, params) -> DataFrame`
  method) rather than the concrete `DuckDBConnection` adapter. A composition
  root (`composition.py`) owns the default-adapter construction. See ADR-0010.

**Naming reconciliation**
- [x] **AC-10.** **RESOLVED (2026-06-12, ADR-0009 / story S002-003 / TR-042 /
  OQ-2).** ADR-0001 port names (`StockRepository`, `ReportRepository`,
  `NoteRepository`, `MarketDataSource`, `TickerMetadataSource`, `Cache`) are
  reconciled with source class names (`IStockRepository`, etc.) via a registry
  alias map — the **I-prefix is kept** and no existing ABC is renamed. The
  `TickerMetadataSource`/`Cache` ambiguity is split into two distinct ports
  (`ITickerMetadataSource` + `ITickerNameCache`). See ADR-0009.

**Entrypoint / test gates (from ADR-0001:212-217)**
- [x] **AC-11.** `pytest` passes for MCP tools, database, and transport in the
  source repository. MCP tests target `doge_mcp.py` / `doge.interfaces.mcp.server`;
  the legacy monolith is deleted.
- [x] **AC-12.** MCP stdio and SSE startup scripts launch `doge_mcp.py`
  (`scripts/mcp_stdio.*`, `scripts/start_mcp_sse*.sh/.bat`).
- [x] **AC-13.** No *new* interface code introduces `sys.path.insert` or
  repeated project-root discovery (review checklist item; enforced by grep in
  CI on `src/doge/interfaces/**` and `doge_mcp.py`).

**Observability**
- [x] **AC-14.** The modular server's `/health` and `/metrics` routes return
  200/503 and Prometheus-style text respectively; transport tests pin this.

---

## Open Questions

- **OQ-1.** **RESOLVED (2026-06-12, Wave 4).** `doge_mcp.py` no longer has a
  `sys.path.insert` fallback; package/editable importability is required.
- **OQ-2.** **RESOLVED (2026-06-12, ADR-0009 / story S002-003 / TR-042).**
  ADR-0001 port names are reconciled with source ABC names by **keeping the
  I-prefix** and recording a registry alias map. The `TickerMetadataSource` vs
  `Cache` ambiguity is resolved by splitting into two distinct ports:
  `ITickerNameCache` (local-JSON name lookup) + `ITickerMetadataSource` (remote
  yfinance `.info` name+sector). See ADR-0009.
- **OQ-3.** Should DuckDB `threads` (duckdb.py:39, currently hardcoded `4`)
  and `OPENBLAS_NUM_THREADS` become operator-configurable via `Settings`, or
  stay adapter-owned?
- **OQ-4.** Should a standalone `NoteRepository` port be split out of
  `IReportRepository` (which currently mixes macro reports, research reports,
  notes, and stock names), or is the combined port acceptable long-term?
- **OQ-5.** **RESOLVED (2026-06-12, ADR-0010 / story S002-004 / TR-041).** A
  `IMarketViewRepository` port IS warranted (single `execute(sql, params) ->
  DataFrame` method covers all four read-only view services). The four services
  now take the port; a composition root owns the infrastructure wiring. See
  ADR-0010.
- **OQ-6.** Migration ordering vs. Modules #4/#5: do Macro Strategy Engine and
  Micro Momentum Scanner services get authored directly under
  `src/doge/core/services/`, or do their existing `src/micro/*` /
  `src/macro/strategist.py` modules get wrapped as adapters first? The
  `macro ↔ micro` circular dependency (MODULARIZATION_PLAN.md:23) must be
  broken either way.
