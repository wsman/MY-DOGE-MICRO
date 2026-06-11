# CDD: MCP Server (Module #8)

> **Slug**: `mcp-server`
> **Category**: Interface
> **Status**: Reverse-documented (brownfield) — 2026-06-12; Phase-2 soft-delete consistency fix applied in this pass
> **Depends On**: #1 `runtime-configuration`, #2 `market-data-storage`, #7 `research-insight-knowledge-base`
> **Depended on by**: (none — terminal Interface module consumed by external MCP clients + the Vue Web Console #11 liveness probe)
> **Related ADRs**: [ADR-0006](../../docs/architecture/adr-0006-mcp-transport-strategy.md) (mcp-transport-strategy), [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) (interface boundary), [ADR-0003](../../docs/architecture/adr-0003-storage-repository-contract.md) (zero-copy read model)
> **Source files reverse-documented**: `mcp_server.py` (canonical live entrypoint), `src/doge/interfaces/mcp/server.py` + `src/doge/interfaces/mcp/tools/*.py` (modular mirror), `docs/MCP_SERVER.md` (operator reference, reused verbatim into §3), `.mcp.json`, `scripts/mcp_stdio.bat`, `scripts/start_mcp_sse.sh`, `scripts/start_mcp_sse.bat`
> **Bug-fix provenance**: CONSISTENCY FIX (Phase-2 soft-delete leak) — `mcp_server.py:346-372` notes block now filters `deleted_at IS NULL` (predicate built at `:352`); regression-pinned by `tests/test_mcp_notes_softdelete.py`

---

## 1. Overview

The MCP Server (`doge-db`) is the AI-facing analytical interface of MY-DOGE-MICRO. It is a single `FastMCP` server that exposes **six read-only tools** — `query_stock`, `stock_overview`, `rsrs_ranking`, `market_breadth`, `volume_anomalies`, `list_views` — over **two transports**: stdio (primary, spawned by Claude Code via `.mcp.json`) and SSE (secondary, an HTTP server for the web console and remote MCP clients). All analytical reads go through **DuckDB zero-copy over the SQLite price databases** (read-only `ATTACH`); the `stock_overview` tool additionally reads the `stock_names` and `stock_notes` tables directly from the research SQLite DB. Every tool is wrapped by a `_timed` decorator that enforces a uniform **30-second** per-tool latency budget (`asyncio.wait_for`) and converts every timeout/exception into a `"Error: ..."` string so the MCP client always receives a textual result. The module is mid-migration: a modular drop-in replacement (`src/doge/interfaces/mcp/server.py`) delegates the same six tools to `doge.core.services` through `doge.interfaces.mcp.tools.*`, but the live registered entrypoint (`.mcp.json`) still points at the monolithic `mcp_server.py`. This CDD documents both surfaces, marking the modular server as the migration target owned by module #12.

## 2. User Promise / JTBD

**Operator / AI-client JTBD**: "When I ask Claude Code (or any MCP-aware client) a question about A-share or US-share market behaviour — what is AAPL's recent price, which stocks have the strongest trend today, how broad is today's rally, what is surging on volume — I want a single local server that answers from my own freshly-synced data within 30 seconds, returns a clean text table every time (never a stack trace), and never exposes a note I retracted."

**Promise the module keeps**:
- Expose exactly six analytical tools, identical in signature, validation, and output on both transports.
- Read exclusively from local SQLite/DuckDB files (no network call inside any tool); zero-copy DuckDB reads keep memory bounded.
- Enforce input validation (market whitelist, ticker charset/length, int/float bounds) before any DB access, on both transports.
- Never raise to the MCP client: timeouts return `"Error: {tool} timed out after 30s"`, exceptions return `"Error: {ExcType}: {msg}"`.
- Provide liveness (`GET /health`) and per-tool metrics (`GET /metrics`) on the SSE transport.
- Respect the Phase-2 soft-delete contract: retracted `stock_notes` rows never appear in `stock_overview` output.

**Promise the module does NOT yet keep** (open questions, §9):
- It does not yet route tools through `doge.core.services` in the live entrypoint — the modular server exists but is not registered in `.mcp.json`.
- It does not yet authenticate SSE clients; the server is intended for loopback use, and binding to `0.0.0.0` is an unguarded operator decision.
- It does not yet have a parity test asserting the modular server's tool outputs are byte-identical to the monolith's.

## 3. Detailed Behavior

> All `file:line` citations are against the current brownfield state on `cdd-adoption-2026-06-11` **after** the Phase-2 soft-delete fix landed. Operator-facing prose for the six tools, the transports, and the Windows notes is reused **verbatim** from `docs/MCP_SERVER.md` (the existing reference); implementation specifics are cited against `mcp_server.py` / `src/doge/interfaces/mcp/server.py`.

### 3.1 Transports and launch (`mcp_server.py:474-516`)

| Transport | Purpose | Launch | Registered entrypoint |
|---|---|---|---|
| **stdio** (primary, default) | Claude Code local integration | `python mcp_server.py` (= `--transport stdio`) | `.mcp.json` → `scripts/mcp_stdio.bat` |
| **SSE** (secondary) | HTTP for the web console / remote clients | `python mcp_server.py --transport sse --host 127.0.0.1 --port 8902` | `scripts/start_mcp_sse.{sh,bat}` |

CLI args (`mcp_server.py:475-483`): `--transport {stdio,sse}` (default `stdio`), `--host` (default `127.0.0.1`), `--port` (default `8902`), `--log-level {DEBUG,INFO,WARNING,ERROR}` (default `INFO`).

**stdio mode** (`mcp_server.py:488-512`): runs the MCP SDK's `stdio_server` over `anyio`. On Windows it applies a mandatory workaround for the SDK's internal double-`TextIOWrapper` over `sys.stdout.buffer` (see §3.9): it saves `sys.stdout.buffer`, replaces `sys.stdout` with a `StringIO()`, and passes a custom anyio-wrapped stdout to `stdio_server(stdout=cl_stdout)`.

**SSE mode** (`mcp_server.py:513-516`): runs `uvicorn.run(mcp.sse_app(), host=args.host, port=args.port)`. In addition to the six MCP tools, it serves two custom Starlette routes: `GET /health` (`mcp_server.py:449-457`) and `GET /metrics` (`mcp_server.py:460-470`).

> Verbatim from `docs/MCP_SERVER.md` "部署模式": "stdio : for local Claude Code integration; sse : for standalone HTTP deployment. 启动脚本 `scripts/mcp_stdio.bat` 会自动检测项目级 venv，回退到系统 Python。"

### 3.2 Server lifecycle, logging, PID tracking (`mcp_server.py:40-159, 245-262`)

- **Logging**: `_setup_logging()` (`:53-76`) configures a `RotatingFileHandler` at `logs/mcp_server.log` (10MB x 5 backups, UTF-8) plus a `stderr` `StreamHandler`, both with a `_CorrelationFilter` that stamps every record with an 8-char `correlation_id` `ContextVar` (set per tool call by `_timed`). Format: `%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s`.
- **Metrics**: in-memory dicts `REQUEST_COUNT: Dict[str,int]` and `REQUEST_DURATION: Dict[str,List[float]]` (`:83-84`), populated by `_timed`, exposed via `/metrics`.
- **PID tracking** (`:87-155`): `_register_pid`/`_unregister_pid` append/remove the current PID to `data/.mcp_server.pid`; `_detect_orphan_processes` warns (read-only, no killing) if another `mcp_server.py` is alive, noting "DuckDB read-only mode supports concurrent access."
- **Lifespan** (`:246-259`): on start, registers PID, runs orphan detection, and pre-warms DuckDB (`SELECT 1`); on shutdown, unregisters PID.

### 3.3 The `_timed` decorator — timeout and error contract (`mcp_server.py:157-194`)

```python
TOOL_TIMEOUT = 30  # matches MCPConfig.tool_timeout (Module #1 §3.7)

def _timed(tool_name):
    # per call: set correlation_id (8-char uuid), log entry
    # result = await asyncio.wait_for(fn(...), timeout=TOOL_TIMEOUT)
    #   success  -> increment REQUEST_COUNT, append duration, log ok, return result
    #   TimeoutError -> log error, return f"Error: {tool_name} timed out after {TOOL_TIMEOUT}s"
    #   Exception    -> log error (exc_info), return f"Error: {type(exc).__name__}: {exc}"
```

This is the load-bearing contract: **no tool ever raises to the MCP client**. Validation errors (raised by `_validate_*` inside the tool body) are caught and returned as `"Error: ValueError: Invalid market: ..."` — pinned by `tests/test_mcp_tools.py::test_query_stock_invalid_market`.

### 3.4 Input validation (`mcp_server.py:197-223`)

| Helper | Rule |
|---|---|
| `_validate_market(market)` (`:201-205`) | `(market or "cn").lower()`; must be in `{"cn","us"}`; else `ValueError("Invalid market...")`. `None`/`""` → `"cn"`. |
| `_validate_ticker(ticker)` (`:208-211`) | must be non-empty str; delegates to `ai_analysis.normalize_ticker` which enforces charset `^[A-Za-z0-9.\-]+$`, max length, and CN suffix rules (`6xx/68x`→`.SH`, `0xx/3xx`→`.SZ`, `4xx/8xx`→`.BJ`). |
| `_validate_int(name, value, min=1, max=500)` (`:214-217`) | must be `int` within `[min,max]`. |
| `_validate_float(name, value, min=0.0, max=1e6)` (`:220-223`) | must be number within `[min,max]`; returns `float`. |

The modular server (`src/doge/interfaces/mcp/server.py:114-137`) reproduces these helpers verbatim, importing `normalize_ticker` from `doge.interfaces.mcp.tools.query_stock` instead of `ai_analysis`.

### 3.5 The six tools (verbatim tool semantics from `docs/MCP_SERVER.md`, impl citations)

> The tool input/output tables, return columns, and examples below are reused verbatim from `docs/MCP_SERVER.md` §"工具清单". Implementation citations added.

#### query_stock (`mcp_server.py:266-291`)

> "查询个股行情数据，含 OHLCV、均线、ATR、波动率等技术指标。"

| Param | Type | Required | Default | Constraint | Notes |
|---|---|---|---|---|---|
| `ticker` | string | yes | — | legal ticker | e.g. `601777`, `000858.SZ`, `AAPL` |
| `market` | string | no | `"cn"` | `"cn"` or `"us"` | market |
| `days` | int | no | `20` | 1 ~ 500 | days returned |

- **CN return columns**: `date, open, high, low, close, volume, ret_pct, ma_5, ma_10, ma_20, ma_60, atr14, ma60_dev, vol_20d` (from `vw_daily_enriched_cn`, `mcp_server.py:276-282`).
- **US return columns**: `date, open, high, low, close, volume, amount` (from `us.stock_prices`, `:285-287`).
- Empty result → `"No data for {t}"` (`:291`).

```
mcp__doge-db__query_stock(ticker="601777", market="cn", days=3)
date        open   high   low    close  volume    ret_pct  ma_5   ...
2026-05-07  11.00  11.40  10.92  11.32  58708796  2.63     11.20  ...
```

#### stock_overview (`mcp_server.py:294-360`)

> "个股全景：名称、板块、最新价格与涨跌幅、用户笔记。"

| Param | Type | Required | Default | Constraint |
|---|---|---|---|---|
| `ticker` | string | yes | — | legal ticker |
| `market` | string | no | `"cn"` | `"cn"` or `"us"` |

Three merged sources (`:302-372`):
1. **Name + sector** — SQLite `stock_names` (`:303-316`); failures logged, swallowed.
2. **Latest 10-day prices + pct change** — DuckDB `{cn|us}.stock_prices` (`:319-336`); failures appended as `价格查询失败: {exc}`.
3. **Notes** — SQLite `stock_notes` count + last 5 (`:346-372`). **Phase-2 fix**: now filters `deleted_at IS NULL` when the column exists (see §3.10).

```
mcp__doge-db__stock_overview(ticker="000858")
=== 000858.SZ (CN) ===
名称: 五 粮 液
最新: 2026-05-07 收盘: 92.6
涨跌幅: 0.37%
...
笔记 (2 条):
  [2026-05-06] 茅台提价带动板块情绪...
```

#### rsrs_ranking (`mcp_server.py:375-385`)

> "RSRS 动量排名，返回趋势强度最高的 Top N 股票。RSRS = R² × sign(slope), range -1.0 ~ +1.0."

| Param | Type | Required | Default | Constraint |
|---|---|---|---|---|
| `market` | string | no | `"cn"` | `"cn"` or `"us"` |
| `top` | int | no | `20` | 1 ~ 100 |

- CN view `vw_rsrs_ranking_cn`, US view `vw_rsrs_ranking_us` (`:381`).
- Returns columns owned by Module #2 §4.4 (e.g. `ticker, rsrs, avg_vol_20d, last_close, ...`).

#### market_breadth (`mcp_server.py:388-398`)

> "市场宽度：每日涨跌家数、上涨占比、平均涨跌幅。"

| Param | Type | Required | Default | Constraint |
|---|---|---|---|---|
| `market` | string | no | `"cn"` | `"cn"` or `"us"` |
| `days` | int | no | `10` | 1 ~ 100 |

- CN view `vw_market_breadth_cn` (cols incl. `advance_ratio`), US view `vw_market_breadth_us` (no `advance_ratio`) (`:394`).

#### volume_anomalies (`mcp_server.py:401-415`)

> "成交量异常检测（仅 A 股），发现放量异动。量比 = 当日成交量 / 前 20 日平均成交量。"

| Param | Type | Required | Default | Constraint |
|---|---|---|---|---|
| `min_ratio` | float | no | `3.0` | 1.0 ~ 1000.0 |
| `top` | int | no | `20` | 1 ~ 100 |

- CN-only (`vw_volume_anomalies_cn`); returns `ticker, date, volume, avg_vol, vol_ratio, ret_pct` (`:409-414`).

#### list_views (`mcp_server.py:418-442`)

> "列出所有可用的 DuckDB 分析视图及其行数和列名。无需参数。"

Returns a JSON array (`json.dumps(..., indent=2, ensure_ascii=False)`): each element `{"view": str, "rows": int|null, "columns": str}`. Per-view failures are swallowed into `{"rows": null}` (`:439-441`).

### 3.6 The modular mirror (`src/doge/interfaces/mcp/server.py`)

`create_mcp_server()` (`:141-234`) builds a `FastMCP("doge-db")` with the same six tools, but each tool delegates to the corresponding async function in `doge.interfaces.mcp.tools.*` (`query_stock`, `stock_overview`, `rsrs_ranking`, `market_breadth`, `volume_anomalies`, `list_views`), which in turn call `doge.core.services` (`StockService`, `RankingService`, `BreadthService`, `AnomalyService`, `ViewService`) over `DuckDBStockRepository` / `DuckDBConnection(read_only=True)`. This is the ADR-0001 target shape: no direct `sqlite3`/`duckdb` import in the interface layer. The validation helpers (`:114-137`) and `_timed` decorator (`:81-107`) are duplicated from the monolith. **Not yet the registered entrypoint** (`.mcp.json` still points at `mcp_server.py`).

> **Notable drift**: the modular `stock_overview` (`src/doge/interfaces/mcp/tools/query_stock.py:57-81`) uses `JSONTickerNameCache` for the name and does **not** yet read `stock_notes` at all (no notes line in its output), whereas the monolith reads notes directly from SQLite. This is an open parity gap (§9).

### 3.7 Formatting helper (`mcp_server.py:227-242`)

`_fmt(columns, rows)` renders a fixed-width space-aligned text table: floats → `{:.2f}`, others → `str()`. Empty `rows` → `""`. Used by all analytical tools.

### 3.8 Health & metrics routes (SSE only)

> Verbatim from `docs/MCP_SERVER.md`: "`GET /health` 健康检查 → `{"status": "ok"}` (200) or 503 `{"status":"error","detail":...}`. `GET /metrics` Prometheus-format tool metrics: `mcp_requests_total{tool="..."}`, `mcp_request_duration_seconds_sum{tool="..."}`, `mcp_request_duration_seconds_count{tool="..."}`; returns `{"metrics": "# no metrics yet"}` when empty."

Impl: `mcp_server.py:449-457` (health), `:460-470` (metrics).

### 3.9 Windows stdout double-TextIOWrapper workaround

> Verbatim from `docs/MCP_SERVER.md` "Windows 已知问题": "MCP SDK 内部创建 `TextIOWrapper(sys.stdout.buffer)` 与 Python 原始 `sys.stdout` 共享同一个 `BufferedWriter`。Windows 上两个 TextIOWrapper 同时 flush 导致冲突 (`OSError: [Errno 22] Invalid argument` at `mcp/server/stdio.py:81`). 修复: 在 SDK 接管前将 `sys.stdout.buffer` 保存到独立变量，`sys.stdout` 替换为 `io.StringIO()`，然后传自定义 stdout 给 `stdio_server(stdout=cl_stdout)`."

Impl: `mcp_server.py:496-512`. The modular server reproduces it at `src/doge/interfaces/mcp/server.py:251-268`.

### 3.10 Phase-2 soft-delete consistency fix (this pass)

Before this pass, `stock_overview`'s notes block (`mcp_server.py:346-372`) ran a raw `SELECT COUNT(*) ... WHERE ticker=?` and `SELECT created_at, content ... WHERE ticker=? ORDER BY created_at DESC LIMIT 5` with **no** `deleted_at` filter, so soft-deleted notes (per Module #7's BUG-A soft-delete contract) leaked into MCP responses. The live `stock_notes` table may or may not have the `deleted_at` column yet (Module #7's `_ensure_deleted_at_column` is lazy and runs only on the `stock_notes.py` read paths, not here), so the fix:

1. Reads `PRAGMA table_info(stock_notes)` once per call (`:349-351`).
2. If `deleted_at` is present, appends ` AND deleted_at IS NULL` to both the COUNT and SELECT predicates (`:352`).
3. If absent, runs the legacy predicate unchanged (no `OperationalError`).

Pinned by `tests/test_mcp_notes_softdelete.py` (3 tests: soft-deleted excluded; legacy schema still works; empty marker shown).

## 4. Contracts / Data Model

### 4.1 Tool I/O contracts (all tools return `str`)

```python
# All async, all wrapped by @_timed(<name>), all never raise to the client.
async def query_stock(ticker: str, market: str = "cn", days: int = 20) -> str
async def stock_overview(ticker: str, market: str = "cn") -> str
async def rsrs_ranking(market: str = "cn", top: int = 20) -> str
async def market_breadth(market: str = "cn", days: int = 10) -> str
async def volume_anomalies(min_ratio: float = 3.0, top: int = 20) -> str
async def list_views() -> str
```

### 4.2 Error contract (load-bearing)

| Outcome | Return value | Client-visible |
|---|---|---|
| Success | formatted string (table / JSON / message) | yes |
| Validation failure (raised `ValueError` inside tool) | `"Error: ValueError: {msg}"` | yes (not raised) |
| Tool timeout (>30s) | `"Error: {tool_name} timed out after 30s"` | yes |
| Any other exception | `"Error: {ExcType}: {msg}"` | yes |
| No data (`query_stock`) | `"No data for {ticker}"` | yes |
| Empty result (ranking/breadth/anomaly) | `"No data"` / `"No anomalies"` | yes |

`stock_overview` is more lenient: per-source failures (name, price, notes) are swallowed into the assembled text (`名称:` omitted, `价格查询失败: {exc}` appended, `暂无笔记` appended); the tool still returns 200 with a partial body.

### 4.3 Transport contracts

| Transport | Wire | Endpoint | Custom routes |
|---|---|---|---|
| stdio | JSON-RPC over process stdin/stdout | `python mcp_server.py` (child of Claude Code) | none |
| SSE | HTTP + Server-Sent Events | `http://{host}:{port}/sse`, `/messages/` | `GET /health`, `GET /metrics` |

### 4.4 Health/metrics response schemas

```jsonc
// GET /health (200)
{"status": "ok"}
// GET /health (503)
{"status": "error", "detail": "<exc str>"}
// GET /metrics (200) — Prometheus text wrapped in JSON
{"metrics": "mcp_requests_total{tool=\"query_stock\"} 12\nmcp_request_duration_seconds_sum{tool=\"query_stock\"} 4.520000\n..."}
// GET /metrics (200, empty)
{"metrics": "# no metrics yet"}
```

### 4.5 Read-source contract (zero-copy)

- `query_stock`, `rsrs_ranking`, `market_breadth`, `volume_anomalies`, `list_views`, and the price block of `stock_overview`: DuckDB read via `ai_analysis.get_duckdb_connection()` (read-only attach of `market_data_cn.db` / `market_data_us.db`). No writes; no OHLCV duplication into DuckDB.
- `stock_overview` name + notes blocks: direct `sqlite3.connect(RESEARCH_DB)` (raw `stock_names`, `stock_notes`). This is an ADR-0001 drift (interface opening SQLite directly) owned by Module #12.

### 4.6 Registry proposals (BLOCKING Phase 5 — do NOT write registry files)

> Routing note: `docs/registry/architecture.yaml` exists today and holds cross-ADR stances; no `entities.yaml` yet (same open question as Modules #2/#3/#7).

**(a) `architecture.yaml` candidates — stances / contracts:**
- `mcp.transport.stdio_primary` = `stdio is the default + registered Claude Code entrypoint; SSE is secondary` (ADR-0006).
- `mcp.transport.zero_copy_reads` = `DuckDB read-only ATTACH over SQLite price DBs; no OHLCV duplication` (ADR-0006 / ADR-0003).
- `mcp.tool.error_contract` = `every tool returns str; timeouts/errors become "Error: ..." strings, never raised to client` (ADR-0006).
- `mcp.tool.soft_delete_aware` = `stock_overview notes read filters deleted_at IS NULL when the column exists` (Phase-2 fix).

**(b) Value-constant candidates (awaiting `entities.yaml`):**
- `mcp.tool_timeout` = 30s (mirrors `MCPConfig.tool_timeout`, Module #1 §3.7).
- `mcp.market_whitelist` = `{"cn","us"}`.
- `mcp.ticker_charset` = `^[A-Za-z0-9.\-]+$`.
- `mcp.int_range.days` = `[1,500]`; `mcp.int_range.top` = `[1,100]`; `mcp.float_range.min_ratio` = `[1.0,1000.0]`.
- `mcp.sse.host` = `127.0.0.1`; `mcp.sse.port` = `8902`.
- `mcp.tool_set` = `{query_stock, stock_overview, rsrs_ranking, market_breadth, volume_anomalies, list_views}` (6 tools; `run_sql` explicitly absent — pinned by `test_run_sql_removed`).

## 5. Edge Cases

| Situation | What happens (Current State) |
|---|---|
| **Invalid `market`** (e.g. `"hk"`, `"cn; DROP TABLE"`) | `_validate_market` raises `ValueError`; `_timed` catches it → returns `"Error: ValueError: Invalid market: ..."`. Pinned by `test_invalid_market`, `test_query_stock_invalid_market`. |
| **Ticker with SQL-injection chars** (`"1; DROP TABLE"`, `"600000@evil"`, unicode `"6零零零零零"`) | `_validate_ticker`/`normalize_ticker` rejects via charset regex → `ValueError("invalid characters")`. Pinned by `test_invalid_ticker_*`. |
| **Ticker too long** (>20 chars) | `normalize_ticker` raises `ValueError("too long")`. Pinned by `test_too_long_raises`. |
| **`days`/`top` out of range or non-int** | `_validate_int` raises; caught by `_timed` → `"Error: ..."`. Pinned by `test_validate_int_*`, `test_volume_anomalies_invalid_ratio`. |
| **`min_ratio` out of range** | `_validate_float` raises; `"Error: ValueError: min_ratio must be a number between 1.0 and 1000.0"`. Pinned by `test_volume_anomalies_invalid_ratio`. |
| **Tool exceeds 30s** | `asyncio.TimeoutError` → `"Error: {tool} timed out after 30s"`; logged at ERROR. Pinned by `test_timeout_returns_error`. |
| **Tool raises any other exception** | caught → `"Error: {ExcType}: {msg}"`; logged with `exc_info`. Pinned by `test_exception_returns_error_string`. |
| **No price data for ticker** (`999999.SH`) | `query_stock` → `"No data for 999999.SH"`; `stock_overview` → still returns a body with `999999.SH (CN)` header and `暂无笔记`. Pinned by `test_query_stock_no_data`, `test_overview_no_data`. |
| **DuckDB attach fails (price block of `stock_overview`)** | Swallowed; `价格查询失败: {exc}` line appended; notes/name blocks still run. |
| **`stock_names` lookup fails** | Logged at ERROR; name/sector lines omitted silently; tool still returns 200. |
| **`stock_notes` table missing the `deleted_at` column (pre-Phase-2 legacy DB)** | The fixed notes block detects the absence via `PRAGMA table_info` and runs the legacy predicate without `deleted_at IS NULL` — no `OperationalError`. Pinned by `test_legacy_schema_without_deleted_at_still_works`. |
| **Soft-deleted note exists** | The fixed notes block filters `deleted_at IS NULL`; the retracted note is excluded from both the count and the list. Pinned by `test_soft_deleted_note_excluded_from_count_and_list`. |
| **Concurrent `mcp_server.py` processes** | `_detect_orphan_processes` logs a WARNING (read-only, no kill); DuckDB read-only attach supports concurrent readers. |
| **SSE `/health` when DuckDB is down** | `con.execute("SELECT 1")` raises → 503 `{"status":"error","detail":...}`. Pinned by `test_health_duckdb_failure`. |
| **SSE `/metrics` with no tool calls yet** | Returns `{"metrics": "# no metrics yet"}`. Pinned by `test_metrics_empty`. |
| **Operator binds SSE to `0.0.0.0`** | Server exposes unauthenticated MCP tools + `/health` + `/metrics` to the LAN. No guardrail; documented risk (§7). |
| **Windows stdio without the workaround** | Would raise `OSError: [Errno 22]` at SDK `stdio.py:81` on `stdout.flush()`. Workaround is mandatory and applied in both servers. |
| **MCP client sends `run_sql`** | Tool is absent (`test_run_sql_removed`); the client gets a method-not-found error from the SDK, not a server exception. |

## 6. Dependencies

**Upstream (this module depends on):**
- **#1 `runtime-configuration`** — `MCPConfig` (`settings.py:67-73`) owns `tool_timeout=30`, `stdio_transport="stdio"`, `sse_host="127.0.0.1"`, `sse_port=8902`. The monolith reads `data_dir` for logging via `_HERE` (legacy recalculation, ADR-0001 drift); the modular server reads `get_settings().data_dir` cleanly (`src/doge/interfaces/mcp/server.py:34`). Module #1's `Depended on by` lists `#8 mcp-server`.
- **#2 `market-data-storage`** — owns the DuckDB zero-copy read model (`get_duckdb_connection`, `vw_*` views), the SQLite price DBs, and `RESEARCH_DB`. Every analytical tool reads through these. Module #2's `Depended on by` lists `#8 mcp-server`.
- **#7 `research-insight-knowledge-base`** — owns the `stock_notes` soft-delete contract (`deleted_at IS NULL` on all reads) that this module's `stock_overview` notes block must honour. The Phase-2 fix in this pass closes the consistency gap Module #7 §9 #4 flagged. Module #7's `Depended on by` lists `#8 mcp-server`.
- **Python packages**: `mcp==1.25.0` (`FastMCP`, `mcp.server.stdio.stdio_server`, `mcp.types`), `starlette` (SSE app + `Request`/`JSONResponse`), `uvicorn==0.38.0`, `anyio`, `duckdb==1.4.4` (transitively via `ai_analysis`), `sqlite3` (stdlib, for `stock_overview` raw reads).

**Downstream (depend on this module):**
- **External MCP clients** — Claude Code (stdio, primary), the Vue Web Console (#11) liveness probe against SSE `/health`, and any remote MCP-aware client (SSE). None are in-repo modules; the Web Console reaches `/health`/`/metrics` over HTTP but does not import this module's Python.
- No in-repo `src/` module imports `mcp_server.py`; it is a terminal entrypoint.

**Documents / ADRs:**
- [ADR-0006](../../docs/architecture/adr-0006-mcp-transport-strategy.md) — the transport strategy decision (this module's governing ADR; **Status: Accepted**).
- [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) — the interface/adapter boundary; the monolith's direct `sqlite3`/`duckdb` use and `_HERE` root recalculation are recorded drifts owned by Module #12.
- [ADR-0003](../../docs/architecture/adr-0003-storage-repository-contract.md) — the zero-copy DuckDB read contract the analytical tools depend on.
- `docs/MCP_SERVER.md` — the operator-facing reference whose tool/transport content is reused verbatim into §3.

**Bidirectional notes (per design-docs rule):**
- Module #1 §6.2, Module #2 §6, and Module #7 §6 each already list `#8 mcp-server` in their *Depended on by*; this CDD's §6 closes the reverse link.

## 7. Configuration Knobs

| Knob | Where | Default | Valid range / enum | Env ownership | Operational risk |
|---|---|---|---|---|---|
| `TOOL_TIMEOUT` | `mcp_server.py:157` / `src/doge/.../server.py:78` | `30` (s) | positive int | code (mirrors `MCPConfig.tool_timeout`, Module #1 §3.7) | **MEDIUM** — raising risks long stalls for AI clients; lowering truncates valid queries. Not env-overridable in the monolith today (open question). |
| `--transport` | `mcp_server.py:476` | `stdio` | `stdio` \| `sse` | CLI arg | LOW — stdio is default and safe. |
| `--host` (SSE) | `mcp_server.py:480` | `127.0.0.1` | IP/hostname | CLI arg / `MCP_HOST` in `scripts/start_mcp_sse.{sh,bat}` | **HIGH if changed to `0.0.0.0`** — exposes unauthenticated MCP tools to the LAN. Loopback is the safe default. |
| `--port` (SSE) | `mcp_server.py:481` | `8902` | TCP port 1-65535, unused | CLI arg / `MCP_PORT` in `scripts/start_mcp_sse.{sh,bat}` | LOW unless port collides. |
| `--log-level` | `mcp_server.py:482` | `INFO` | `DEBUG`\|`INFO`\|`WARNING`\|`ERROR` | CLI arg | LOW. |
| `_MARKET_WHITELIST` | `mcp_server.py:198` | `{"cn","us"}` | fixed set | code | LOW for current scope; adding a market requires code + data pipeline. |
| ticker charset | `ai_analysis.normalize_ticker` | `^[A-Za-z0-9.\-]+$` | regex | code | LOW — injection-safe by construction. |
| `days`/`top` bounds | `_validate_int` callers | `[1,500]` / `[1,100]` | int ranges | code | LOW. |
| `min_ratio` bounds | `_validate_float` (`:220`) — called by `volume_anomalies` (`:405`) | `[1.0, 1000.0]` | float range | code | LOW. |
| log file path | `LOG_DIR` (`:41`) | `<root>/logs/mcp_server.log` | path | code (legacy `_HERE` recalc) | LOW — created if missing. |
| PID file | `PID_FILE` (`:87`) | `<root>/data/.mcp_server.pid` | path | code | LOW — read-only orphan detection. |

**Migration target (vs. Current State):**
- *Current State*: `TOOL_TIMEOUT` is a module constant duplicated in both servers; `--host`/`--port` defaults are duplicated between `argparse` and `MCPConfig`; the monolith recomputes `_HERE` for the log dir (ADR-0001 drift); `MCP_HOST`/`MCP_PORT` env support lives only in the shell scripts, not in `mcp_server.py`.
- *Target (Migration)*: `TOOL_TIMEOUT`, `host`, `port` read from `MCPConfig` (single source); the monolith is retired in favour of the modular server; no `_HERE` recalculation. Tracked under Module #12.

## 8. Acceptance Criteria

**Contract / data-model:**
- [x] `await srv.mcp.list_tools()` returns exactly the six tools and `run_sql` is absent (verified — `tests/test_mcp_tools.py::TestToolsNotPresent`).
- [x] Every tool has a non-empty Chinese description (verified — `test_tools_have_descriptions`, `test_tools_descriptions_are_chinese`).
- [x] `_validate_market`/`_validate_ticker`/`_validate_int`/`_validate_float` enforce the documented whitelists/ranges/charset (verified — `TestValidateMarket`, `TestValidateTicker`, `TestValidateInt`, `TestValidateFloat`).
- [x] `_timed` records `REQUEST_COUNT`/`REQUEST_DURATION` on success, returns `"Error: ... timed out"` on timeout, returns `"Error: {ExcType}: {msg}"` on exception, sets an 8-char `correlation_id` (verified — `TestTimedDecorator`).
- [x] `_fmt` renders floats to 2 decimals, aligns columns, returns `""` for empty rows (verified — `TestFormatHelper`).

**Transport:**
- [x] stdio `initialize` handshake returns `serverInfo.name == "doge-db"` (verified — `tests/test_transport.py::TestStdioTransport`).
- [x] SSE `/health` returns 200 `{"status":"ok"}` and 503 on DuckDB failure; `/metrics` returns Prometheus text or `# no metrics yet`; `/sse` exists (verified — `TestSseTransport`, `TestSseRoutes`).

**Integration (real DB, no network):**
- [x] `query_stock`/`stock_overview`/`rsrs_ranking`/`market_breadth`/`volume_anomalies`/`list_views` return strings against the live local DBs; CN/US paths exercised; boundary `days=1`/`top=5` honoured (verified — `TestQueryStockIntegration` … `TestListViewsIntegration`).
- [x] `list_views` returns JSON containing all 7 documented views (verified — `test_list_views_contains_known_views`).

**Phase-2 soft-delete consistency (this pass):**
- [x] `stock_overview` excludes soft-deleted notes from both count and list when `deleted_at` exists (verified — `tests/test_mcp_notes_softdelete.py::test_soft_deleted_note_excluded_from_count_and_list`).
- [x] `stock_overview` does NOT raise on a legacy DB lacking `deleted_at` (verified — `test_legacy_schema_without_deleted_at_still_works`).
- [x] `stock_overview` shows `暂无笔记` when no active notes exist (verified — `test_no_notes_shows_empty_marker`).
- [x] **Fix proven load-bearing**: the buggy (no-predicate) query returns count=2 including the retracted note; the fixed query returns count=1 with only the active note (verified by direct SQLite simulation during this pass).

**Docs:**
- [x] This CDD cites real `file:line` for every claim (auditable).
- [x] ADR-0006 is `Accepted` (authored in this pass).
- [x] Registry proposals in §4.6 are queued for Phase 5 entry approval (not written).

**Migration / remediation (OPEN — owned by Module #12):**
- [ ] `.mcp.json` points at the modular `src/doge/interfaces/mcp/server.py` once a parity test proves byte-identical tool outputs.
- [ ] Parity test: `create_mcp_server()` exposes the same six tools with matching validation; the modular `stock_overview` gains the notes block (currently absent — §3.6 drift).
- [ ] No direct `sqlite3`/`duckdb` import in the interface layer (the monolith's `import sqlite3` + `get_duckdb_connection` are ADR-0001 drifts; the modular server already complies).
- [ ] `TOOL_TIMEOUT`/`host`/`port` sourced from `MCPConfig` (single source), not duplicated constants/CLI defaults.

## 9. Integration Requirements

> Appended per the special instructions for Interface/Integration modules. Cross-cuts ADR-0006 (transport) and ADR-0003 (zero-copy read).

### 9.1 Transport / protocol

- **stdio (primary)**: JSON-RPC 2.0 over the process stdin/stdout. Claude Code spawns `scripts/mcp_stdio.bat` → `python mcp_server.py` as a child; `protocolVersion: "2024-11-05"` is accepted by the SDK (`tests/test_transport.py::test_stdio_initialize` pins the handshake). The Windows stdout workaround (§3.9) is mandatory.
- **SSE (secondary)**: HTTP + Server-Sent Events. `mcp.sse_app()` is served by Uvicorn; MCP messages flow over `/sse` (the event stream) and `/messages/` (POST). Two custom Starlette routes (`/health`, `/metrics`) are mounted on the same app.
- **One server, two transports**: both transports expose the identical six tools with identical signatures, validation, and error contract. No transport-specific tool behaviour.

### 9.2 Request / response schemas

- **Tool call (both transports)**: MCP `tools/call` with `name` ∈ the six-tool set and `arguments` matching §4.1. Response is always a single `TextContent` whose `text` is the formatted string or an `"Error: ..."` string.
- **`GET /health`**: `200 {"status":"ok"}` | `503 {"status":"error","detail":"<exc>"}`.
- **`GET /metrics`**: `200 {"metrics":"<prometheus text>"}` (Prometheus text wrapped in JSON; `# no metrics yet` when empty).
- **`GET /sse`**: 200, `text/event-stream` (the MCP SSE channel).

### 9.3 Error contracts

- **Tool-level**: every tool returns `str`; no exception ever propagates to the MCP client. Timeouts (`>30s`) → `"Error: {tool} timed out after 30s"`; validation/other exceptions → `"Error: {ExcType}: {msg}"` (§4.2). This is the load-bearing integration invariant — AI clients must never see a stack trace.
- **Health-level**: DuckDB failure → HTTP 503 with a `detail` string (the only place an exception message crosses the wire intentionally, for operator diagnostics).
- **Per-source leniency (`stock_overview`)**: name/price/notes sub-failures are swallowed into the assembled text; the tool still returns 200 with a partial body.

### 9.4 CORS

- **Current State**: the MCP SSE app does **not** configure CORS. The Vue Web Console (#11) is expected to reach `/health`/`/metrics` from a same-origin or loopback context; cross-origin browser consumption of the MCP tools is not supported today.
- **Target (Migration)**: if a browser client needs to call MCP tools directly, add a `CORSMiddleware` scoped to the loopback origin. Track alongside Module #9's `allow_origins=["*"]` review. (Open question §9.)

### 9.5 Concurrency

- **Read concurrency**: all DuckDB reads use `read_only=True` attach (`ai_analysis.get_duckdb_connection`); multiple MCP readers (and multiple `mcp_server.py` processes) coexist — `_detect_orphan_processes` confirms this is by design. No write occurs inside any tool.
- **Process concurrency**: the PID file (`data/.mcp_server.pid`) is append-only; orphan detection is read-only and never kills. Two simultaneous stdio servers (e.g. two Claude Code windows) are safe for reads.
- **In-process**: `_timed` sets a `ContextVar` `correlation_id` per call, so concurrent tool calls do not cross-correlate their log lines. `REQUEST_COUNT`/`REQUEST_DURATION` are plain dicts mutated without a lock — a benign race at local-first scale (last-write on the counter); not thread-safe under high fan-out (open question).

### 9.6 Timeouts

- **Per-tool**: `TOOL_TIMEOUT = 30` seconds, enforced by `asyncio.wait_for` inside `_timed` (matches `MCPConfig.tool_timeout` and `standards/technical-preferences.md`). Applies identically on stdio and SSE.
- **SSE startup**: Uvicorn + DuckDB pre-warm (`SELECT 1`) typically <2s; `tests/test_transport.py` allows up to ~5s for the server to answer `/health`.
- **Health-check DB probe**: `con.execute("SELECT 1")` — no explicit timeout; bounded by DuckDB's own connect latency. If the DuckDB file is locked by a long write, `/health` could block (open question: add a small timeout to the health probe).

### 9.7 Observability

- **Logs**: `logs/mcp_server.log` (rotating 10MB×5, UTF-8) with per-call `correlation_id`; `stderr` mirror. Every tool call logs entry (`TOOL CALL: {name} args=...`), success (`ok duration=...s result_len=...`), timeout, and error (with `exc_info`).
- **Metrics**: `/metrics` exposes `mcp_requests_total{tool}` and `mcp_request_duration_seconds_{sum,count}{tool}` for every tool that has been called at least once.
- **PID tracking**: `data/.mcp_server.pid` enables orphan detection across operator sessions.

---

*Reverse-documented 2026-06-12. Source of truth: `mcp_server.py`, `src/doge/interfaces/mcp/server.py`, `docs/MCP_SERVER.md`, `.mcp.json` on branch `cdd-adoption-2026-06-11` post Phase-2 soft-delete fix. Operator-facing tool/transport prose reused verbatim from `docs/MCP_SERVER.md`.*
