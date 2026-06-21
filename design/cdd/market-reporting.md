# CDD: Market Reporting (Module #6)

> **Module #6** — Category: **Feature**
> **Slug**: `market-reporting`
> **Status**: Designed
> **Last Verified**: 2026-06-21
> **Notes**: Reverse-documented from brownfield reporting code; BUG E tests landed 2026-06-12.
> **Depends on**: #1 `runtime-configuration`, #2 `market-data-storage`
> **Depended on by**: #7 `research-insight-knowledge-base` (shares `src/ai_analysis/__init__.py` and `stock_names`/`stock_notes` tables), #9 `fastapi-service`, #10 `pyqt-desktop-dashboard`
> **Source files reverse-documented**: `src/ai_analysis/__init__.py` (shared DB connection layer), `src/ai_analysis/market_overview.py`, `src/ai_analysis/anomaly_detection.py`, `src/ai_analysis/catalog_generator.py`, `src/ai_analysis/fetch_names.py`
> **NOT documented here (cross-references)**: `src/ai_analysis/stock_notes.py` (owned by Module #7 — see `design/cdd/research-insight-knowledge-base.md`); the DeepSeek LLM client (owned by Module #4 — `src/macro/strategist.py`); the LLM-based industry-chain clustering `IndustryAnalyzer` (owned by Module #5 — `src/micro/industry_analyzer.py`).
> **Related ADRs**: [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) (clean architecture, forbidden patterns), [ADR-0002](../../docs/architecture/adr-0002-centralized-configuration.md) (config centralization)

---

## 1. Overview

Market Reporting is the **pure SQL report-generation module** that reads the DuckDB analytical views owned by Module #2 (`market-data-storage`) and emits Markdown market-overview and anomaly-detection reports plus a JSON data catalog. It lives under `src/ai_analysis/` and is composed of four scripts — `market_overview.py` (the daily market-panorama report: trading-day statistics, 90-day market breadth, RSRS Top/Bottom 20, volume spikes), `anomaly_detection.py` (volume-ratio anomalies, price gaps, and still-ongoing consecutive up/down streaks), `catalog_generator.py` (a JSON manifest of every SQLite table and DuckDB view, written to `data/catalog.json`), and `fetch_names.py` (a yfinance-driven enrichment job that backfills `stock_names` rows used as ticker labels by other reports). The shared `src/ai_analysis/__init__.py` provides `connect_duckdb`, `run_views_sql`, the env-overridable path constants (`CN_DB`, `US_DB`, `RESEARCH_DB`, `DUCKDB_PATH`, `VIEWS_SQL`, `REPORT_DIR`), `normalize_ticker`, and the SQLite/DuckDB statistics helpers (`get_sqlite_stats`, `get_duckdb_view_stats`).

> **Naming clarification (resolves the prior "AI Industry Analysis" misnomer):**
> This module has **NO LLM**. Every report in `src/ai_analysis/{market_overview,anomaly_detection,catalog_generator,fetch_names}.py` is produced by SQL queries against the DuckDB views; there is no model call, no prompt, and no generated prose anywhere in these four files.
> - The project's **real LLM client** is Module #4 — `DeepSeekStrategist` in `src/macro/strategist.py` (constructs `openai.OpenAI(base_url="https://api.deepseek.com", model="deepseek-chat")`).
> - The **LLM-based industry-chain clustering** (`IndustryAnalyzer.run_analysis`, which calls DeepSeek to produce an "industry prosperity" Markdown report) lives in Module #5 — `src/micro/industry_analyzer.py` — and is documented in `design/cdd/micro-momentum-scanner.md` §3.8.
>
> The prior module name "AI Industry Analysis" was a misnomer for this code: none of the four scripts here performs AI or industry analysis. Renaming it to "Market Reporting" makes the dependency graph honest — Module #6 reads Module #2's storage views and writes Markdown/JSON reports, nothing more.

## 2. User Promise / JTBD

**Operator JTBD**: "Every morning (or on demand), point the platform at my freshly synced market data and hand me a single Markdown page that shows, in one glance, today's advance/decline line, the strongest- and weakest-trend names by RSRS, and any abnormal volume, price gaps, or ongoing win/loss streaks — plus a JSON catalog of my entire local data footprint — without me writing any SQL."

**The module must reliably**:
- Produce a Markdown market-overview report anchored on the **actual latest data date in `cn.stock_prices`** (not the system clock), so a stale-but-present database still yields a coherent report (`market_overview.py:122-124`).
- Produce a Markdown anomaly-detection report with three independent detectors (volume ratio, price gap, consecutive streaks), each parameterizable from the CLI, and each tolerant of an empty result set (the report still writes the section header with a "_无符合条件的结果_" placeholder — `anomaly_detection.py:130-155`).
- Refresh the DuckDB views before each report run (`run_views_sql(con)` is called in every `generate()`), so the report reflects the most recent ingestion.
- Emit a deterministic JSON catalog (`catalog.json`) describing every SQLite table and DuckDB view currently present, suitable for tooling and MCP introspection (`catalog_generator.py:26-90`).
- Backfill missing ticker names into `stock_names` from yfinance with a local JSON cache and graceful per-ticker fallback, never crashing the batch on a single network failure (`fetch_names.py:58-97`).

**The module does NOT**:
- Call any LLM, generate any prose interpretation, or perform any industry analysis. (LLM work is Module #4; industry clustering is Module #5.)
- Persist reports to the research database. (Reports are written to `ai_report/*.md` files only; DB archiving is Module #7's `save_research_report` concern.)
- Modify the price databases. All report queries are read-only SELECTs against attached SQLite via DuckDB views.

## 3. Detailed Behavior

All file:line citations are against the current brownfield state on the `cdd-adoption-2026-06-11` branch.

### 3.1 Shared connection layer — `src/ai_analysis/__init__.py`

| Symbol | Location | Responsibility |
|---|---|---|
| `PROJECT_ROOT` | `__init__.py:21` | `Path(__file__).resolve().parents[2]` — resolves to the repo root |
| `_env_path(name, default)` | `__init__.py:24-26` | Returns `Path(env)` when the env var is set, else `default` |
| `DB_DIR` | `__init__.py:30` | `DOGE_DB_DIR` override or `<root>/data` |
| `CN_DB` / `US_DB` / `RESEARCH_DB` | `__init__.py:31-33` | `DOGE_CN_DB` / `DOGE_US_DB` / `DOGE_RESEARCH_DB` overrides |
| `DUCKDB_PATH` | `__init__.py:34` | `DOGE_DUCKDB_PATH` override |
| `VIEWS_SQL` | `__init__.py:35` | `<DB_DIR>/views.sql` (NOT env-overridable) |
| `REPORT_DIR` | `__init__.py:36` | `<PROJECT_ROOT>/ai_report` |
| `normalize_ticker(ticker, market="cn")` | `__init__.py:39-62` | Validates + suffixes a bare A-share code (`.SH`/`.SZ`/`.BJ`) |
| `ensure_report_dir()` | `__init__.py:65-66` | `REPORT_DIR.mkdir(parents=True, exist_ok=True)` |
| `connect_duckdb(read_only=False)` | `__init__.py:97-114` | Legacy direct-connection helper: opens `DUCKDB_PATH`, ATTACHes `cn` + `us` SQLite read-only-or-not by flag. Returns an **open** connection the caller must `.close()`. |
| `run_views_sql(con=None)` | `__init__.py:117-138` | Reads `VIEWS_SQL`, splits on `;`, executes each non-comment statement; per-statement errors are caught and printed, never raised (view-refresh failures are non-fatal). |
| `query_view` / `query_sql` | `__init__.py:141-155` | Convenience wrappers around the `get_duckdb_connection()` context manager (returns DataFrames). Not used by the four report scripts but exported for MCP/API consumption. |
| `get_sqlite_stats(db_path)` | `__init__.py:158-186` | Returns `{table: {row_count, columns, date_range, distinct_tickers}}` for every table in a SQLite DB. Used by `catalog_generator`. |
| `get_duckdb_view_stats(con)` | `__init__.py:189-201` | Returns `{view: {row_count}}` for every DuckDB view; `row_count` is `None` when a view errors. Used by `catalog_generator`. |

> **Migration note (Current State vs Target):** `connect_duckdb` and `run_views_sql` are the legacy direct-connection surface (ADR-0001 forbidden pattern `direct_duckdb_connect_in_interface`). The clean-architecture replacement is `get_duckdb_connection()` (`__init__.py:69-94`) and the `DuckDBConnection` adapter in Module #2 (`src/doge/infrastructure/database/duckdb.py`). The four report scripts still call the legacy pair; routing them through the adapter is an open migration target (Section 8).

### 3.2 Market overview report — `src/ai_analysis/market_overview.py`

Entrypoint: `generate()` (`market_overview.py:112-179`), or `python src/ai_analysis/market_overview.py` from the CLI (no arguments).

Report assembly order:
1. **Anchor on the data's latest date** (`market_overview.py:122-124`): `max_d = con.execute("SELECT MAX(CAST(date AS DATE)) FROM cn.stock_prices").fetchone()[0]`. From `max_d`, compute `cutoff_10d = max_d - 10 days` (for trading-day stats) and `cutoff_90d = max_d - 90 days` (for breadth).
2. **Trading-day statistics** — `market_stats(con, cutoff)` (`market_overview.py:86-109`): a window-function query over `cn.stock_prices` that classifies each bar as `up`/`down`/`flat` relative to its prior close, then groups by date returning `date, advancers, decliners, avg_return_pct, advance_ratio` for the trailing ~10 days.
3. **Market breadth (90-day)** — `market_breadth(con, cutoff)` (`market_overview.py:30-56`): the same classification plus `unchanged`, `active`, `std_return_pct`, and `advance_ratio` over the trailing ~90 days.
4. **RSRS Top 20** — `rsrs_top20(con)` (`market_overview.py:59-65`): `SELECT rank, ticker, rsrs, last_close, pct_change_60d, avg_vol_20d FROM vw_rsrs_ranking_cn WHERE rank <= 20 ORDER BY rank`. (View defined in Module #2 / `data/views.sql:62-137`.)
5. **RSRS Bottom 20** — `rsrs_bottom20(con)` (`market_overview.py:68-74`): same view, `ORDER BY rank DESC LIMIT 20`.
6. **Volume spikes** — `volume_spikes(con)` (`market_overview.py:77-83`): `SELECT ticker, date, volume, avg_vol_20d, vol_ratio, intraday_return FROM vw_volume_anomalies_cn ORDER BY vol_ratio DESC LIMIT 15`. (View defined in `data/views.sql:142-171+`.)

Output: `ai_report/market_overview_YYYYMMDD.md` (5 sections, each rendered via `df.to_markdown(index=False)`; an empty section writes a placeholder line). The report's first line is a `> 生成时间: ... | 数据截止: <max_d>` header. Returns the output path.

### 3.3 Anomaly detection report — `src/ai_analysis/anomaly_detection.py`

Entrypoint: `generate(min_ratio=3.0, gap_threshold=5.0, recent_days=3)` (`anomaly_detection.py:102-158`), or `python src/ai_analysis/anomaly_detection.py [--days N] [--min-ratio F] [--gap-threshold F]`.

Three independent detectors:
1. **Volume anomalies** — `volume_anomalies(con, min_ratio=3.0, cutoff=None)` (`anomaly_detection.py:23-37`): `SELECT ... FROM vw_volume_anomalies_cn WHERE vol_ratio >= ? [AND date >= cutoff] ORDER BY vol_ratio DESC LIMIT 30`. The optional cutoff lets the report scope to a recent window.
2. **Price gaps** — `price_gaps(con, gap_threshold=5.0, cutoff=None)` (`anomaly_detection.py:40-60`): a window-function query that computes `(open - prev_close)/prev_close * 100` per ticker-day, returns rows where `ABS(gap_pct) >= gap_threshold`, ordered by `date DESC, ABS(gap_pct) DESC`, `LIMIT 30`. Columns: `ticker, date, open, prev_close, close, gap_pct, return_pct`.
3. **Consecutive extremes** — `consecutive_extremes(con, direction, min_days=5, cutoff=None)` (`anomaly_detection.py:63-99`): a gaps-and-islands query that finds runs of consecutive `down` (or `up`) closes of length `>= min_days`, then filters to streaks whose `to_date` is within 2 days of the data's `MAX(date)` (i.e. **still ongoing**). Columns: `ticker, from_date, to_date, streak_days`. `LIMIT 30`.

The `generate()` function computes `cutoff = max_d - max(30, recent_days + 5) days` (`anomaly_detection.py:114`) so all three detectors share a common recent window, runs `down` and `up` streak detection separately, and writes `ai_report/anomaly_detection_YYYYMMDD.md` (4 sections). The report header records the thresholds in effect (`anomaly_detection.py:126-127`).

### 3.4 Data catalog — `src/ai_analysis/catalog_generator.py`

Entrypoint: `generate_catalog()` (`catalog_generator.py:26-90`), or `python src/ai_analysis/catalog_generator.py`.

Behavior: opens a DuckDB connection, refreshes views, then calls `get_sqlite_stats` for each of the three SQLite DBs (`CN_DB`, `US_DB`, `RESEARCH_DB`) and `get_duckdb_view_stats(con)` for the DuckDB views. Assembles a `catalog` dict with `version`, `databases` (3 SQLite entries with path/engine/description/tables), `duckdb` (path/`views_sql`/engine/description/views/usage example), `analysis_scripts` (pointers to the three report scripts), and `report_directory`. Adds `generated_at = datetime.now()`. Writes JSON to `data/catalog.json` (`catalog_generator.py:78-80`). Prints a CN/US ticker+row count summary and the view count; returns the catalog dict.

### 3.5 Name enrichment — `src/ai_analysis/fetch_names.py`

Entrypoint: CLI only — `python src/ai_analysis/fetch_names.py [--force] [--from-cache] [--market cn|us]`.

Two enrichment sources:
- `fetch_from_meta_cache()` (`fetch_names.py:100-120`): imports names from the existing `data/meta_cache.json` (the same cache `IndustryAnalyzer` writes in Module #5) into `stock_names`, skipping tickers that already have a name.
- `fetch_batch_yfinance(tickers, market, batch_size=20, delay=2.0)` (`fetch_names.py:58-97`): for each ticker missing a name, calls `yf.Ticker(t).info`, reads `longName`/`shortName`/`sector`/`industry`, and `save_name(...)`s it; on any per-ticker exception, falls back to saving the ticker itself as the name (`fetch_names.py:86-87`). `time.sleep(0.3)` between tickers and `delay` between batches to respect rate limits. `--force` clears the existing `stock_names` rows for the market first (`fetch_names.py:137-143`).

`get_all_tickers(market)` (`fetch_names.py:24-32`) reads `DISTINCT ticker FROM stock_prices` from the market's SQLite DB. `save_name` (`fetch_names.py:45-55`) does `INSERT OR REPLACE INTO stock_names (ticker, name_cn, name_en, market, sector, industry, updated_at)`.

> **Note:** `stock_names` and `stock_notes` tables both live in `research_insights.db` and are owned by Module #7 (`research-insight-knowledge-base`). This script writes to `stock_names`; it does not touch `stock_notes`.

## 4. Contracts / Data Model

### 4.1 Inputs (read)

| Source | Table/View | Columns consumed | Owner |
|---|---|---|---|
| DuckDB view | `vw_rsrs_ranking_cn` | `rank, ticker, rsrs, last_close, pct_change_60d, avg_vol_20d` | Module #2 (`data/views.sql:62-137`) |
| DuckDB view | `vw_volume_anomalies_cn` | `ticker, date, volume, avg_vol_20d, vol_ratio, intraday_return` | Module #2 (`data/views.sql:142+`) |
| DuckDB-attached SQLite | `cn.stock_prices` | `ticker, date, open, close, volume, amount` | Module #2 |
| SQLite | `research_insights.db.stock_names` | `ticker, name_cn, name_en, market, sector, industry, updated_at` | Module #7 (read+write by this script) |
| SQLite | `market_data_{cn,us}.db.stock_prices` | `DISTINCT ticker` | Module #2 |
| File | `data/views.sql` | All `CREATE OR REPLACE VIEW` statements | Module #2 |
| File | `data/meta_cache.json` | `{ticker: {name, sector}}` | Module #5 (`IndustryAnalyzer`) |
| Network | `yfinance.Ticker().info` | `longName`, `shortName`, `sector`, `industry` | External |

### 4.2 Outputs (written)

| Output | Path | Format | Producer |
|---|---|---|---|
| Market overview report | `ai_report/market_overview_YYYYMMDD.md` | Markdown (5 sections, `df.to_markdown`) | `market_overview.generate()` |
| Anomaly detection report | `ai_report/anomaly_detection_YYYYMMDD.md` | Markdown (4 sections, `df.to_markdown`) | `anomaly_detection.generate(...)` |
| Data catalog | `data/catalog.json` | JSON | `catalog_generator.generate_catalog()` |
| Ticker names | `research_insights.db.stock_names` | SQLite rows | `fetch_names.save_name(...)` |

### 4.3 Report section contract (Markdown structure)

Both Markdown reports follow a fixed contract that downstream consumers (MCP tools, the dashboard) may parse:
- **Line 1**: `# <report title>` (e.g. `# 市场全景报告`).
- **Line 3**: a `>` header line carrying metadata (`生成时间`, `数据截止`, and for anomaly reports, `量比阈值` + `跳空阈值`).
- **Sections**: `## N. <section title>` headers, each followed by either a `to_markdown` table or a `_无..._` placeholder line. An empty detector result MUST still emit the section header + placeholder (not omit the section) — see Acceptance Criteria §8.3.

### 4.4 CLI argument contract

| Script | Flag | Type | Default | Effect |
|---|---|---|---|---|
| `anomaly_detection.py` | `--min-ratio` | float | `3.0` | Volume-ratio threshold (≥) |
| `anomaly_detection.py` | `--gap-threshold` | float | `5.0` | Absolute price-gap threshold (%) |
| `anomaly_detection.py` | `--days` | int | `3` | Recency window driving the shared `cutoff` |
| `fetch_names.py` | `--force` | flag | off | Clear existing `stock_names` for the market before refetch |
| `fetch_names.py` | `--from-cache` | flag | off | Only import from `meta_cache.json`; skip yfinance |
| `fetch_names.py` | `--market` | enum `cn\|us` | `cn` | Which market's tickers to enrich |
| `market_overview.py` | (none) | — | — | No arguments |
| `catalog_generator.py` | (none) | — | — | No arguments |

### 4.5 Exit codes / error behavior

These scripts use the legacy `print(...)` + raise pattern; they do **not** define explicit exit codes. Failure modes:
- DuckDB connection open failure → propagates as a `duckdb.Error` from `connect_duckdb`; the script exits non-zero with a traceback.
- A failing individual view inside `run_views_sql` → caught and printed (`__init__.py:131-134`); execution continues. Downstream queries against a missing view will then raise `duckdb.CatalogException`, which DOES propagate.
- A failing detector query inside `generate()` → propagates (no try/except wraps the four detector calls in `market_overview.generate`). This is an open robustness gap (Section 8).
- `fetch_names` per-ticker yfinance failure → caught locally, falls back to saving the ticker as its own name (`fetch_names.py:86-87`); the batch continues. Batch-level exception → caught and printed (`fetch_names.py:93-94`); batch continues.

## 5. Edge Cases

| Case | What happens |
|---|---|
| `cn.stock_prices` is empty / `MAX(date)` is NULL | `max_d` is `None`; the `max_d - timedelta(...)` arithmetic in `market_overview.py:127-128` and `anomaly_detection.py:114` raises `TypeError: unsupported operand type(s)`. **Open gap** — no guard exists. (Section 8.) |
| A DuckDB view failed to create in `run_views_sql` | The error is printed; the script continues. The next query against that view raises `duckdb.CatalogException` and aborts the run. |
| A detector returns zero rows | The report still writes the `## N. ...` section header followed by `_无符合条件的结果_` (or `_无近期数据_` / `_无数据_`). The Markdown file is complete and well-formed. (`market_overview.py:144-176`, `anomaly_detection.py:130-155`.) |
| `--gap-threshold` is 0 or negative | The query `WHERE ABS(gap_pct) >= 0` returns every row with a prior close; the `LIMIT 30` caps it. No crash, but a noisy report. No validation exists. |
| `--min-ratio` < 1.0 | `vw_volume_anomalies_cn` rows with `vol_ratio < 1` are included; the report is correct but semantically "below-average volume". No validation exists. |
| `consecutive_extremes` with a market that has < `min_days` of history | The gaps-and-islands query yields no groups meeting `HAVING COUNT(*) >= min_days`; empty DataFrame; the section writes the placeholder. |
| `fetch_names` yfinance rate-limit (429) on a batch | Caught by the per-ticker `except Exception`; that ticker gets the fallback name; the batch moves on. There is no explicit 429 backoff at the batch level. |
| `fetch_names --force` on a market with no rows in `stock_prices` | `get_all_tickers` returns `[]`; `fetch_batch_yfinance` prints "All 0 tickers already have names" and returns. No crash. |
| `catalog_generator` when `data/views.sql` is missing | `run_views_sql` opens it inside a `with open(...)` (`__init__.py:124`) → `FileNotFoundError` propagates. No graceful degradation. |
| Concurrent report generation (two `generate()` calls) | Both open their own DuckDB connection; both write to `ai_report/market_overview_YYYYMMDD.md` with the same filename → the second overwrites the first. No file locking. |

## 6. Dependencies

### Upstream (this module depends on)

| Module | How | Detail |
|---|---|---|
| **#1 Runtime Configuration** | Env-var path overrides | `DOGE_DB_DIR`, `DOGE_CN_DB`, `DOGE_US_DB`, `DOGE_RESEARCH_DB`, `DOGE_DUCKDB_PATH` (`__init__.py:30-34`). The four scripts do NOT read `src/doge/config/settings.py` directly — they re-derive paths from these module constants (ADR-0002 drift; open question). |
| **#2 Market Data Storage** | DuckDB views + attached SQLite | All four reports query views defined in `data/views.sql` (`vw_rsrs_ranking_cn`, `vw_volume_anomalies_cn`) and the `cn.stock_prices` table attached via `connect_duckdb`. The catalog reads SQLite stats via `get_sqlite_stats`. |
| **#7 Research Insight Knowledge Base** (shared table) | `stock_names` table | `fetch_names` reads/writes `research_insights.db.stock_names`. The table schema is owned by Module #7; this module is a writer to it. |
| External: `yfinance` | Network | `fetch_names` only. Optional at runtime for the report scripts. |
| External: `duckdb`, `pandas` | Library | Required for all report scripts. `df.to_markdown` requires `tabulate` (a pandas extra). |

### Downstream (depend on this module)

| Module | How |
|---|---|
| **#7 Research Insight Knowledge Base** | Shares `src/ai_analysis/__init__.py` (the connection layer) and the `stock_names`/`stock_notes` SQLite tables. `stock_notes.py` (Module #7) imports `connect_duckdb`, `RESEARCH_DB`, `CN_DB`, `US_DB` from this package's `__init__`. |
| **#8 MCP Server** | The MCP `market_breadth`, `rsrs_ranking`, and `volume_anomalies` tools read the same DuckDB views this module reports on; they are sibling consumers of Module #2, not direct callers of these scripts. |
| **#9 FastAPI Service** | Exposes report-generation and breadth endpoints that wrap the same DuckDB views. |
| **#10 PyQt Desktop Dashboard** | Renders these reports in its dashboard view; may shell out to `market_overview.py` / `anomaly_detection.py` or call shared query functions. |

### Bidirectional notes (required by design-docs rules)

- Module #2's CDD (`design/cdd/market-data-storage.md`) lists this module among the consumers of its DuckDB views. ✓
- Module #4's CDD (`design/cdd/macro-strategy-engine.md` §1) carries the cross-reference clarifying that the project's LLM lives there, not here. ✓
- Module #5's CDD (`design/cdd/micro-momentum-scanner.md` §3.8) documents `IndustryAnalyzer` as the LLM-based industry analyzer; this module's CDD cross-references it in §1. ✓
- Module #7's CDD owns `stock_names`/`stock_notes`; this module is a writer to `stock_names` only and must NOT be treated as the owner.

## 7. Configuration Knobs

| Knob | Owner | Default | Valid range / enum | Env-owned | Rollout / op risk |
|---|---|---|---|---|---|
| `DOGE_DB_DIR` | Module #1 | `<root>/data` | any dir path | yes | Changing mid-session moves every DB; restart required. |
| `DOGE_CN_DB` / `DOGE_US_DB` / `DOGE_RESEARCH_DB` | Module #1 | `<DB_DIR>/market_data_{cn,us}.db`, `<DB_DIR>/research_insights.db` | any file path | yes | Pointing at a non-existent file → `sqlite3.OperationalError` on first read. |
| `DOGE_DUCKDB_PATH` | Module #1 | `<DB_DIR>/market.duckdb` | any file path | yes | If the file does not exist, `duckdb.connect` creates a fresh empty one → all views return zero rows. |
| `OPENBLAS_NUM_THREADS` / `OMP_NUM_THREADS` | This module (`__init__.py:15-16`) | `1` | positive int | `os.environ.setdefault` (only sets if unset) | Set to avoid OOM during `df()` conversion. Lowering further has no benefit; raising can OOM on large result sets. |
| `REPORT_DIR` | This module (`__init__.py:36`) | `<root>/ai_report` | any dir path | no (computed from `PROJECT_ROOT`) | Not env-overridable — a gap vs the DB-path knobs. |
| `--min-ratio` | CLI (`anomaly_detection.py`) | `3.0` | float > 0 | no | < 1.0 produces semantically-meaningless "below-average volume" rows. |
| `--gap-threshold` | CLI (`anomaly_detection.py`) | `5.0` | float ≥ 0 (percent) | no | 0 returns every row with a prior close (capped at 30). |
| `--days` | CLI (`anomaly_detection.py`) | `3` | int ≥ 0 | no | Drives `cutoff = max_d - max(30, days+5)`; values < 25 are clamped up to a 30-day floor. |
| `batch_size` / `delay` | `fetch_names.fetch_batch_yfinance` | `20` / `2.0s` | positive int / seconds | no (hardcoded) | Hardcoded — a yfinance rate-limit change would require a code edit. Open question. |
| `LIMIT` clauses | hardcoded in each query | 15 / 20 / 30 | positive int | no | Not configurable without code change. Open question. |

## 8. Acceptance Criteria

### 8.1 Report generation (contract)

- **AC-1**: Given a fixture `vw_rsrs_ranking_cn` result with 20 rows, `rsrs_top20(con)` returns a DataFrame whose columns are exactly `[rank, ticker, rsrs, last_close, pct_change_60d, avg_vol_20d]` and whose row count is ≤ 20, ordered by `rank` ascending. (Verified by `tests/test_market_reporting.py`.)
- **AC-2**: Given a fixture `vw_volume_anomalies_cn` result, `volume_spikes(con)` returns ≤ 15 rows ordered by `vol_ratio` descending, columns `[ticker, date, volume, avg_vol_20d, vol_ratio, intraday_return]`.
- **AC-3**: `anomaly_detection.volume_anomalies(con, min_ratio, cutoff)` filters fixture rows to those with `vol_ratio >= min_ratio` and (when `cutoff` is set) `date >= cutoff`, returning ≤ 30 rows ordered by `vol_ratio` desc.
- **AC-4**: `anomaly_detection.consecutive_extremes(con, "down", 5, cutoff)` returns only runs whose `streak_days >= 5`; an empty fixture yields an empty DataFrame (never raises).

### 8.2 Empty-result rendering

- **AC-5**: When a detector returns an empty DataFrame, the corresponding Markdown section in the generated report still contains the `## N. <title>` header and a placeholder line; the file is well-formed Markdown end-to-end. (Pinned by the empty-result test case.)

### 8.3 Determinism / isolation (test gate)

- **AC-6**: `tests/test_market_reporting.py` runs green with **no live DuckDB connection and no network** — every `con.execute(...).df()` call is served by a mock connection returning fixture DataFrames. The suite is deterministic across repeated runs (no time seeds, no random ordering). (Required by `.claude/rules/test-standards.md`.)

### 8.4 Naming-honesty gate

- **AC-7**: This CDD's §1 explicitly states the module has no LLM, names Module #4 as the LLM owner, and names Module #5 as the industry-clustering owner. (Self-evident from this document.)
- **AC-8**: `design/cdd/module-index.md` row 6 names this module "Market Reporting", points its Design Doc at this file, and its Depends On reflects only the storage/config dependencies this module actually imports (no Macro/Micro LLM dependency).

### 8.5 Migration-readiness (open, non-blocking)

- **AC-9** (open): The four report scripts route through `get_duckdb_connection()` (or the Module #2 `DuckDBConnection` adapter) instead of the legacy `connect_duckdb`/`run_views_sql` pair. Tracked as a Section-7/8 migration target, not a current gate.

## 9. Open Questions

1. **Empty-`stock_prices` guard**: `market_overview.generate` and `anomaly_detection.generate` assume `MAX(date)` is non-NULL. Should they emit a "no data" report and exit 0 instead of raising `TypeError`? (Recommended fix: guard at `generate()` entry.)
2. **Per-detector error isolation**: `market_overview.generate` runs all five queries with no try/except; a single failing view aborts the whole report. Should each section be wrapped so a partial report is still written?
3. **Config centralization (ADR-0002 drift)**: the four scripts re-derive paths from `__init__` constants rather than reading `Settings().db`. Migrate to centralized config.
4. **Interface-layer DB access (ADR-0001 drift)**: the scripts call `connect_duckdb`/`run_views_sql` directly. Migrate to the `DuckDBConnection` adapter behind an `IReportRepository` port (see Module #12).
5. **Hardcoded `LIMIT`s and yfinance `batch_size`/`delay`**: surface these as CLI flags or config values.
6. **`REPORT_DIR` env override**: align with the DB-path knobs (add `DOGE_REPORT_DIR`).
7. **File-locking on concurrent `generate()`**: two same-day runs overwrite `market_overview_YYYYMMDD.md`. Decide whether to timestamp-suffix or lock.
