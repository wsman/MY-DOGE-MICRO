# CDD: Market Data Storage

> **Module #2** — Category: **Foundation**
> **Slug**: `market-data-storage`
> **Status**: Reverse-documented (brownfield) — 2026-06-11
> **Depends on**: #1 `runtime-configuration`
> **Depended on by**: #3 `data-sources`, #4 `macro-strategy-engine`, #5 `micro-momentum-scanner`, #7 `research-insight-knowledge-base`, #8 `mcp-server`, #9 `fastapi-service`, #12 `clean-architecture-migration`
> **Source files reverse-documented**: `src/micro/database.py`, `src/doge/infrastructure/database/{duckdb.py,sqlite.py,repositories.py}`, `src/doge/core/ports/repository.py`, `data/views.sql`, `src/doge/config/settings.py`

---

## 1. Overview

Market Data Storage is the local-first persistence and analytical-read substrate for MY-DOGE-MICRO. It owns **five SQLite database files** (A-share prices, US-share prices, research/knowledge base, plus the auto-created DuckDB file and `views.sql`) and the **DuckDB analytical layer that zero-copy reads over the SQLite price databases** through attached databases and materialized views. Storage is consumed in two distinct shapes: (a) **writes** — incremental OHLCV ingestion from the TDX/yfinance adapters into `stock_prices` tables, plus report/insight/note inserts into the research DB; and (b) **reads** — DuckDB views (`vw_daily_enriched_cn`, `vw_rsrs_ranking_cn/us`, `vw_market_breadth_cn/us`, `vw_volume_anomalies_cn`, `vw_cross_sectional_return_cn`) that compute technical indicators and screening results on demand. The module is mid-migration: a new clean-architecture surface (`src/doge/...`) wraps storage behind `IStockRepository` / `IReportRepository` ports and `DuckDBConnection` / `SQLiteConnection` adapters, while the legacy surface (`src/micro/database.py`) still contains direct `sqlite3.connect(...)` calls used by the live ingestion path.

## 2. User Promise / JTBD

**Operator JTBD**: "When I sync market data and run a scan, every price I downloaded is durably stored on my local disk, queryable the same way by the desktop dashboard, the web console, the MCP tools, and the FastAPI service — and I never silently lose data or history because of a hidden write error or an undocumented retention rule."

**The module must reliably**:
- Persist A-share and US-share OHLCV bars to versioned local SQLite files whose locations are governed by env vars (`DOGE_DB_DIR`, `DOGE_CN_DB`, `DOGE_US_DB`, `DOGE_RESEARCH_DB`, `DOGE_DUCKDB_PATH`) from module #1.
- Persist macro/industry reports, AI insights, knowledge entities/relations, and stock notes to the research DB.
- Expose the same data to all interfaces through repository ports so that no interface layer opens a SQLite/DuckDB connection directly (ADR-0001 forbidden pattern `direct_sqlite_import_in_interface` / `direct_duckdb_connect_in_interface`).
- Make analytical reads (indicators, breadth, RSRS ranking, volume anomalies) deterministic and reproducible from the same underlying SQLite rows.

## 3. Detailed Behavior

### 3.1 Storage layout (the five SQLite artifacts + DuckDB + views)

Resolved through `Settings().db` (`src/doge/config/settings.py:23-38`):

| Artifact | Default path | Env override | Purpose |
|---|---|---|---|
| `cn_db` | `<PROJECT_ROOT>/data/market_data_cn.db` | `DOGE_CN_DB` | A-share `stock_prices` rows |
| `us_db` | `<PROJECT_ROOT>/data/market_data_us.db` | `DOGE_US_DB` | US-share `stock_prices` rows |
| `research_db` | `<PROJECT_ROOT>/data/research_insights.db` | `DOGE_RESEARCH_DB` | `macro_reports`, `research_reports`, `insights`, `knowledge_entities`, `knowledge_graph`, `stock_notes`, `stock_names` |
| `duckdb` | `<PROJECT_ROOT>/data/market.duckdb` | `DOGE_DUCKDB_PATH` | Analytical engine file; hosts the views |
| `views_sql` | `<PROJECT_ROOT>/data/views.sql` | (not overridable) | DDL executed by `DuckDBConnection.refresh_views()` |

> **Legacy note (Current State vs Target)**: `src/micro/database.py` also opens a fourth legacy path `data/market_data.db` as the *default* when no path is supplied (`get_db_connection`, `database.py:15-16`). This default is **not** wired to `DBConfig` and is superseded by `init_db_custom(db_path)` calls in `market_scanner.py`. The target is to delete the un-parameterized default and route every open through `DBConfig`. See Open Questions.

### 3.2 Write path — OHLCV ingestion (legacy live path)

The active ingestion caller is `src/micro/market_scanner.py`, which:
1. Calls `init_db_custom(db_path)` (`database.py:94-116`) — `CREATE TABLE IF NOT EXISTS stock_prices(...)` with composite PK `(ticker, date)`. Non-destructive.
2. For each ticker, builds a DataFrame and calls `save_stock_data_custom(df, db_path)` (`database.py:118-155`).

`save_stock_data_custom(data, db_path, retention_days=None)` behavior (`database.py:118-171`):
- Opens a connection via `get_db_connection`.
- When `retention_days is None`, resolves it from `Settings().market.retention_days` (`DOGE_RETENTION_DAYS`, default **730**) — falls back to 730 with a logged WARNING only if the `doge` config import itself fails. An explicit `retention_days=` arg overrides the config default.
- Computes `cutoff = now - retention_days` (default **730**) as `YYYY-MM-DD`.
- Reads `MAX(date)` for the first ticker in the frame as the incremental anchor.
- Appends only rows with `date > max_existing` (incremental upsert-like behavior, but PK-violating duplicate dates will raise, see Edge Cases).
- **Destructive retention**: `DELETE FROM stock_prices WHERE ticker=? AND date<cutoff` (`database.py:147-150`).
- **Error swallowing**: `except Exception as e: pass` (`database.py:152-153`) — write failures are **silently dropped**, no log, no re-raise. Flagged as a HIGH-RISK open question / acceptance criterion.
- `conn.close()` in `finally`.

`get_tickers_sync_state(db_path, tickers)` (`database.py:157-194`) returns `{ticker: {"latest_date", "row_count}}` for incremental download planning, batched at `BATCH=900` to respect the SQLite 999-parameter limit.

### 3.3 Write path — reports / insights / knowledge graph (legacy live path)

All open the research DB directly (Current State; target is `SQLiteReportRepository`):
- `save_macro_report(content, risk_signal, volatility, tags, analyst)` (`database.py:213-254`) — inserts into `macro_reports`, auto-migrates missing columns via `_ensure_columns` (`database.py:197-211`).
- `save_research_report(title, content, tags, analyst)` (`database.py:256-296`) — inserts into `research_reports`, auto-migrates.
- `save_insight(category, target, summary, full_content)` (`database.py:298-322`) — inserts into `insights`.
- `add_entity(name, entity_type)` (`database.py:373-398`) — `INSERT OR IGNORE` into `knowledge_entities`.
- `add_relationship(source, target, relation, insight_id)` (`database.py:400-424`) — inserts into `knowledge_graph`.

### 3.4 Cold-start initialization

`initialize_system_dbs()` (`database.py:426-522`) is invoked at app boot. It:
1. Recomputes `project_root` locally (forbidden pattern `_PROJECT_ROOT_recalculation`, ADR-0001; target routes through `Settings`).
2. Creates `data/` plus `macro_report/`, `micro_report/`, `research_report/` directories.
3. Creates `market_data_cn.db` and `market_data_us.db` with empty `stock_prices` if missing.
4. Creates `research_insights.db` with `macro_reports` and `research_reports` tables if missing.
5. Returns `True`/`False`; never raises (every step is `try/except`).

> **Schema drift**: `initialize_system_dbs` does **not** create `insights`, `knowledge_entities`, `knowledge_graph`, `stock_notes`, or `stock_names`. Those rely on `init_research_db()` (`database.py:52-92`) being called separately, or on the first insert path failing until the table exists. See Edge Cases.

### 3.5 Read path — clean-architecture surface (target; partial live)

**Port contracts** (`src/doge/core/ports/repository.py:10-68`):

- `IStockRepository` (implemented by `DuckDBStockRepository`, `repositories.py:16-110`):
  - `get_prices(ticker, market, days=20)` — CN reads `vw_daily_enriched_cn` (enriched); US reads raw `us.stock_prices`.
  - `get_overview(ticker, market)` — latest 10 prices from `cn/us.stock_prices` plus name from `JSONTickerNameCache`.
  - `get_sync_state(tickers)` — direct `sqlite3.connect(cn_db)` batched at `BATCH=900` (repository still opens SQLite directly rather than via `SQLiteConnection`; see Open Questions).
- `IReportRepository` (implemented by `SQLiteReportRepository`, `repositories.py:113-203`):
  - `list_macro_reports`, `get_macro_report`, `save_macro_report`, `save_research_report`, `add_note`, `search_notes`, `list_stock_names`. All via `SQLiteConnection` (`use_row_factory=True`).

> **Cache port**: ADR-0001 lists a `Cache` port; storage's only current cache usage is `JSONTickerNameCache` (`src/doge/infrastructure/cache/ticker_cache.py`) consumed inside `get_overview`. A formal `ICache` port is not yet declared in `repository.py` (Open Question).

### 3.6 Read path — DuckDB analytical layer

`DuckDBConnection` (`src/doge/infrastructure/database/duckdb.py:20-83`):
- `connect()` is a context manager that opens `market.duckdb` (read-only by default), sets `threads=4`, and `ATTACH`es the cn/us SQLite files via the sqlite extension with zero-copy reads.
- `execute(sql, params)` returns a pandas DataFrame.
- `refresh_views(con=None)` parses `data/views.sql`, splits on `;`, and runs each non-comment statement best-effort (individual view failures are swallowed, `duckdb.py:78-80`).
- Sets `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` to bound memory during pandas conversion (`duckdb.py:16-17`).
- Legacy shims `get_duckdb_connection` / `connect_duckdb` (`duckdb.py:87-96`) remain for `src/micro` and `src/ai_analysis` callers (e.g. `market_scanner._refresh_duckdb_views` calls `connect_duckdb()` + `run_views_sql(con)`).

### 3.7 Read path — refresh trigger

`market_scanner._refresh_duckdb_views()` (`market_scanner.py:29-34`) is invoked after every CN and US sync completes (`market_scanner.py:121, 148, 187, 212`), re-running `views.sql` against the just-written SQLite. This makes the views reflect the freshest rows. Views are not auto-refreshed on inserts that bypass the scanner.

## 4. Contracts / Data Model

### 4.1 Physical schema — SQLite `stock_prices` (cn + us)

```sql
CREATE TABLE stock_prices (
  ticker TEXT,
  date   TEXT,        -- 'YYYY-MM-DD' string
  open   REAL,
  high   REAL,
  low    REAL,
  close  REAL,
  volume INTEGER,
  amount REAL,
  PRIMARY KEY (ticker, date)
);
```
Source: `database.py:33-45` (legacy `init_db`), `database.py:99-112` (`init_db_custom`), `database.py:470-478` (cold-start). PK enforces uniqueness on `(ticker, date)`; `to_sql(..., if_exists='append')` will raise `IntegrityError` on a duplicate (see Edge Cases).

### 4.2 Physical schema — research DB tables

| Table | Columns | Created by | Source |
|---|---|---|---|
| `macro_reports` | `id PK, date, timestamp, tags, analyst, risk_signal, volatility, content` | `save_macro_report` / cold-start | `database.py:224-235`, `494-500` |
| `research_reports` | `id PK, date, timestamp, tags, analyst, title, content` | `save_research_report` / cold-start | `database.py:267-277`, `503-509` |
| `insights` | `id PK, created_at, category, target, summary, full_content` | `init_research_db` | `database.py:58-67` |
| `knowledge_entities` | `id PK, name UNIQUE, entity_type` | `init_research_db` | `database.py:70-76` |
| `knowledge_graph` | `id PK, source, target, relation, insight_id FK->insights(id) ON DELETE CASCADE` | `init_research_db` | `database.py:79-88` |
| `stock_notes` | `ticker, market, created_at, note_type, title, content, tags, price_at_note, source` (+ implicit PK) | `SQLiteReportRepository.add_note` | `repositories.py:170-186` |
| `stock_names` | `ticker, name_cn, sector` | not bootstrapped here | `repositories.py:199-203` |

### 4.3 Auto-migration behavior

`_ensure_columns(cursor, table_name, new_columns)` (`database.py:197-211`) issues `PRAGMA table_info` and `ALTER TABLE ... ADD COLUMN` for any missing column. It is invoked by `save_macro_report` (adds `tags`, `analyst`) and `save_research_report` (adds `timestamp`, `analyst`, `tags`). Failures print `[WARN]` but do not abort.

### 4.4 DuckDB analytical views (live enumeration, `mcp__doge-db__list_views`)

Enumerated from the live `market.duckdb`. DDL lives in `data/views.sql`.

| View | Rows | Columns |
|---|---:|---|
| `temp_vol_check` | 279,652 | `ticker, date, volume, avg_vol, vol_ratio` |
| `vw_cross_sectional_return_cn` | 600,690 | `ticker, date, return_pct, volume, close` |
| `vw_daily_enriched_cn` | 600,690 | `ticker, date, open, high, low, close, volume, amount, return_pct, ma_5, ma_10, ma_20, ma_60, atr_14, ma60_deviation, volatility_20d` |
| `vw_market_breadth_cn` | 118 | `date, advancers, decliners, unchanged, active, avg_return_pct, std_return_pct, advance_ratio` |
| `vw_market_breadth_us` | 122 | `date, advancers, decliners, unchanged, active, avg_return_pct, std_return_pct` |
| `vw_rsrs_ranking_cn` | 200 | `ticker, last_close, close_60d_ago, pct_change_60d, avg_vol_20d, avg_amt_60d_wan, rsrs, rsrs_points, rank` |
| `vw_rsrs_ranking_us` | 200 | `ticker, last_close, close_60d_ago, pct_change_60d, avg_vol_20d, avg_amt_60d_wan, rsrs, rsrs_points, rank` |
| `vw_volume_anomalies_cn` | 40,555 | `ticker, date, volume, avg_vol_20d, vol_ratio, intraday_return` |

Key DDL facts (cite `data/views.sql`):
- **RSRS view** (`data/views.sql:62-137`) takes the last **180** days of CN data (`INTERVAL 180 DAYS`, `views.sql:72`), filters tickers matching `^(00|30|60|68)` (`views.sql:74-77`), requires `>= 61` data points and `avg_vol_20d > 500000` for CN (`> 50000` for US, `views.sql:330`), ranks top 200 by `pct_change_60d`, then computes `rsrs = REGR_R2(rn, close) * sign(REGR_SLOPE(rn, close))` over the most recent 18 bars (`views.sql:114-122`). **This matches the canonical RSRS formula in module #5** (`src/micro/momentum_scanner.py:47-71`).
- **Volume anomalies** (`views.sql:142-173`) keep a wide window from `2025-01-01` and surface rows where `vol_ratio >= 2.0`.
- **Daily enriched** (`views.sql:202-253`) computes `return_pct`, `ma_5/10/20/60`, `atr_14`, `ma60_deviation`, `volatility_20d` over the last 365 days.
- **Market breadth CN** uses `INTERVAL 730 DAYS` (`views.sql:23`); **US breadth** uses 365 days (`views.sql:266`) and **US RSRS** uses 180 days (`views.sql:305`). The 730-day CN breadth window is the longest view horizon in the system (root cause of the §9.2 retention-vs-window latent bug).

### 4.5 Port contract signatures (target API surface)

From `src/doge/core/ports/repository.py`:

```python
class IStockRepository(ABC):
    def get_prices(self, ticker: str, market: str, days: int = 20) -> List[dict]: ...
    def get_overview(self, ticker: str, market: str) -> dict: ...
    def get_sync_state(self, tickers: List[str]) -> dict[str, dict]: ...

class IReportRepository(ABC):
    def list_macro_reports(self, limit: int = 100) -> List[dict]: ...
    def get_macro_report(self, report_id: int) -> Optional[dict]: ...
    def save_macro_report(self, *, content, risk_signal, volatility, tags, analyst) -> None: ...
    def save_research_report(self, *, title, content, tags, analyst) -> None: ...
    def add_note(self, *, ticker, content, market, note_type, title, tags, price_at_note, source) -> int: ...
    def search_notes(self, query: str, limit: int = 50) -> List[dict]: ...
    def list_stock_names(self) -> List[dict]: ...
```

### 4.6 Error / exit-code contract (Current State)

- `save_stock_data_custom`: **swallows all exceptions** (returns silently). No exit code. Caller cannot tell success from failure.
- `save_macro_report`, `save_research_report`, `save_insight`, `add_entity`, `add_relationship`: print `[ERR] ...` and continue; no raise.
- `initialize_system_dbs`: returns `False` on any failure; never raises.
- `get_tickers_sync_state`: prints `[ERR]` and returns the all-zero sentinel on failure.
- `DuckDBConnection.refresh_views`: swallows per-statement errors silently.
- **Target (Migration)**: every write path raises a typed exception (`StorageWriteError`) or returns a structured result; every swallowed exception is replaced by a `logger.warning`/`logger.error` with ticker + cause.

### 4.7 Proposed registry entries (BLOCKING Phase 5 — do NOT write yet)

The following constants/formulas/entities should later be promoted to `docs/registry/entities.yaml` or `docs/registry/architecture.yaml`. Listed here for review only:

- **Entities (`entities.yaml`)**:
  - `storage.sqlite_db.cn` — `market_data_cn.db` (path, env `DOGE_CN_DB`)
  - `storage.sqlite_db.us` — `market_data_us.db` (env `DOGE_US_DB`)
  - `storage.sqlite_db.research` — `research_insights.db` (env `DOGE_RESEARCH_DB`)
  - `storage.duckdb.path` — `market.duckdb` (env `DOGE_DUCKDB_PATH`)
  - `storage.duckdb.views_sql` — `data/views.sql`
  - `storage.view.vw_daily_enriched_cn` (columns as enumerated)
  - `storage.view.vw_rsrs_ranking_cn` / `vw_rsrs_ranking_us`
  - `storage.view.vw_market_breadth_cn` / `vw_market_breadth_us`
  - `storage.view.vw_volume_anomalies_cn`
  - `storage.view.vw_cross_sectional_return_cn`
  - `storage.view.temp_vol_check`
  - `storage.table.stock_prices` (schema + PK `(ticker, date)`)
  - `storage.table.macro_reports`, `research_reports`, `insights`, `knowledge_entities`, `knowledge_graph`, `stock_notes`, `stock_names`
- **Architecture (`architecture.yaml`)**:
  - `port.IStockRepository`, `port.IReportRepository` (method signatures above)
  - `adapter.DuckDBStockRepository`, `adapter.SQLiteReportRepository`
  - `adapter.DuckDBConnection`, `adapter.SQLiteConnection`
  - `knob.retention_days = 180` (operational risk: destructive)
  - `knob.tdx.MAX_DAYS = 120` (operational risk: ingest trim ceiling)
  - `knob.sqlite.BATCH = 900` (parameter-limit batch size)
  - `knob.duckdb.threads = 4`
  - `constraint.rsrs.window = 18`, `constraint.rsrs.min_points = 10`, `constraint.rsrs.universe_lookback_days = 180`

## 5. Edge Cases

- **Duplicate `(ticker, date)` on append**: `save_stock_data_custom` only appends `date > max_existing`, but if `to_sql` is called with the full frame (no prior rows), a re-run that overlaps existing dates raises `sqlite3.IntegrityError`. **Current State**: the `except Exception: pass` swallows it — the row is not inserted and no error surfaces. **Target**: log and raise a typed error.
- **Empty DataFrame**: `save_stock_data_custom` reads `data['ticker'].iloc[0]` guarded by `if not data.empty` (else `'UNKNOWN'`). If empty, the `SELECT MAX(date)` runs for ticker `'UNKNOWN'`; the subsequent append is a no-op (empty frame), the DELETE matches nothing. Safe but wasteful.
- **Retention `180` vs ingest ceiling `120`** (HIGH-RISK inconsistency): `tdx_loader.MAX_DAYS=120` trims each parsed file to the last 120 bars (`src/micro/tdx_loader.py:64, 136-137`), but `save_stock_data_custom(retention_days=180)` deletes anything older than 180 calendar days. Because ingestion only ever provides ~120 bars, the 180-day retention rarely triggers — but a manual backfill or yfinance history longer than 180 days would be silently truncated. See Configuration Knobs + Open Questions.
- **`date` column is TEXT**: comparisons use lexicographic `YYYY-MM-DD` ordering, which is correct only for zero-padded ISO dates. A non-ISO date string silently compares wrongly.
- **Missing research tables at cold start**: `initialize_system_dbs` does not create `insights`, `knowledge_entities`, `knowledge_graph`, `stock_notes`, `stock_names`. Calling `save_insight` before `init_research_db()` raises `sqlite3.OperationalError: no such table` and is swallowed/printed per caller. **Target**: cold start must create every table the read/write ports reference.
- **Concurrent writers**: SQLite default journal mode allows only one writer; two scanners writing the same `cn_db` concurrently will hit `database is locked`. No `WAL` mode, no `busy_timeout` is set. **Target**: single-writer contract documented; enable WAL.
- **DuckDB refresh partial failure**: `refresh_views` swallows per-statement errors, so a malformed view leaves the previous version (or none) with no signal. **Target**: collect failures and report at least one aggregate warning.
- **`get_sync_state` opens `cn_db` even for US tickers** (`repositories.py:86-87`): the comment claims "all tickers tracked there" — this is incorrect for US tickers and returns `latest_date=None` for any US code. **Target**: route by market.
- **Auto-migration drops data type info**: `_ensure_columns` adds columns as the supplied type but does not backfill; legacy rows get `NULL` for the new column.
- **Read-only DuckDB attach + `refresh_views`**: `refresh_views` re-opens the DuckDB file `read_only=False` when no connection is supplied (`duckdb.py:62-66`). If the file is held open read-only elsewhere (e.g. by an MCP query), the refresh connect may fail or block.

## 6. Dependencies

**Upstream (this module depends on):**
- **#1 `runtime-configuration`** — `Settings`, `DBConfig` (`src/doge/config/settings.py:23-38`) is the single source of truth for all paths. Every adapter reads `get_settings()`.
- **Python packages**: `sqlite3` (stdlib), `duckdb==1.4.4`, `pandas`, `scipy` (transitively, via RSRS view alignment with module #5).
- **DuckDB `sqlite` extension** — required for `ATTACH ... (TYPE sqlite)` zero-copy reads (`duckdb.py:41-46`, `views.sql:9-10`).

**Downstream (consumers):**
- **#3 `data-sources`** — `market_scanner.py` is the primary writer (`init_db_custom`, `save_stock_data_custom`, `_refresh_duckdb_views`).
- **#4 `macro-strategy-engine`** — reads `vw_market_breadth_*`, `vw_daily_enriched_cn`; writes `macro_reports`.
- **#5 `micro-momentum-scanner`** — canonical RSRS formula (`momentum_scanner.py:47-71`); the `vw_rsrs_ranking_*` views reproduce it in SQL.
- **#7 `research-insight-knowledge-base`** — owns `stock_notes`, `stock_names`. (The four AI/research tables that share the same physical DB — `insights`, `knowledge_entities`, `knowledge_graph`, `research_reports` — are owned by **this storage module's** legacy `src/micro/database.py` write functions `save_insight`, `add_entity`, `add_relationship`, `save_research_report`, and are **not** claimed by Module #7. Module #7's `add_note`/`search_notes` live only in `src/ai_analysis/stock_notes.py`, which touches no other table.)
- **#8 `mcp-server`** — consumes `DuckDBConnection` + repositories for tool responses.
- **#9 `fastapi-service`** — `src/api/routers/scan.py` imports `init_db_custom` directly (`scan.py:150`, used at `scan.py:153`) and delegates writes to `MarketScanner` (`scan.py:246`), which in turn calls `save_stock_data_custom` — so the ADR-0001 forbidden pattern is the **direct `init_db_custom` import in the interface layer** plus **transitive direct writes via the scanner** (there is no `save_stock_data_custom` import anywhere in `src/api/`). Target: route through services/ports.
- **#12 `clean-architecture-migration`** — ADR-0001 governs the boundary this module must enforce.

**Documents:**
- `docs/architecture/adr-0001-brownfield-clean-architecture.md` (layer rules, forbidden patterns).
- `docs/architecture/adr-0003-storage-repository-contract.md` (this module's contract decision; **Status: Proposed as of 2026-06-11 — not yet binding**, see Acceptance Criteria §8).

## 7. Configuration Knobs

All env vars are read by `_env_path` (`settings.py:18-20`). Knobs not yet in `DBConfig` are flagged.

| Knob | Default | Valid range / type | Env owner | Operational risk |
|---|---|---|---|---|
| `DOGE_DB_DIR` | `<PROJECT_ROOT>/data` | writable dir path | operator | None; must be writable at boot |
| `DOGE_CN_DB` | `<DB_DIR>/market_data_cn.db` | path | operator | None |
| `DOGE_US_DB` | `<DB_DIR>/market_data_us.db` | path | operator | None |
| `DOGE_RESEARCH_DB` | `<DB_DIR>/research_insights.db` | path | operator | None |
| `DOGE_DUCKDB_PATH` | `<DB_DIR>/market.duckdb` | path | operator | Must be writable for `refresh_views` |
| `retention_days` (`save_stock_data_custom`) | **730** | int >= 730 | env `DOGE_RETENTION_DAYS` (read by `Settings().market.retention_days`, `settings.py` `MarketConfig`) | **DESTRUCTIVE** — each write deletes rows older than N days for that ticker. Must be >= 730 to satisfy the widest view window (`vw_market_breadth_cn`, `views.sql:23`). |
| `MAX_DAYS` (`tdx_loader`) | **120** | int > 0 | **HARDCODED** class attr (`tdx_loader.py:64`) | Ingest ceiling — only the last 120 bars are ever parsed/written. Inconsistent with `retention_days=180` (see Edge Cases). |
| `BATCH` (`get_tickers_sync_state`, `DuckDBStockRepository.get_sync_state`) | **900** | int < 999 | hardcoded (`database.py:171`, `repositories.py:91`) | Below SQLite's 999-host-parameter limit; safe but must not be raised above 998. |
| DuckDB `threads` | **4** | int >= 1 | hardcoded (`duckdb.py:39`) | Memory/CPU contention; bounds OpenBLAS to 1 thread separately (`duckdb.py:16-17`). |
| `MCPConfig.tool_timeout` | 30s | int seconds | env (module #1) | Read-side budget; long view scans must fit. |

**Registry proposals** (BLOCKING Phase 5 — enumerated, not written):
- `knob.retention_days`, `knob.tdx.MAX_DAYS`, `knob.sqlite.BATCH`, `knob.duckdb.threads` (see §4.7).

## 8. Acceptance Criteria

Contract / data-model checks:
- [ ] `mcp__doge-db__list_views` returns exactly the 8 views listed in §4.4 with the documented column sets.
- [ ] `stock_prices` PK `(ticker, date)` rejects a duplicate insert with `sqlite3.IntegrityError` (regression test).
- [ ] `DuckDBStockRepository.get_prices("000001","cn",20)` returns 20 rows from `vw_daily_enriched_cn` ordered `date DESC`.
- [ ] `SQLiteReportRepository.save_macro_report` then `list_macro_reports` round-trips the row.
- [ ] `_ensure_columns` adds a missing column idempotently and does not error when the column exists.

Migration checks (ADR-0001 / ADR-0003):
- [ ] No file under `src/api/`, `src/doge/interfaces/`, or `src/interface/` imports `sqlite3` or `duckdb` directly (`grep -rnE "import sqlite3|import duckdb|sqlite3.connect|duckdb.connect"` returns zero hits in interface layers).
- [ ] `src/micro/database.py` write failures are **logged** (not `pass`); a test asserts a warning is emitted when `to_sql` raises.
- [x] `retention_days` is configurable via `DOGE_RETENTION_DAYS`; default documented (730, shipped S002-007). Regression guard: `tests/migration/test_retention_view_window_safety.py` asserts `max(INTERVAL N DAYS) <= retention_days`.
- [ ] Cold-start `initialize_system_dbs()` creates every table referenced by `IReportRepository` and `IStockRepository` (including `insights`, `stock_notes`, `stock_names`).

Workflow / observability:
- [ ] After a scanner run, `vw_rsrs_ranking_cn` reflects the just-written rows (refresh actually ran).
- [ ] `DuckDBConnection.connect()` is a context manager that closes the connection on exit (test with `con.closed`).
- [ ] A write that hits `database is locked` is surfaced (not swallowed) when two writers race.

Docs:
- [ ] This CDD cites real `file:line` for every claim (auditable).
- [ ] ADR-0003 is `Accepted` before any story references it.

## 9. Integration Requirements

> Appended per the special instructions for data/API modules.

### 9.1 Write paths

- **Single logical writer per SQLite DB**: ingestion is performed by `market_scanner.py` only, calling `init_db_custom` then `save_stock_data_custom`. No other module should write to `market_data_cn.db` / `market_data_us.db`. **Target (Migration)**: enforce via `IStockRepository.save_prices(...)`; the legacy free function is removed.
- **Reports/notes**: written only through `IReportRepository` (`save_macro_report`, `save_research_report`, `add_note`) or, until migration completes, the legacy `save_*` functions in `database.py`. All writes target `research_insights.db`.
- **Incremental semantics**: `save_stock_data_custom` appends `date > max_existing` only — it is **not** an upsert. Corrections to historical bars require a manual delete first.
- **Atomicity**: each `save_*` call commits once before close; there is no cross-table transaction. A failure between a price write and a refresh leaves the DuckDB views stale until the next refresh.

### 9.2 Retention

- `retention_days` (default **730**, env `DOGE_RETENTION_DAYS`) deletes rows older than N calendar days **per ticker** on every write (`database.py:147-150`). This is **destructive and irreversible**; there is no archive step. Any backfill history older than 730 days is lost the next time that ticker is synced. Operational guidance: keep `DOGE_RETENTION_DAYS` >= the longest analysis window actually used (current views use up to **730 days** for `vw_market_breadth_cn` (`views.sql:23`); `vw_daily_enriched_cn` / `vw_cross_sectional_return_cn` use 365 days; US breadth uses 365 and US RSRS uses 180). **Warm-up caveat**: `tdx_loader.MAX_DAYS=120` means only ~120 bars are ingested per ticker, so breadth fills toward 730 days gradually post-fix; the 730 default does not retroactively backfill history.

### 9.3 Concurrency model

- **SQLite writers**: serialized by SQLite's file lock. No `WAL`, no `busy_timeout` configured. Concurrent writers will receive `database is locked`. Target: enable WAL + `busy_timeout` and document the single-writer contract.
- **DuckDB readers**: `DuckDBConnection` defaults to `read_only=True` so multiple MCP/API readers can coexist. `refresh_views` opens `read_only=False` and must be the only writer to `market.duckdb`.
- **Cross-process**: no inter-process locking beyond SQLite/DuckDB file locks. Two operator sessions running scans simultaneously are unsafe.

### 9.4 Refresh / zero-copy behavior

- **Zero-copy**: DuckDB attaches the SQLite files via the sqlite extension and reads rows directly — no duplication of OHLCV into DuckDB. Only the view definitions (and DuckDB's own metadata) live in `market.duckdb`.
- **Refresh trigger**: `views.sql` is re-executed after each scan (`market_scanner._refresh_duckdb_views`). Views are `CREATE OR REPLACE`, so refresh is idempotent. Reads between a SQLite write and the next refresh return stale results.
- **Failure mode**: per-view failures are swallowed (`duckdb.py:78-80`); a partially-refreshed view set is indistinguishable from a fully-refreshed one to the caller.

### 9.5 Retry / backoff

- Storage itself performs **no retries** — retry/backoff lives in module #3 (`data-sources`) for TDX/yfinance fetches. Storage calls (`to_sql`, `INSERT`) are single-attempt. A transient `database is locked` is not retried.
- **Target**: the repository layer should retry lock errors with a small bounded backoff (e.g. 3 attempts, 100ms) before surfacing.

---

## Open Questions (aspirational — flagged for Phase 5 reconciliation)

1. **RESOLVED (2026-06-12, story S002-007 / TR-006)** — `retention_days` is now env-configurable via `DOGE_RETENTION_DAYS` (read by `Settings().market.retention_days`) with a default of **730**, which satisfies the widest view window (`vw_market_breadth_cn`, `views.sql:23`). The legacy silent 180-day ceiling is lifted: `save_stock_data_custom` resolves its `retention_days` from `Settings()` when no explicit arg is passed. **Warm-up caveat (NOT fixed by this story)**: `tdx_loader.MAX_DAYS=120` means raising retention does NOT backfill history — breadth will fill toward 730 days gradually as new bars accumulate post-fix. Operators may perceive the fix as inert on day one. `MAX_DAYS` is a separate lockstep invariant (4 call sites, `entities.yaml`) and is out of scope for S002-007.
2. **Swallowed write exception** (`database.py:152-153`) — must become a logged, typed error. Blocking acceptance criterion.
3. **Legacy `data/market_data.db` default** (`database.py:15-16`) — unused by the live scanner; delete after confirming no callers.
4. **`initialize_system_dbs` does not create all tables** — should it, or should each repository lazily create its table?
5. **`DuckDBStockRepository.get_sync_state` always queries `cn_db`** even for US tickers — bug or intended?
6. **No WAL / `busy_timeout`** — should the target contract enable WAL?
7. **`ICache` port** — ADR-0001 mentions a `Cache` port; `JSONTickerNameCache` is used but not behind a declared port. Formalize?
8. **`stock_names` bootstrap** — who creates and populates this table? (Currently only read by `list_stock_names`; no writer in this module.)
9. **`temp_vol_check` view** — appears in `list_views` but is not in `data/views.sql`. Where is it defined? (Likely created ad-hoc; needs to be added to `views.sql` or removed.)
