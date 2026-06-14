# CDD: TDX/YFinance Data Sources (Module #3)

> **Slug**: `data-sources`
> **Category**: Foundation
> **Status**: Draft (reverse-documentation of brownfield code)
> **Created**: 2026-06-11
> **Depends On**: `runtime-configuration` (#1), `market-data-storage` (#2)
> **Related ADRs**: [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) (brownfield clean architecture), [ADR-0004](../../docs/architecture/adr-0004-data-source-adapter-contract.md) (data-source adapter contract)
> **Source files reverse-documented**: `src/micro/tdx_loader.py`, `src/micro/tdx_downloader.py`, `src/doge/infrastructure/data_source/tdx.py`, `src/doge/infrastructure/data_source/yfinance.py`, `src/doge/core/ports/data_source.py`

---

## 1. Overview

The TDX/YFinance Data Sources module is the Foundation layer responsible for bringing market OHLCV data into the local-first platform. It currently has three concrete ingestion paths in the brownfield code: (a) `src/micro/tdx_loader.py` — a local-file reader that parses 32-byte-per-record TDX `.day` binary files from a locally installed通达信 (TDX) `vipdoc` directory; (b) `src/micro/tdx_downloader.py` — a server-fallback downloader that connects to TDX quotation servers over the opentdx protocol to fetch daily K-lines via `get_kline` (and a deprecated raw-`.day` mode), with incremental sync, automatic server reconnection, and direct SQLite writes; and (c) the new clean-architecture adapters under `src/doge/infrastructure/data_source/` that implement the `IMarketDataSource` port — a TDX stub (`tdx.py`) awaiting migration of the downloader logic, and a fully working yfinance adapter (`yfinance.py`, added to fix BUG B) that wraps `yfinance.download` with shared retry/backoff and normalizes to the canonical 8-column frame. All paths ultimately write into the `stock_prices` table owned by Module #2 (Market Data Storage).

## 2. User Promise / JTBD

**Operator's job**: "Refresh my local A-share and US-equity market data so that momentum scans, macro analysis, and AI industry reports run against the most recent N trading days — without me babysitting flaky servers, proxies, or rate limits."

**Promise the module must keep**:
- Given a ticker list and a market (`cn` or `us`), fetch the most recent ~120 trading days of OHLCV per ticker and persist them to the local SQLite market database.
- Tolerate TDX server failures, yfinance rate-limiting (HTTP 429), and offline operation by retrying, reconnecting, and ultimately degrading to "no new data" rather than crashing or corrupting existing rows.
- Never require the operator to re-derive project paths, server lists, or DB locations — these come from centralized config (`runtime-configuration` #1).
- Produce a normalized frame shape (`date, open, high, low, close, volume, amount, ticker`) regardless of which source produced it, so downstream scanners (#4, #5) do not branch on source.

## 3. Detailed Behavior

This section documents the three ingestion paths. All file:line citations are against the current brownfield state on the `cdd-adoption-2026-06-11` branch.

### 3.1 Local TDX file reader — `src/micro/tdx_loader.py`

Class `TDXReader(root_dir)` reads pre-downloaded TDX `.day` files from a local vipdoc root (e.g. `D:\Games\New Tdx Vip2020\vipdoc`).

- `get_data(symbol, market_type=None)` (`tdx_loader.py:22-62`):
  - Infers market: if the symbol contains `.` it is treated as CN (`'cn'`); otherwise US (`'us'`) (`tdx_loader.py:35-39`).
  - CN path (`tdx_loader.py:42-48`): splits `symbol` on `.` into `code`/`market`, lowercases the market suffix, and constructs `<root>/<market>/lday/<market><code>.day`.
  - US path (`tdx_loader.py:50-57`): globs `<root>/ds/lday/*#<symbol>.day` and takes the first match; raises `FileNotFoundError` if none.
  - Raises `FileNotFoundError` if the resolved file does not exist (`tdx_loader.py:59-60`).
- `_parse_file(file_path, market_type, trim_to_recent=True)` (`tdx_loader.py:66-139`):
  - Reads 32 bytes per record (`tdx_loader.py:80-84`).
  - **CN binary layout** (`tdx_loader.py:104-119`): `<IIIII fII` — `date_int, open, high, low, close` are integers (prices divided by 100), `amount` is float, `volume` is int, trailing field unused.
  - **US binary layout** (`tdx_loader.py:87-102`): `<IfffffII` — prices and amount are floats (no division).
  - Date is decoded from a `YYYYMMDD` integer (`tdx_loader.py:92-96`, `109-113`).
  - Output columns: `['date','open','high','low','close','volume','amount']` (`tdx_loader.py:121-129`), sorted ascending by date.
  - `MAX_DAYS = 120` (`tdx_loader.py:64`): if `trim_to_recent` and `len(df) > 120`, keeps only the last 120 rows. This is the canonical "120d fetch default" shared with the server downloader and the yfinance adapter.

### 3.2 TDX server downloader — `src/micro/tdx_downloader.py`

A CLI-driven batch downloader that connects to TDX quotation servers via the `opentdx` package and writes directly to SQLite.

- **Module-level `sys.path.insert` (FORBIDDEN pattern — remediation target)**: `tdx_downloader.py:23-26` computes `_PROJECT_ROOT` and inserts it (plus the script's own directory) into `sys.path`. This is an ADR-0001 forbidden pattern (`sys_path_insert` / `_PROJECT_ROOT_recalculation`) and is recorded as an acceptance criterion in section 8.
- **Server discovery** (`tdx_downloader.py:33-84`):
  - `_load_servers_from_opentdx()` prefers server lists from `opentdx.const.main_hosts` / `ex_hosts`; falls back to hardcoded CN/US host lists (`tdx_downloader.py:42-47`).
  - `find_working_server(servers, test_market, timeout=5)` (`tdx_downloader.py:52-84`): concurrently probes the first 20 servers in a `ThreadPoolExecutor(max_workers=10)`, connects+logs in on port `7709` (CN) or `7727` (US/ex), and returns the first client that responds. Returns `(None, None)` if none connect.
- **Incremental fetch planning** (`tdx_downloader.py:91-130`):
  - `_get_latest_market_date(client, market)` queries 5 bars of an active index (`000001.SH` for CN, `AAPL` for US) to determine the latest trading date (`tdx_downloader.py:91-103`).
  - `_compute_fetch_params(ticker, sync_state, latest_market_date, buffer=10)` (`tdx_downloader.py:106-130`): returns `(start, count, reason)` where reason ∈ {`full`, `skip`, `incr`}. First-ever fetch → `(0, 800, "full")`; already up-to-date → `(0, 0, "skip")`; otherwise incremental with a 10-bar buffer (`count = min(800, 20+buffer)`).
- **K-line download** (`download_cn_kline` `tdx_downloader.py:173-230`, `download_us_kline` `tdx_downloader.py:233-288`):
  - For each ticker: compute params → call `client.stock_kline(...)` (CN) or `client.goods_kline(EX_MARKET.US_STOCK, ...)` (US) → `_bars_to_df()` → `save_stock_data_custom(df, db_path)`.
  - `_bars_to_df(bars, ticker, max_rows=120)` (`tdx_downloader.py:148-166`): normalizes the list-of-dicts to `['date','open','high','low','close','volume','amount','ticker']`, handling the differing date key (`'datetime'` for CN `stock_kline`, `'date_time'` for US `goods_kline`), renaming `vol`→`volume`, and trimming to the last 120 rows.
  - **Reconnect logic** (`tdx_downloader.py:209-222`, `266-280`): on 5 consecutive failures, disconnects and calls `find_working_server()` again; aborts the whole run if reconnection fails.
- **Raw `.day` mode** (`download_day_file_raw` `tdx_downloader.py:364-407`, `download_cn_raw` `tdx_downloader.py:410-441`): **DEPRECATED** — protocol `0x6B9` (FileDownload) returns empty on most servers. US raw mode is silently redirected to `goods_kline`. Retained for compatibility only.
- **`.day` binary round-trip** (`parse_day_records` `tdx_downloader.py:303-345`, `_write_local_day_file` `tdx_downloader.py:444-482`): mirrors the `_parse_file` CN/US layouts; `_write_local_day_file` re-packs records back into the TDX file format, written date-descending to match the canonical TDX on-disk order.
- **CLI** (`tdx_downloader.py:524-601`): `--market {cn,us}`, `--method {kline,raw}`, `--db`, `--local-dir`, `--from-csv`, `--only`, `--max-bars` (default `120`), `--no-incremental`. Default DB is `<root>/data/market_data_{cn|us}.db` (`tdx_downloader.py:544-546`). After download, calls `_refresh_views()` to rebuild DuckDB analytical views (`tdx_downloader.py:509-517`).

### 3.3 Clean-architecture adapters — `src/doge/infrastructure/data_source/`

The port is `IMarketDataSource` (`src/doge/core/ports/data_source.py:8-49`):

```
connect() -> None
disconnect() -> None
download_kline(ticker, market, start=0, count=800) -> Optional[DataFrame]
get_latest_market_date(market) -> Optional[str]
is_connected() -> bool
```

`download_kline` MUST return a frame with columns `date, open, high, low, close, volume, amount, ticker` (`data_source.py:28-39`).

#### 3.3.1 TDX adapter (`src/doge/infrastructure/data_source/tdx.py`) — STUB

`TDXDataSource(IMarketDataSource)` (`tdx.py:13-35`) is a placeholder. `connect/disconnect/is_connected` are no-ops returning `False`; `download_kline` and `get_latest_market_date` raise `NotImplementedError("... migrate from tdx_downloader.py")`. Migration of the `tdx_downloader.py` logic into this adapter is open work (see section 8 acceptance criteria and open questions).

#### 3.3.2 yfinance adapter (`src/doge/infrastructure/data_source/yfinance.py`) — IMPLEMENTED (BUG B fix)

`YFinanceDataSource(IMarketDataSource)` (`yfinance.py`) wraps `yfinance.download` and normalizes to the canonical 8-column frame. Key behaviors:

- **Construction** (`yfinance.py:__init__`): `max_retries=3`, `retry_delay=5.0`, `period_days=120` (matching `TDXReader.MAX_DAYS`).
- **Connection lifecycle**: yfinance is stateless HTTP, so `connect/disconnect/is_connected` are flag-only no-ops (documented in docstrings) that exist purely to satisfy the shared port contract.
- **Ticker remap** (`_to_yf_ticker`, mirrors `src/micro/industry_analyzer.py:184`): CN `.SH` is rewritten to yfinance's `.SS` suffix (`.SZ` passes through); US tickers pass through unchanged.
- **`download_kline(ticker, market, start=0, count=800)`**:
  - `start` is accepted but ignored (documented) — yfinance is period-based, not offset-based; the semantic mismatch with the TDX offset contract is noted in the docstring.
  - Lazily `import yfinance` so tests can monkeypatch and so module import never touches the network.
  - Calls `_fetch_with_retry`, then `_normalize`, then trims to the most recent `count` rows.
- **`_fetch_with_retry`** (`yfinance.py`): bounded retry loop that reuses the rate-limit heuristic from `src/macro/data_loader.py:94-97` — error messages containing `"Rate"`, `"429"`, or `"Too Many Requests"` are treated as rate-limit responses and retried after `retry_delay` seconds. Empty responses are also retried (a common rate-limit symptom). After `max_retries` it logs and returns `None`.
- **`_normalize`** (`yfinance.py`): flattens yfinance's single-ticker MultiIndex columns; maps TitleCase `Open/High/Low/Close/Volume` → lowercase canonical names (`Adj Close` maps to `close` when present); builds a string `date` column from the `DatetimeIndex`; adds `amount = 0.0` (yfinance daily OHLCV has no turnover — see section 5 edge case); adds the `ticker` column; coerces OHLCV to numeric and drops rows with NaN OHLC; sorts ascending and returns exactly the 8 canonical columns in order.
- **`get_latest_market_date(market)`**: fetches 5 days of a liquid proxy (`000300.SS` for CN, `SPY` for US) and returns the last index value as `YYYY-MM-DD`; returns `None` on failure.

## 4. Contracts / Data Model

### 4.1 Canonical output frame (all sources)

| Column   | dtype            | Notes                                                       |
|----------|------------------|-------------------------------------------------------------|
| `date`   | `object` (str)   | `YYYY-MM-DD`, sorted ascending                              |
| `open`   | `float64`        |                                                             |
| `high`   | `float64`        |                                                             |
| `low`    | `float64`        |                                                             |
| `close`  | `float64`        | TDX CN: integer/100; yfinance: adjusted close when present  |
| `volume` | `int64`/`uint64` |                                                             |
| `amount` | `float64`        | TDX: turnover; **yfinance: `0.0` placeholder** (not provided) |
| `ticker` | `object` (str)   | Canonical form (e.g. `600000.SH`, `AAPL`)                   |

The TDX local reader returns 7 columns (no `ticker`); the downloader `_bars_to_df` and the yfinance adapter return the full 8. Downstream consumers must not assume `amount` is meaningful when the source is yfinance.

### 4.2 Storage contract (delegated to Module #2)

Persisted via `save_stock_data_custom(data, db_path, retention_days=180)` (`src/micro/database.py:118-155`): incremental upsert keyed by `(ticker, date)` PRIMARY KEY on `stock_prices`; rows older than `retention_days` are pruned per ticker; exceptions are swallowed (logged nowhere — see open questions).

### 4.3 TDX `.day` binary contracts

| Market | Struct format    | Price encoding     |
|--------|------------------|--------------------|
| CN     | `<IIIII fII`     | prices ÷ 100 (int) |
| US     | `<IfffffII`      | prices as float    |

Record size: 32 bytes (`tdx_loader.py:82`, `tdx_downloader.py:300`). Date is a `YYYYMMDD` integer; the downloader rejects records outside `[19900101, 20991231]` as garbage (`tdx_downloader.py:317-318`).

### 4.4 Exit codes (CLI)

`tdx_downloader.py` CLI exits `1` when no tickers are found (`tdx_downloader.py:557-559`) or when no TDX server is reachable (`tdx_downloader.py:570-572`). Normal completion prints `Done in <seconds>s` (`tdx_downloader.py:600-601`) with exit `0`. The yfinance adapter is library-only (no CLI) and signals failure by returning `None`.

### 4.5 Registry proposals (for later Phase 5 entry approval — DO NOT write registry files)

> **Routing note (current `docs/registry/` state)**: only `docs/registry/architecture.yaml` exists today. Per its header comment, that file holds **cross-ADR architectural stances** (written by `/architecture-decision` Phase 5) — NOT concrete runtime values. The proposals below are split by destination so value constants are not misrouted into the ADR-stance registry.

**(a) `architecture.yaml` candidates — architectural stances / port contracts:**
- `data_source.canonical_ohlcv_columns` = `[date, open, high, low, close, volume, amount, ticker]` — the `IMarketDataSource.download_kline` port contract (ADR-0004); a stance, not a tunable value.
- `data_source.default_window_days` = 120 — the **shared-window constraint** that `TDXReader.MAX_DAYS`, downloader `--max-bars`, `_bars_to_df(max_rows=)`, and yfinance `period_days` MUST change in lockstep. This is an architectural alignment rule, not a free knob.

**(b) Value-constant candidates — concrete runtime values (NOT architecture.yaml):**
- `tdx.day_record_size` = 32 (bytes)
- `tdx.day_format_cn` = `<IIIII fII`
- `tdx.day_format_us` = `<IfffffII`
- `tdx.day_date_valid_range` = `[19900101, 20991231]`
- `tdx.cn_port` = 7709; `tdx.us_port` = 7727
- `tdx.find_server_timeout` = 5 (seconds); probe pool = first 20 servers, max 10 workers
- `tdx.reconnect_threshold` = 5 (consecutive failures)
- `data_source.incremental_buffer_bars` = 10
- `data_source.full_fetch_count` = 800 (TDX); `data_source.incremental_fetch_count` = `min(800, 20+buffer)`
- `yfinance.max_retries` = 3; `yfinance.retry_delay_seconds` = 5.0
- `yfinance.rate_limit_tokens` = `["Rate", "429", "Too Many Requests"]`
- `yfinance.cn_proxy_index` = `000300.SS`; `yfinance.us_proxy_index` = `SPY`
- `storage.retention_days` = 180 (from `save_stock_data_custom`)

> **OPEN QUESTION (registry design):** `docs/registry/entities.yaml` does **not** exist. The value constants in group (b) are not architectural stances, so `architecture.yaml` is the wrong home for them, and there is currently no constants/value registry to receive them. Creating such a registry (e.g. a new `constants.yaml` or an `entities.yaml`) is itself a registry-design decision that should get its own ADR before any Phase 5 write. Until that artifact exists, group (b) proposals stay enumerated here only.

## 5. Edge Cases

| Situation | What happens (Current State) |
|---|---|
| **TDX local file missing** | `get_data` raises `FileNotFoundError` (`tdx_loader.py:59-60`); US glob miss raises `FileNotFoundError` with the glob pattern (`tdx_loader.py:55`). |
| **Truncated `.day` file** (last record < 32 bytes) | `_parse_file` stops reading cleanly (`tdx_loader.py:83-84`); partial record is dropped. |
| **Garbage record in streamed `.day`** (downloader only) | `parse_day_records` skips records whose date is outside `[19900101, 20991231]` (`tdx_downloader.py:317-318`). The local loader does NOT apply this guard. |
| **All TDX servers unreachable** | `find_working_server` returns `(None, None)`; CLI prints `No server available` and exits `1` (`tdx_downloader.py:570-572`). |
| **Mid-run TDX server failure** | After 5 consecutive per-ticker failures, the downloader disconnects and re-runs `find_working_server`; if that also fails it aborts the whole run (`tdx_downloader.py:209-222`, `266-280`). Already-saved tickers are preserved (incremental upsert). |
| **Ticker already up-to-date (incremental)** | `_compute_fetch_params` returns `(0, 0, "skip")`; the ticker is counted as `skipped` and no DB write occurs (`tdx_downloader.py:121-123`, `192-197`). |
| **Deprecated raw `.day` mode** | `download_day_file_raw` is a no-op on most servers (protocol `0x6B9` returns empty); US raw mode silently uses `goods_kline` instead (`tdx_downloader.py:364-407`). |
| **yfinance empty ticker / delisted** | `download` returns an empty frame; the adapter retries (empty often means rate-limit), then returns `None`. Downstream treats `None` as "no new data" (`yfinance.py:_fetch_with_retry`). |
| **yfinance rate limit (HTTP 429)** | Detected by the shared rate-limit token heuristic; retried up to `max_retries` with `retry_delay` backoff, then returns `None` (degraded, not crash). Mirrors `macro/data_loader.py:94-97`. |
| **yfinance generic network error** | Logged and retried like a rate-limit; after exhaustion returns `None`. |
| **yfinance partial data / NaN OHLC rows** | `_normalize` coerces OHLCV to numeric with `errors="coerce"` and drops rows missing any of `open/high/low/close` (`yfinance.py:_normalize`). Volume NaNs are preserved as numeric NaN (current behavior — see open questions). |
| **yfinance missing `amount`** | Daily OHLCV from yfinance has no turnover; `amount` is set to `0.0`. Consumers that weight by turnover must branch on source. |
| **CN ticker suffix mismatch (`.SH` vs `.SS`)** | yfinance adapter remaps `.SH`→`.SS` on input and restores the canonical `.SH` on output (`yfinance.py:_to_yf_ticker`). TDX paths use `.SH`/`.SZ` natively. |
| **`start` parameter on yfinance** | Accepted but ignored (period-based API); documented in the adapter docstring. Callers needing offset semantics should use the TDX adapter. |
| **DB write failure** | `save_stock_data_custom` swallows exceptions silently (`database.py:152-153`); no log, no retry. Recorded as an open question (observability gap). |
| **Concurrent downloads to same DB** | Not guarded. SQLite's default locking applies; concurrent writers may hit `database is locked` (`sqlite3.OperationalError`). The downloader is single-threaded per market. **Because `save_stock_data_custom` catches all exceptions silently (`database.py:152-153`, bare `except: pass`), a locked-DB failure produces NO log and NO error surface — the affected ticker's refresh is silently dropped (silent data loss).** This is the observability gap also noted in open questions; see section 9.3 for the concurrency model. |

## 6. Dependencies

**Upstream (this module depends on):**
- **Module #1 Runtime Configuration** — env vars `DOGE_DB_DIR`, `DOGE_CN_DB`, `DOGE_US_DB`, `PROJECT_ROOT` (`src/doge/config/settings.py:23-38`). The legacy downloader still recomputes `_PROJECT_ROOT` locally (`tdx_downloader.py:23-26`) — tech debt to be retired by routing through `settings.py`.
- **Module #2 Market Data Storage** — `init_db_custom`, `save_stock_data_custom`, `get_tickers_sync_state` (`src/micro/database.py:94,118,157`) and the `stock_prices` schema.

**Downstream (depend on this module):**
- **Module #4 Macro Strategy Engine** — `src/macro/data_loader.py` uses `yfinance.download` directly (not yet through the adapter) with the same retry heuristic; migration target is to inject `YFinanceDataSource`.
- **Module #5 Micro Momentum Scanner** — consumes the persisted `stock_prices` rows produced by the TDX downloader.
- **Module #6 AI Industry Analysis** — `src/micro/industry_analyzer.py:6,184,190` uses `yfinance.Ticker().info` for metadata (separate from OHLCV, but shares the remap heuristic).

**External packages:**
- `opentdx` (TDX protocol client) — `from opentdx.tdxClient import TdxClient`, `from opentdx.const import MARKET, EX_MARKET, PERIOD, ADJUST` (`tdx_downloader.py:29-30`).
- `yfinance` 0.2.66 — `yfinance.download` and `yfinance.Ticker` (`requirements.txt`).
- `pandas`, `scipy` (used by consumers, not the adapters directly).

**Docs / ADRs:**
- [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) — defines the forbidden patterns this module still violates (see section 8).
- [ADR-0004](../../docs/architecture/adr-0004-data-source-adapter-contract.md) — records that external market data access is via `IMarketDataSource` adapters.

## 7. Configuration Knobs

| Knob | Where | Default | Valid range / enum | Env ownership | Operational risk |
|---|---|---|---|---|---|
| `DOGE_DB_DIR` | `settings.py:26` | `<root>/data` | any writable dir | operator env | Wrong path → data written to unexpected location |
| `DOGE_CN_DB` / `DOGE_US_DB` | `settings.py:34-35` | `<dir>/market_data_{cn,us}.db` | any path | operator env | Override mismatch between downloader CLI (`--db`) and settings |
| `TDXReader.MAX_DAYS` | `tdx_loader.py:64` | `120` | positive int | code (propose registry) | Larger → more memory + slower scans; must stay aligned with downloader/yfinance window |
| `--max-bars` (CLI) | `tdx_downloader.py:537-538` | `120` | positive int | CLI flag | Misalignment with `MAX_DAYS`/`period_days` → inconsistent row counts per source |
| `DEFAULT_PERIOD_DAYS` (yfinance) | `yfinance.py` | `120` | positive int | code (propose registry) | Same alignment risk |
| `DEFAULT_MAX_RETRIES` (yfinance) | `yfinance.py` | `3` | int ≥ 1 | code (propose registry) | Too high → slow offline runs; too low → spurious empty results |
| `DEFAULT_RETRY_DELAY` (yfinance) | `yfinance.py` | `5.0`s | float ≥ 0 | code (propose registry) | Aggressive delay → rate-limit not respected |
| `tdx.timeout` (find server) | `tdx_downloader.py:52` / `settings.py:54` | `5`s | float ≥ 1 | code/`TDXConfig` | Too low → no server found; too high → slow startup |
| `reconnect_threshold` | `tdx_downloader.py:211,268` | `5` | int ≥ 1 | code (propose registry) | Frequent reconnect storms if too low |
| `retention_days` (storage) | `database.py:118` | `180` | positive int | code | Prunes data older than N days; must exceed scan lookback |
| `proxy_url` (HTTP proxy — **CROSS-CUTTING, not owned by this module**) | `macro/data_loader.py:53-60`, `industry_analyzer.py:48-51` | unset | URL | operator env | Documented here for visibility only. The proxy env-var mutation (`HTTP_PROXY`/`HTTPS_PROXY`, set/restored at runtime) is owned by **Modules #4 and #6** consumers, NOT by this module's adapter. `YFinanceDataSource` itself does **not** touch proxy env vars — it inherits whatever proxy env the caller's process has set. See open questions. |

**Migration target (vs. Current State):**
- *Current State*: server lists hardcoded as fallback in `tdx_downloader.py:42-47` and duplicated in `settings.py:TDXConfig.cn_servers/us_servers`; CLI `--db` overrides settings silently.
- *Target (Migration)*: all TDX knobs sourced from `TDXConfig` (`settings.py:42-54`); yfinance knobs promoted to a `YFinanceConfig` dataclass in `settings.py`; CLI flags become overrides-on-top-of-settings rather than replacements.

## 8. Acceptance Criteria

**Contract:**
- [ ] `YFinanceDataSource` is an instance of `IMarketDataSource` (verified — `tests/test_yfinance_adapter.py::test_yfinance_datasource_implements_port`).
- [ ] `download_kline` returns a frame with exactly the columns `[date, open, high, low, close, volume, amount, ticker]` in order (verified).
- [ ] `download_kline` returns `None` (never raises) for empty ticker, missing columns, exhausted retries, and network failure (verified).
- [ ] CN ticker `.SH` is remapped to `.SS` on the yfinance call and restored to `.SH` in the output (verified).
- [ ] Rate-limit (429) responses are retried then succeed on a subsequent call (verified).
- [ ] No test in `tests/test_yfinance_adapter.py` performs a real network call (all use `FakeYFinance` / `monkeypatch`).

**Workflow:**
- [ ] `python -m pytest tests/test_yfinance_adapter.py` passes with 13/13 (verified — 0.46s).
- [ ] `python src/micro/tdx_downloader.py --market cn --method kline --only 600000.SH` runs end-to-end against a reachable TDX server (manual smoke — requires network). **PASS =** exit code `0` AND stdout contains `Done in <N>s` AND after the run, `SELECT COUNT(*) FROM stock_prices WHERE ticker='600000.SH'` returns `>= 1` with at least one row dated within the current trading week (Mon–Fri of the run date). Capture the command transcript + the `SELECT` output as evidence under `production/qa/evidence/` (ADVISORY gate).

**Migration / remediation:**
- [ ] **BUG B RESOLVED**: `src/doge/infrastructure/data_source/yfinance.py` exists and implements the port (done).
- [ ] `src/micro/tdx_downloader.py:23-26` `sys.path.insert` / `_PROJECT_ROOT` removed — replaced by import of `settings.py` (ADR-0001 forbidden pattern — OPEN).
- [ ] `TDXDataSource.download_kline` / `get_latest_market_date` no longer raise `NotImplementedError` — migrated from `tdx_downloader.py` (OPEN).
- [ ] yfinance knobs (`max_retries`, `retry_delay`, `period_days`) moved into a `YFinanceConfig` in `settings.py` (OPEN).

**Docs / observability:**
- [ ] ADR-0004 accepted (this CDD references it).
- [ ] `save_stock_data_custom` silent exception swallow (`database.py:152-153`) is at minimum logged (OPEN — observability gap).
- [ ] Registry proposals enumerated in section 4.5 are queued for Phase 5 entry approval.

## 9. Integration Requirements

This section is mandatory for data/API modules per the assignment brief.

### 9.1 Ingestion paths

1. **TDX local file** — `TDXReader.get_data` → 7-col frame (no persistence; caller writes).
2. **TDX server K-line** — `download_{cn,us}_kline` → `_bars_to_df` → `save_stock_data_custom` → `stock_prices`. Refreshes DuckDB views via `_refresh_views()` on CLI exit (`tdx_downloader.py:509-517`).
3. **TDX server raw `.day`** — DEPRECATED; do not rely on. US raw is silently `goods_kline`.
4. **yfinance** — `YFinanceDataSource.download_kline` → 8-col frame. The adapter does NOT write to the DB itself; the caller (a future service in Module #2/#4) is responsible for calling `save_stock_data_custom`. This keeps the adapter pure and testable.

### 9.2 Write paths & retention

- Single table `stock_prices` with composite PK `(ticker, date)` (`database.py:100-112`).
- Incremental upsert: only rows with `date > MAX(date)` for the ticker are appended (`database.py:138-144`).
- Retention: rows older than `retention_days` (default 180) are deleted per ticker after each write (`database.py:146-149`).
- No transaction spanning multiple tickers — each `save_stock_data_custom` call is its own commit.

### 9.3 Concurrency model

- **Current State**: single-threaded per market. The downloader processes tickers sequentially; `find_working_server` uses a bounded `ThreadPoolExecutor(max_workers=10)` only for server *probing*, not for data fetch. No DB-level write lock is held across tickers.
- **Target (Migration)**: if parallel fetch is introduced, all writers must serialize on a single SQLite connection or use WAL mode; concurrent default-mode writers will raise `database is locked`.

### 9.4 Refresh / zero-copy behavior

- **No zero-copy**: every path materializes a `pandas.DataFrame` in memory before writing. The 120-day / ~120-row-per-ticker cap keeps per-ticker memory bounded (a few KB).
- **Refresh granularity**: per-ticker incremental. A full refresh (`--no-incremental`) re-requests 800 bars and lets the retention pruner drop old rows; it does NOT drop-and-recreate the table.
- **Idempotency**: re-running a refresh for an up-to-date ticker is a no-op (`skip` path) — no duplicate rows, no spurious deletes.

### 9.5 Retry budgets & offline/degraded behavior

| Source | Retry budget | Backoff | Offline outcome |
|---|---|---|---|
| TDX server (per ticker) | reconnect after 5 consecutive failures | none (immediate reconnect) | abort whole run, keep already-saved rows |
| TDX server probe | 20 candidates, 5s timeout | first-responder wins | exit 1 if none respond |
| yfinance | `max_retries=3` | fixed `retry_delay=5.0`s | return `None` per ticker (degraded, not crash) |

**Offline principle** (ADR-0001 / ADR-0004): network failure must never corrupt local data or crash the operator's session. The platform continues to serve from the most recent successful refresh; scans and reports run against stale-but-intact rows.

### 9.6 The 120d fetch default

Every ingestion path defaults to the most recent **~120 trading days** per ticker:
- `TDXReader.MAX_DAYS = 120` (`tdx_loader.py:64`)
- downloader `--max-bars` default `120` (`tdx_downloader.py:537`)
- `_bars_to_df(..., max_rows=120)` (`tdx_downloader.py:148`)
- yfinance `DEFAULT_PERIOD_DAYS = 120` (`yfinance.py`)

This alignment is deliberate: it bounds memory, matches the ~6-month lookback used by the momentum scanner (Module #5) and macro engine (Module #4), and ensures a refresh from any source produces the same row width. Any change to this default must change all four locations in lockstep (propose registry entry `data_source.default_window_days`).
