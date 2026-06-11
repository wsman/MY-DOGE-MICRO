# CDD: FastAPI Service (Module #9)

> **Module #9** — Category: **Interface**
> **Slug**: `fastapi-service`
> **Status**: Reverse-documented (brownfield) — 2026-06-12; BUG E fixed + router tests added 2026-06-12
> **Depends on**: #1 `runtime-configuration`, #2 `market-data-storage`, #4 `macro-strategy-engine`, #5 `micro-momentum-scanner`
> **Depended on by**: #11 `vue-web-console` (the web UI consumes this API), #10 `pyqt-desktop-dashboard` (desktop may also call it)
> **Source files reverse-documented**: `src/api/main.py`, `src/api/routers/{scan,data,notes,macro,analysis,config}.py`
> **Related ADRs**: [ADR-0007](../../docs/architecture/adr-0007-api-surface-and-cors.md) (api-surface-and-cors — **this module's** decision), [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) (clean architecture, forbidden patterns), [ADR-0002](../../docs/architecture/adr-0002-centralized-configuration.md) (centralized configuration)

---

## 1. Overview

The FastAPI Service is the local-first HTTP interface layer of MY-DOGE-MICRO. It is a single FastAPI application (`src/api/main.py`) that binds to `127.0.0.1:8901` and exposes **26 product routes** — **24 across six routers** (`scan`, `data`, `notes`, `macro`, `analysis`, `config`) plus two top-level helpers (`/api/health`, `/api/stats`). It is the backend that the Vue web console (Module #11) and optionally the PyQt desktop dashboard (Module #10) call to trigger market scans, browse persisted price/report data, manage stock notes (with soft-delete), read macro and research reports, validate TDX paths, and read/write operator settings. The service is mid-migration: every router still recomputes its own `_PROJECT_ROOT` via `os.path.dirname` chains (ADR-0001 forbidden pattern `_PROJECT_ROOT_recalculation`), opens SQLite connections directly inside the interface layer (`direct_sqlite_import_in_interface`), and the scan router imports `init_db_custom` from the legacy storage module (`scan.py:150`, used at `scan.py:153`) — both ADR-0001 violations tracked as remediation in Section 8. Error handling is also non-compliant: handlers use the anti-pattern `except Exception as e: raise HTTPException(500, str(e))` (`data.py:141-142`, `notes.py:31-32,48-49,58-59,67-68,76-77`) which leaks internal messages — tracked tech debt (Section 8 + ADR-0007).

## 2. User Promise / JTBD

**Operator JTBD**: "From my browser (or desktop), drive the whole platform over a local HTTP API — start a scan and watch its progress stream in, browse the data I just downloaded, manage my stock notes, read the latest macro and research reports, and configure my TDX install — all on `localhost`, with no remote clients and no auth burden, and with predictable JSON/SSE responses I can build a UI against."

**The module must reliably**:
- Serve a stable JSON contract on every read endpoint (status code, documented key fields), a `400`/`422` on validation failure, a `404` when a requested resource is absent, and a non-`5xx`-leaking error shape on internal failure (the last is a **target**, not current behavior — see Section 8).
- Stream scan and macro-run progress over Server-Sent Events (`sse-starlette` `EventSourceResponse`) so long-running work does not block the request thread.
- Serialize at most one concurrent scan per market (`_scan_locks`, `scan.py:20`) and reject a second with `409`.
- Soft-delete notes (Bug A fix, Phase 2) so `DELETE /api/notes/{id}` returns `200 {"ok": true}` on success and `404` when no active note exists, and the deleted note is hidden from all read paths.
- Keep configuration (API key, model, TDX path) out of source: `models_config.json` / `user_settings.json` files only, never inlined.

**The module does NOT yet keep** (open questions, Section 9): centralized configuration (`_PROJECT_ROOT` per router instead of `get_settings()`), repository-routed data access (no `IStockRepository`/`IReportRepository` injection — routers open SQLite directly), a stable non-leaking error envelope, auth (intentionally absent for local-first), or a tightened CORS origin list.

## 3. Detailed Behavior

### 3.1 Application construction (`src/api/main.py`)

- `app = FastAPI(title="MY-DOGE API", version="0.1.0")` (`main.py:20`).
- Sets `OPENBLAS_NUM_THREADS=1` / `OMP_NUM_THREADS=1` via `os.environ.setdefault` at import (`main.py:12-13`) — process-global BLAS shim shared with `src/ai_analysis/__init__.py` and `src/doge/infrastructure/database/duckdb.py` (Module #1 §3.12).
- Adds `CORSMiddleware` with `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]` (`main.py:22-27`). The inline comment "仅 localhost, 无安全风险" records the local-first rationale — the server binds to `127.0.0.1` (`main.py:67`), so `*` cannot be reached from a remote client in the default deployment. ADR-0007 records this decision and a hardening option (tighten to explicit localhost origins).
- Registers the six routers under `/api/<router>` prefixes (`main.py:30-35`).
- Two top-level helpers: `/api/health` (`main.py:38-40`, returns `{"status":"ok"}`) and `/api/stats` (`main.py:43-62`, opens each of the three DB files directly with `sqlite3` and returns per-table row counts — a `direct_sqlite_import_in_interface` violation, Section 8).
- `_PROJECT_ROOT` recomputed locally (`main.py:9`) — forbidden pattern.
- `if __name__ == "__main__": uvicorn.run(app, host="127.0.0.1", port=8901)` (`main.py:65-67`).

### 3.2 scan router (`src/api/routers/scan.py`)

| Route | Behavior | file:line |
|---|---|---|
| `GET /api/scan/servers` | Returns CN/US TDX server lists with fixed ports (cn 7709, us 7727). Sourced from `tdx_downloader.CN_SERVERS/US_SERVERS` if importable, else a hardcoded fallback IP list (`scan.py:30-51`). | `scan.py:44-51` |
| `POST /api/scan/servers/test` | Body `{market}`; rejects `market not in {cn,us}` with `400` (`scan.py:61-62`); otherwise concurrently probes each server with `opentdx.TdxClient` (timeout 5s, pool 15s) and returns `{results:[{host, ok, latency_ms, error?}]}` in original order. | `scan.py:58-108` |
| `GET /api/scan/status` | Returns the in-memory `_scan_status = {cn,us}` map (`idle`/`running`). | `scan.py:121-123` |
| `POST /api/scan/{market}` | Body `ScanRequest{tdx_path, use_server, server?}`. Rejects invalid market with `400` (`scan.py:128-129`). Acquires `_scan_locks[market]` non-blocking; on failure returns `409 "{market} scan already running"` (`scan.py:131-132`). On success sets status `running` and returns an SSE stream of `{progress, message}` events ending at `progress=100` (done) or `progress=-1` (error). The worker thread calls **`init_db_custom`** directly (`scan.py:150-153`) — the ADR-0001 forbidden-pattern remediation AC. | `scan.py:126-237` |

The worker (`run_scan`, `scan.py:148-226`) prefers a TDX server download (`find_working_server` + `download_{cn,us}_kline`), falls back to local `.day` files via `MarketScanner` (`_run_local_scan`, `scan.py:240-251`), and best-effort refreshes the DuckDB views via `connect_duckdb`/`run_views_sql` (`scan.py:208-215`, failure swallowed). Errors are pushed onto the SSE queue as `progress=-1` (`scan.py:220-223`); the lock is always released in `finally` (`scan.py:224-226`).

### 3.3 data router (`src/api/routers/data.py`)

- `_DB_MAP` is built at import from `_PROJECT_ROOT` pointing at `market_data_cn.db`, `market_data_us.db`, `research_insights.db` (`data.py:13-17`) — `_PROJECT_ROOT_recalculation` violation.
- `GET /api/data/{market}/tables` — `market in _DB_MAP` else `400` (`data.py:24-25`); if DB absent returns `{"tables": []}` (`data.py:27-28`); else lists `sqlite_master` tables (`data.py:29-34`). Opens SQLite directly (`direct_sqlite_import_in_interface`).
- `GET /api/data/{market}/table/{table_name}` — `Query` constraints: `page>=1`, `1<=page_size<=500`, `sort_order in {asc,desc}` (`data.py:41-45`). Invalid market → `400`; DB absent → `404`; table absent → `404` (`data.py:47-61`). Builds a parameterized `WHERE`/`ORDER BY`/`LIMIT`/`OFFSET` query (table/column interpolated into SQL but values parameterized). Returns `{columns, rows, total, page, page_size}`.
- `GET /api/data/{market}/ticker/{ticker}/kline` — `days` constrained `1..365` (`data.py:104`). Uses `connect_duckdb()` lazily (`data.py:110`): CN reads `vw_daily_enriched_cn` (with MA/ATR columns), US reads raw `us.stock_prices`. On any exception: `raise HTTPException(500, str(e))` (`data.py:141-142`) — **error-leak anti-pattern**. Returns `{"data": [...]}` sorted by date asc.
- `GET /api/data/{market}/ticker-names` — `market in {cn,us}` else `400`. `_load_ticker_names` (`data.py:149-187`) reads a local `<data>/<market>_ticker_names.json` cache (in-process `_ticker_names_cache`), else for `cn` falls back to `akshare.stock_info_a_code_name()` (network) and writes the cache; `us` has no online fallback. Returns `{names, count}`.

### 3.4 notes router (`src/api/routers/notes.py`)

All handlers import `stock_notes` lazily via the **fully-qualified** `from src.ai_analysis.stock_notes import ...` path (`notes.py:25,38,55,65,75,88`). Body model `NoteCreate{ticker, content, market?, note_type?, title?, tags?}` (`notes.py:12-18`).

| Route | Behavior | file:line |
|---|---|---|
| `GET /api/notes/ticker/{ticker}` | `get_ticker_with_context(ticker)`; converts `price_data` DataFrame to records. Wrap: `except Exception as e: raise HTTPException(500, str(e))` (error-leak). | `notes.py:21-32` |
| `POST /api/notes` | `add_note(...)` returns the new `id`. Error-leak wrap. | `notes.py:35-49` |
| `GET /api/notes/search` | `Query(q, min_length=1)` — missing/empty `q` → `422`. Error-leak wrap. | `notes.py:52-59` |
| `GET /api/notes/recent` | `days=7, limit=100` query params. Error-leak wrap. | `notes.py:62-68` |
| `GET /api/notes/tracked` | Lists tickers with note counts. Error-leak wrap. | `notes.py:71-77` |
| `DELETE /api/notes/{note_id}` | **Bug A fix (Phase 2)**: `delete_note(note_id)` soft-deletes (`stock_notes.py:175-198`). Returns `200 {"ok": true}` when a row was affected, `404 "note not found"` otherwise. **No** error-leak wrap (the only handler that does not swallow). | `notes.py:80-92` |

Soft-delete contract: `stock_notes.deleted_at` is nullable; all read queries (`get_notes`, `search_notes`, `list_tracked_tickers`, `get_recent_notes`, `get_ticker_with_context`) filter `deleted_at IS NULL` (`stock_notes.py:73,156,209,225,244`). `_ensure_deleted_at_column` (`stock_notes.py:29-49`) idempotently migrates a legacy schema on first call.

### 3.5 macro router (`src/api/routers/macro.py`)

| Route | Behavior | file:line |
|---|---|---|
| `GET /api/macro/reports` | Lists `macro_reports` (id/date/timestamp/tags/analyst/risk_signal/volatility). If research DB absent → `{"reports": []}`. | `macro.py:22-35` |
| `GET /api/macro/reports/latest` | Latest report by `date DESC, timestamp DESC`. DB absent → `404 "no reports"`; empty table → `404 "no reports"`. | `macro.py:38-53` |
| `GET /api/macro/reports/{report_id}` | Single report by id. Absent → `404 "not found"`. | `macro.py:56-68` |
| `POST /api/macro/run` | Body `MacroRunRequest{profile_name?}` (all optional). Returns an SSE stream. The worker (`macro.py:88-118`) calls `GlobalMacroLoader` (yfinance fetch, Module #3/#4), `DeepSeekStrategist.generate_strategy_report` (the project's single LLM client, Module #4), and `save_macro_report`. Progress events `10/40/60/80/100` or `-1` on error. | `macro.py:71-129` |

> **Note**: every macro handler opens `research_insights.db` directly with `sqlite3` (`macro.py:25,41,58`) — `direct_sqlite_import_in_interface` violation. They do NOT use the error-leak `except Exception` pattern (they let FastAPI's default 500 handling apply on uncaught errors, which is a different but related observability gap).

### 3.6 analysis router (`src/api/routers/analysis.py`)

| Route | Behavior | file:line |
|---|---|---|
| `GET /api/analysis/reports` | Lists `research_reports` (id/date/timestamp/tags/analyst/title). DB absent → `{"reports": []}`. | `analysis.py:13-25` |
| `GET /api/analysis/reports/{report_id}` | Single report by id. Absent → `404 "not found"`. | `analysis.py:28-40` |

Both handlers open `research_insights.db` directly (`analysis.py:19,32`) — `direct_sqlite_import_in_interface` violation.

### 3.7 config router (`src/api/routers/config.py`)

Helpers `_read_json`/`_write_json` (`config.py:16-25`) read/write JSON files under `_PROJECT_ROOT`.

| Route | Behavior | file:line |
|---|---|---|
| `GET /api/config` | Reads `models_config.json`; absent → `{}`. | `config.py:28-32` |
| `GET /api/config/settings` | Reads `user_settings.json`; absent → `{}`. | `config.py:35-39` |
| `PUT /api/config/settings` | Body `SettingsUpdate{tdx_path?}`; merges into `user_settings.json` and writes. Returns `{ok, settings}`. | `config.py:46-54` |
| `POST /api/config/validate-tdx` | Body `SettingsUpdate`; `tdx_path` falsy → `400 "tdx_path required"`. Returns `{valid: true, vipdoc_path}` if `<path>/vipdoc` exists or `<path>` itself is named `vipdoc`, else `{valid: false, message}`. | `config.py:57-68` |

## 4. Contracts / Data Model

### 4.1 Full route table (the canonical enumeration)

| # | Method | Full path | Router | Purpose | file:line |
|---|---|---|---|---|---|
| 1 | GET | `/api/health` | (main) | Liveness probe → `{"status":"ok"}` | `main.py:38-40` |
| 2 | GET | `/api/stats` | (main) | Per-DB per-table row counts | `main.py:43-62` |
| 3 | GET | `/api/scan/servers` | scan | CN/US TDX server list | `scan.py:44-51` |
| 4 | POST | `/api/scan/servers/test` | scan | Probe server latencies | `scan.py:58-108` |
| 5 | GET | `/api/scan/status` | scan | In-memory scan status | `scan.py:121-123` |
| 6 | POST | `/api/scan/{market}` | scan | Start scan (SSE) | `scan.py:126-237` |
| 7 | GET | `/api/data/{market}/tables` | data | List tables in market DB | `data.py:22-34` |
| 8 | GET | `/api/data/{market}/table/{table_name}` | data | Paginated table query | `data.py:37-100` |
| 9 | GET | `/api/data/{market}/ticker/{ticker}/kline` | data | OHLCV + MA kline (DuckDB) | `data.py:103-142` |
| 10 | GET | `/api/data/{market}/ticker-names` | data | Ticker→name map | `data.py:190-197` |
| 11 | GET | `/api/notes/ticker/{ticker}` | notes | Price+name+notes context | `notes.py:21-32` |
| 12 | POST | `/api/notes` | notes | Add a note | `notes.py:35-49` |
| 13 | GET | `/api/notes/search` | notes | Keyword search | `notes.py:52-59` |
| 14 | GET | `/api/notes/recent` | notes | Recent notes | `notes.py:62-68` |
| 15 | GET | `/api/notes/tracked` | notes | Tracked tickers | `notes.py:71-77` |
| 16 | DELETE | `/api/notes/{note_id}` | notes | Soft-delete a note | `notes.py:80-92` |
| 17 | GET | `/api/macro/reports` | macro | List macro reports | `macro.py:22-35` |
| 18 | GET | `/api/macro/reports/latest` | macro | Latest macro report | `macro.py:38-53` |
| 19 | GET | `/api/macro/reports/{report_id}` | macro | Single macro report | `macro.py:56-68` |
| 20 | POST | `/api/macro/run` | macro | Run macro analysis (SSE) | `macro.py:71-129` |
| 21 | GET | `/api/analysis/reports` | analysis | List research reports | `analysis.py:13-25` |
| 22 | GET | `/api/analysis/reports/{report_id}` | analysis | Single research report | `analysis.py:28-40` |
| 23 | GET | `/api/config` | config | Read `models_config.json` | `config.py:28-32` |
| 24 | GET | `/api/config/settings` | config | Read `user_settings.json` | `config.py:35-39` |
| 25 | PUT | `/api/config/settings` | config | Update `user_settings.json` | `config.py:46-54` |
| 26 | POST | `/api/config/validate-tdx` | config | Validate TDX vipdoc path | `config.py:57-68` |

> The OpenAPI surface also exposes `/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc` (FastAPI defaults) — not enumerated as product endpoints.

### 4.2 Request/response schemas (current, Pydantic v2)

```python
# scan.py
class ServerTestRequest(BaseModel): market: str
class ScanRequest(BaseModel):
    tdx_path: str = ""
    use_server: bool = True
    server: Optional[str] = None

# notes.py
class NoteCreate(BaseModel):
    ticker: str
    content: str
    market: str = "cn"
    note_type: str = "comment"
    title: Optional[str] = None
    tags: Optional[str] = None

# macro.py
class MacroRunRequest(BaseModel):
    profile_name: Optional[str] = None

# config.py
class SettingsUpdate(BaseModel):
    tdx_path: Optional[str] = None
```

Query-param constraints enforced by `fastapi.Query`:
- `data` table query: `page: int = Query(1, ge=1)`, `page_size: int = Query(50, ge=1, le=500)`, `sort_order: str = Query("asc", pattern="^(asc|desc)$")` (`data.py:41-45`).
- `data` kline: `days: int = Query(120, ge=1, le=365)` (`data.py:104`).
- `notes` search: `q: str = Query(..., min_length=1)` (`notes.py:53`).

### 4.3 Response shapes (success)

| Endpoint | Shape |
|---|---|
| `/api/health` | `{"status": "ok"}` |
| `/api/stats` | `{<db_name>: {<table>: <count>}}` |
| `/api/scan/servers` | `{"cn": [{host, port, latency_ms}, ...], "us": [...]}` |
| `/api/scan/servers/test` | `{"results": [{host, ok, latency_ms, error?}]}` |
| `/api/scan/status` | `{"cn": "idle"|"running", "us": ...}` |
| `/api/scan/{market}` | SSE stream, event `progress`, data `{"progress": int, "message": str}` |
| `/api/data/{market}/tables` | `{"tables": [str]}` |
| `/api/data/{market}/table/{t}` | `{columns: [str], rows: [dict], total: int, page: int, page_size: int}` |
| `/api/data/{market}/ticker/{t}/kline` | `{"data": [{date, open, high, low, close, volume, ...}]}` |
| `/api/data/{market}/ticker-names` | `{"names": {<ticker>: <name>}, "count": int}` |
| `/api/notes/ticker/{t}` | `{ticker, market, name_cn?, name_en?, sector?, industry?, price_data?, notes: [...], note_count_total}` |
| `POST /api/notes` | `{"id": int}` |
| `/api/notes/search` | `{"results": [{ticker, created_at, note_type, title, content}]}` |
| `/api/notes/recent` | `{"results": [{ticker, market, created_at, ...}]}` |
| `/api/notes/tracked` | `{"tickers": [{ticker, market, n, last_note}]}` |
| `DELETE /api/notes/{id}` | `{"ok": true}` |
| `/api/macro/reports` | `{"reports": [{id, date, timestamp, tags, analyst, risk_signal, volatility}]}` |
| `/api/macro/reports/latest` | full `macro_reports` row (dict) |
| `/api/macro/reports/{id}` | full `macro_reports` row (dict) |
| `POST /api/macro/run` | SSE stream, event `progress`, data `{"progress": int, "message": str}` |
| `/api/analysis/reports` | `{"reports": [{id, date, timestamp, tags, analyst, title}]}` |
| `/api/analysis/reports/{id}` | full `research_reports` row (dict) |
| `/api/config` | `models_config.json` contents (dict) |
| `/api/config/settings` | `user_settings.json` contents (dict) |
| `PUT /api/config/settings` | `{"ok": true, "settings": <merged dict>}` |
| `POST /api/config/validate-tdx` | `{valid: bool, vipdoc_path?}` or `{valid: false, message: str}` |

### 4.4 Error contract (Current State vs Target)

| Situation | Current behavior | Status code |
|---|---|---|
| Invalid `market` path/query param | `raise HTTPException(400, "...")` explicit | 400 |
| Missing/invalid Pydantic body or query param | FastAPI `RequestValidationError` default | 422 |
| Resource not found (table/report/note) | `raise HTTPException(404, "...")` explicit | 404 |
| Concurrent scan on same market | `raise HTTPException(409, "{market} scan already running")` | 409 |
| `validate-tdx` with no `tdx_path` | `raise HTTPException(400, "tdx_path required")` | 400 |
| **Internal handler exception** (data kline, most notes handlers) | `except Exception as e: raise HTTPException(500, str(e))` — **leaks the internal message/stack** | 500 |
| Uncaught exception (macro/analysis read handlers) | FastAPI default 500 with generic message | 500 |

**Target (Migration)** — see ADR-0007 + Section 8 AC: every error response must return a **stable, non-leaking envelope** (e.g. `{"error": {"code": str, "message": str}}`) where `message` is operator-safe and never includes `str(e)` of an internal exception, stack trace, DB path, or SQL. The current `500`-with-`str(e)` is tracked tech debt, not a contract to rely on.

### 4.5 Concurrency model (Current State)

- **Scan serialization**: `_scan_locks = {cn: Lock, us: Lock}` (`scan.py:20`) — at most one scan per market per process. Acquired non-blocking; a second concurrent scan gets `409`. The lock is released in the worker thread's `finally` (`scan.py:224-226`).
- **SSE worker threads**: scan (`scan.py:228`) and macro-run (`macro.py:120`) spawn a `threading.Thread(daemon=True)` and bridge progress to the async event loop via `asyncio.run_coroutine_threadsafe(queue.put(...), loop)` (`scan.py:140-146`, `macro.py:80-86`).
- **SQLite reads**: every read opens a fresh `sqlite3.connect(...)` and closes it in the same handler — no connection pooling, no WAL, no `busy_timeout` (inherited from Module #2 §9.3). Concurrent reads are safe (SQLite allows concurrent readers); concurrent writer+reader can hit `database is locked`.

### 4.6 Registry proposals (BLOCKING Phase 5 — enumerated, not written)

- **`architecture.yaml` candidates (stances/contracts):**
  - `api.fastapi.title` = `"MY-DOGE API"`, version `0.1.0`.
  - `api.fastapi.bind_host` = `127.0.0.1`, `api.fastapi.bind_port` = `8901` (local-first).
  - `api.cors.allow_origins` = `["*"]` with local-first rationale (ADR-0007) — **with a hardening note to tighten to explicit localhost origins**.
  - `api.error.envelope` (Target) — the stable non-leaking error shape (not yet implemented).
  - `api.scan.concurrency` — one in-flight scan per market (`_scan_locks`).
- **`entities.yaml` candidates (concrete values):**
  - `api.route_table` — the product routes enumerated in §4.1 (currently 26) (method+path+router+file:line).
  - `api.router_prefix` = `{scan:/api/scan, data:/api/data, notes:/api/notes, macro:/api/macro, analysis:/api/analysis, config:/api/config}`.
  - `api.data.page.default` = 1; `api.data.page_size.default` = 50, `.max` = 500; `api.data.days.default` = 120, `.max` = 365.
  - `api.notes.search.min_length` = 1; `api.notes.recent.days.default` = 7, `.limit.default` = 100.
  - `api.scan.server.cn_port` = 7709; `api.scan.server.us_port` = 7727 (mirrors Module #1 `TDXConfig`).

## 5. Edge Cases

| Situation | What happens (Current State) |
|---|---|
| **Invalid `market` path/query** (`xx`, `foo`) | `400` from explicit `HTTPException` in scan/data/notes handlers. Deterministic. (Covered by `tests/test_api_routers.py`.) |
| **`market=research` in the data router** | **Per-endpoint nuance**: `GET /api/data/{market}/tables` and `GET /api/data/{market}/table/{t}` accept `market in {cn, us, research}` (validated against `_DB_MAP`, `data.py:13-17`), so `GET /api/data/research/tables` is VALID and returns the research DB's tables. The kline and ticker-names endpoints accept only `market in {cn, us}` (`data.py:106-107`, `data.py:193-194`), so `GET /api/data/research/ticker/.../kline` and `GET /api/data/research/ticker-names` correctly return `400`. A reader of the row above must NOT infer that `research` is invalid for all four data routes. |
| **Missing required body** (POST/PUT with no JSON) | FastAPI `422` (Pydantic validation). Deterministic. |
| **Query param out of range** (`page=0`, `page_size=999`, `days=99999`) | FastAPI `422` from `Query(ge=, le=)` constraints. Deterministic. |
| **`/api/notes/search` with empty `q`** | `422` from `Query(..., min_length=1)`. |
| **`GET /api/data/{market}/tables` with DB absent** | `200 {"tables": []}` — graceful empty, not an error. |
| **`GET /api/data/{market}/table/{t}` with DB absent** | `404 "database not found"`. |
| **`GET /api/data/{market}/table/{t}` with table absent** | `404 "table '{t}' not found"`. Table name is validated against `sqlite_master` (parameterized) before any SQL interpolation — no SQL injection via table name. |
| **`DELETE /api/notes/{id}` on a non-existent id** | `404 "note not found"` (Bug A contract). |
| **Double `DELETE` on the same note** | First → `200`, second → `404` (soft-deleted row is no longer "active"). |
| **`DELETE` then re-read** (search/recent/tracked/context) | The soft-deleted note is hidden from all read paths (`deleted_at IS NULL` filter). |
| **`GET /api/macro/reports/latest` with DB absent or empty** | `404 "no reports"`. |
| **`GET /api/macro/reports/{id}` / `GET /api/analysis/reports/{id}` absent** | `404 "not found"`. |
| **`GET /api/config` / `/api/config/settings` with file absent** | `200 {}` (graceful empty). |
| **`POST /api/config/validate-tdx` with no `tdx_path`** | `400 "tdx_path required"`. |
| **`POST /api/config/validate-tdx` with a path lacking `vipdoc`** | `200 {"valid": false, "message": "vipdoc directory not found"}` (not an error). |
| **Concurrent `POST /api/scan/{market}` for the same market** | Second request → `409 "{market} scan already running"`. |
| **`POST /api/scan/{market}` / `POST /api/macro/run` upstream failure (TDX/yfinance/LLM)** | The worker pushes `{"progress": -1, "message": "error: ..."}` onto the SSE stream and closes; HTTP status stays `200` (SSE already started). The error message is leaked into the SSE payload (same anti-pattern family). |
| **Internal exception in `data` kline or `notes` read handlers** | `500` with `str(e)` in the `detail` field — **leaks internal message** (anti-pattern, Section 8 remediation). Tests assert ONLY the status code for these paths. |
| **`/api/data/{market}/ticker-names` first call for `cn` with no cache** | Synchronously calls `akshare.stock_info_a_code_name()` (network) inside the request thread — blocks the request until akshare returns; failure is swallowed and an empty map returned. (Network-dependent behavior; not covered by isolated tests.) |
| **CORS preflight (`OPTIONS`) from a browser** | `CORSMiddleware` answers with `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]` — permissive by design (local-first, see ADR-0007). |

## 6. Dependencies

**Upstream (this module depends on):**
- **#1 `runtime-configuration`** — `Settings().db.*` is the *intended* source of all DB paths and `MCPConfig`/host settings. **Current State**: every router recomputes its own `_PROJECT_ROOT` and does NOT consult `get_settings()` (ADR-0001/ADR-0002 drift). The TDX server ports (`7709`/`7727`) hard-coded in `scan.py:50` duplicate `TDXConfig.cn_port/us_port`.
- **#2 `market-data-storage`** — every read handler opens `market_data_cn.db` / `market_data_us.db` / `research_insights.db` directly with `sqlite3` (or DuckDB via `connect_duckdb` for kline). The scan router imports `init_db_custom` (`scan.py:150`) and delegates writes to `MarketScanner` (Module #3/#5). Target: route through `IStockRepository` / `IReportRepository` ports (ADR-0001/ADR-0003).
- **#4 `macro-strategy-engine`** — `POST /api/macro/run` constructs `GlobalMacroLoader` and `DeepSeekStrategist` (the project's single LLM client, `macro.py:90-91`) and calls `save_macro_report` (`macro.py:92,106`). The macro read handlers read the `macro_reports` table Module #4 writes.
- **#5 `micro-momentum-scanner`** — `POST /api/scan/{market}` delegates to `MarketScanner.scan_{cn,us}_market` (`scan.py:246-251`) and `tdx_downloader` (`scan.py:157-159`), both owned by the micro/data-source modules.

**Downstream (depend on this module):**
- **#11 `vue-web-console`** — the primary consumer; the web UI calls every read endpoint and triggers scans/macro runs.
- **#10 `pyqt-desktop-dashboard`** — the desktop may also call this API (or call the same services directly; the dependency is documented in the module index).

**Bidirectional notes (per design-docs rule):**
- The `runtime-configuration` CDD (#1 §6.2) lists `fastapi-service` as an intended consumer of `get_settings()` and §3.11 enumerates every `src/api/routers/*.py` as a `_PROJECT_ROOT_recalculation` offender.
- The `market-data-storage` CDD (#2 §6) lists this module as a dependent that imports `init_db_custom` directly.
- The `macro-strategy-engine` CDD (#4 §6) lists this module's macro router as a downstream consumer.

**External packages:**
- `fastapi` 0.123.8, `uvicorn` 0.38.0, `pydantic` 2.12.4, `sse-starlette` 3.0.3, `httpx` 0.28.1 (TestClient).
- `sqlite3` (stdlib), `duckdb` (transitively via `connect_duckdb`), `akshare` (optional, cn ticker-name fallback).

**Docs / ADRs:**
- [ADR-0007](../../docs/architecture/adr-0007-api-surface-and-cors.md) — **this module's** decision: API surface enumeration + `allow_origins=["*"]` local-first CORS + the error-leak remediation stance.
- [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md) — forbidden patterns this module violates (`_PROJECT_ROOT_recalculation`, `direct_sqlite_import_in_interface`, `direct_duckdb_connect_in_interface` via `connect_duckdb`, the `init_db_custom` direct import).
- [ADR-0002](../../docs/architecture/adr-0002-centralized-configuration.md) — config-centralization decision this module does not yet honor.

## 7. Configuration Knobs

| Knob | Default | Valid range / type | Owner (Current) | Env ownership | Operational risk |
|---|---|---|---|---|---|
| `bind_host` | `127.0.0.1` | IP/hostname | **hardcoded** in `main.py:67` | (not env) | **HIGH** — changing to `0.0.0.0` exposes the API to the LAN; security implication. Local-first by design. |
| `bind_port` | `8901` | TCP port 1-65535 | **hardcoded** in `main.py:67` | (not env) | LOW unless port collides (note: MCP SSE is 8902, Module #1). |
| `cors.allow_origins` | `["*"]` | list of origin strings | **hardcoded** in `main.py:24` | (not env) | **MEDIUM** — permissive; safe only because `bind_host=127.0.0.1`. Hardening target: explicit localhost origins (ADR-0007). |
| `cors.allow_methods` | `["*"]` | list | `main.py:25` | (not env) | LOW. |
| `cors.allow_headers` | `["*"]` | list | `main.py:26` | (not env) | LOW. |
| `data.page.default` | `1` | int >= 1 | `data.py:41` | (not env) | LOW. |
| `data.page_size.default` / `.max` | `50` / `500` | int 1-500 | `data.py:42` | (not env) | LOW — bounds response size / memory. |
| `data.days.default` / `.max` | `120` / `365` | int 1-365 | `data.py:104` | (not env) | LOW — bounds kline payload. |
| `scan.server.cn_port` / `us_port` | `7709` / `7727` | TCP port | `scan.py:50` (hardcoded) | (not env) | **MEDIUM** — duplicates `TDXConfig.cn_port/us_port` (Module #1); drift risk. |
| `scan.servers.test.timeout` | `15s` (pool) / `5s` (per-server) | seconds | `scan.py:75,95` | (not env) | LOW. |
| `notes.search.min_length` | `1` | int | `notes.py:53` | (not env) | LOW. |
| `notes.recent.days.default` / `.limit.default` | `7` / `100` | int | `notes.py:63` | (not env) | LOW. |

**Migration target (vs Current State):**
- *Current State*: every knob is hardcoded in the router/`main.py`; `_PROJECT_ROOT` is recomputed per file; CORS is `*`.
- *Target (Migration)*: `bind_host`/`bind_port`/CORS sourced from `Settings()` (an `APIConfig` extension); DB paths via `Settings().db.*`; TDX ports via `Settings().tdx.*`; CORS tightened to explicit localhost origins (hardening story). No `_PROJECT_ROOT` recalculation anywhere under `src/api/`.

## 8. Acceptance Criteria

**Contract / route coverage (BUG E — RESOLVED):**
- [x] `tests/test_api_routers.py` exists and covers every endpoint in §4.1 with a success case, a validation-failure (4xx) case, and at least one edge case (no-auth local-first API, so the auth-failure case is intentionally skipped per api-code.md). Verified — `python -m pytest tests/test_api_routers.py -q` → **57 passed**.
- [x] The notes DELETE endpoint is covered: `200 {"ok": true}` on delete, `404` when not found, `404` on double-delete, soft-delete hidden from search/recent/tracked (Bug A contract).
- [x] Internal-error paths assert ONLY the status code (not the leaked `str(e)` message), because the leak pattern is under remediation (see below).
- [x] `python -m pytest tests/ -q` → full suite green (**204 passed** — 147 prior baseline + 57 new) with no live network and no live-DB reads (every router is isolated via temp dirs / monkeypatched `NOTES_DB` / mocked `connect_duckdb`). **Baseline traceability**: the `147 prior` is the suite count on this branch immediately before `tests/test_api_routers.py` was added (i.e. `pytest tests/` with `tests/test_api_routers.py` deselected); re-audit by `git stash`/`git checkout` of that file, or by `pytest tests/ -q --ignore=tests/test_api_routers.py` which yields 147 passed (verified 2026-06-12 on branch `cdd-adoption-2026-06-11`).

**Error-leak remediation (ADR-0007 stance — OPEN, tracked tech debt):**
- [ ] Error responses return a **stable, non-leaking envelope** (e.g. `{"error": {"code": str, "message": str}}`); `message` is operator-safe and never includes the raw `str(e)`, a stack trace, a DB path, or SQL. The current `except Exception as e: raise HTTPException(500, str(e))` pattern (`data.py:141-142`; `notes.py:31-32,48-49,58-59,67-68,76-77`) is **tracked tech debt**, not a contract. Until fixed, contract tests on these paths assert status code only.
- [ ] A single FastAPI exception handler (`@app.exception_handler(Exception)`) maps uncaught exceptions to the stable envelope with a logged (not returned) detail.

**ADR-0001 forbidden-pattern remediation (OPEN, owned jointly with #12):**
- [ ] `src/api/routers/scan.py:150` direct `from src.micro.database import init_db_custom` removed — scan initialization routed through `IStockRepository`/a scan service port.
- [ ] No `_PROJECT_ROOT` recalculation in `src/api/main.py:9` or any `src/api/routers/*.py` (`main.py:9`, `scan.py:17`, `data.py:11`, `macro.py:13`, `analysis.py:8`, `config.py:11`) — all paths via `get_settings()`.
- [ ] No `sqlite3.connect` in `src/api/**` (`main.py:46,52`, `data.py:29,53`, `macro.py:25,41,58`, `analysis.py:19,32`) — reads via `IStockRepository`/`IReportRepository`.
- [ ] No direct `connect_duckdb` import in `data.py:110` — DuckDB reads via `IStockRepository`.

**Contract / data model:**
- [ ] `/api/data/{market}/table/{t}` always validates `table_name` against `sqlite_master` before SQL interpolation (no SQL injection via table name) — regression test (OPEN).
- [ ] `/api/scan/{market}` returns `409` on a second concurrent scan for the same market and releases the lock on worker exit (OPEN — the 409 branch is covered; the lock-release-under-failure path is not yet an automated test).

**Docs / observability:**
- [ ] This CDD cites real `file:line` for every claim (auditable).
- [ ] ADR-0007 is `Accepted` (currently **Proposed** as of 2026-06-12; the CORS hardening story is the gating follow-on).
- [ ] Registry proposals in §4.6 queued for Phase 5 entry approval.

## 9. Integration Requirements

> Appended per the assignment brief for interface/integration modules. Also satisfies api-code.md ("document request/response/error/auth/compatibility behavior").

### 9.1 Transport / protocol

- **HTTP/1.1** over loopback (`127.0.0.1:8901`), served by `uvicorn`. No HTTPS termination in the service itself (local-first; a reverse proxy would own TLS if ever needed).
- **Two response modes**:
  1. **JSON** — every read/write endpoint except the two SSE streams. `Content-Type: application/json`.
  2. **Server-Sent Events** — `POST /api/scan/{market}` (`scan.py:237`) and `POST /api/macro/run` (`macro.py:129`) return `EventSourceResponse` with `Content-Type: text/event-stream`. Each event is `{event: "progress", data: <json string of {"progress": int, "message": str}>}`. The stream terminates when `progress in {100, -1}`.
- **Auth**: none. This is a local-first API with no remote clients in scope. api-code.md's "auth failure" test case is therefore N/A and intentionally skipped (documented in §8). If the service is ever bound to a non-loopback interface, auth MUST be added first (see §7 `bind_host` risk).

### 9.2 Request/response schemas

- See §4.2 (Pydantic body models) and §4.3 (response shapes). All bodies are `application/json`. Path and query params are validated by FastAPI/Pydantic at the boundary (api-code.md "validate all external input at the boundary" — satisfied for the parameters FastAPI manages; the `data` table query interpolates the validated `table_name`/`sort_by` into SQL but only after a `sqlite_master` allow-list check).

### 9.3 Error contracts

- **Stable status codes** (Current State): `200` success; `400` explicit bad-request (invalid market, missing tdx_path); `404` resource absent; `409` concurrent-scan conflict; `422` Pydantic/FastAPI validation failure; `500` internal error.
- **Error body (Current State)**: FastAPI's default `{"detail": "..."}`. For the explicit `HTTPException` paths the `detail` is a fixed operator-safe string. For the **error-leak** paths (`data` kline, most `notes` handlers) the `detail` is `str(e)` — the raw internal exception message. **Target (ADR-0007)**: a single stable envelope `{"error": {"code": str, "message": str}}` with no internal detail; the raw detail is logged server-side, never returned.
- **Retry semantics**: the API itself performs **no retry**. The scan/macro SSE workers do not retry upstream (TDX/yfinance/LLM) failures — they surface `progress=-1` and close. The macro data-fetch retry (`max_retries=3`, Module #4) happens inside the worker thread before any LLM call. Clients that need retries must implement them at the HTTP layer.

### 9.4 CORS

- **Current State**: `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]` (`main.py:22-27`). Permissive.
- **Justification (local-first)**: the server binds to `127.0.0.1` (`main.py:67`); no remote client can reach it in the default deployment. The Vue web console (Module #11) is served from the same origin or from a dev server on `localhost`, so `*` is operationally equivalent to `http://localhost:*` in practice. See ADR-0007 for the full rationale.
- **Hardening target (ADR-0007)**: replace `["*"]` with an explicit allow-list of localhost origins (e.g. `http://localhost:5173`, `http://127.0.0.1:5173`, the Tauri/desktop origin). This is a tracked hardening story, not current behavior.

### 9.5 Concurrency model

- **Async handlers, sync work off-loaded**: handlers are `async def`, but blocking work (SQLite reads, TDX probes, scan/macro runs) is either awaited directly (SQLite is sync and blocks the event loop — a known latency risk) or pushed to a `threading.Thread` (scan/macro SSE workers). There is **no thread pool** for the SQLite read handlers — a slow query blocks the event loop. Target: off-load SQLite reads via `run_in_threadpool`.
- **Per-market scan lock**: `_scan_locks` serializes scans (§4.5). The lock lives in module-global state — it does NOT survive a process restart and does NOT coordinate across multiple worker processes (uvicorn `--workers > 1` would break the single-scan-per-market guarantee). Documented single-process deployment assumption.

### 9.6 Timeouts

- **HTTP request timeout**: none configured at the service level — uvicorn's defaults apply. Long-running scans/macro runs are SSE-streamed precisely so they are not bounded by a single request timeout; the client should treat the SSE connection as long-lived.
- **Upstream timeouts inside workers**: TDX per-server connect `5s`, server-test pool `15s` (`scan.py:75,95`); yfinance retry `max_retries=3` × `5s` (Module #4); LLM call has **no explicit timeout** (Module #4 §9.3 — the OpenAI SDK default applies).
- **MCP budget**: this is the HTTP API, not the MCP server; `MCPConfig.tool_timeout=30s` (Module #1) does NOT apply here.

---

## Open Questions (aspirational — flagged for Phase 5 reconciliation)

1. **Error envelope** — adopt `{"error": {"code", "message"}}` via a single `@app.exception_handler(Exception)`; map the existing `HTTPException(500, str(e))` sites to logged-detail + stable message. (Blocking AC in §8; ADR-0007.)
2. **Repository routing** — every read handler opens SQLite/DuckDB directly (ADR-0001 violations). Route through `IStockRepository`/`IReportRepository` (depends on Module #2/#12). Which repository methods does the API need that the ports don't yet expose (e.g. `list_tables`, `query_table` paginated)?
3. **`_PROJECT_ROOT` per router** — collapse to `get_settings()` (ADR-0002). Straightforward but touches all six routers + `main.py`.
4. **CORS hardening** — replace `["*"]` with an explicit localhost allow-list (ADR-0007 hardening story). What are the exact origins the Vue dev server and the Tauri/desktop shell use?
5. **`bind_host`/`bind_port` as settings** — promote from hardcoded `main.py:67` to an `APIConfig` on `Settings()` so a non-default port can be set without code change.
6. **TDX port drift** — `scan.py:50` hardcodes `7709`/`7727`, duplicating `TDXConfig.cn_port`/`us_port` (Module #1). Which wins?
7. **SQLite read blocking the event loop** — should read handlers use `run_in_threadpool`? Today a slow `query_table` blocks the whole event loop, including SSE heartbeats for in-flight scans.
8. **`akshare` network call in `ticker-names`** — the cn fallback synchronously hits the network inside the request thread with no timeout; should it be backgrounded/cached-only?
9. **SSE error payload leak** — the scan/macro workers push `"error: {e}"` into the SSE `message` (same anti-pattern family as the HTTP error leak). Should the SSE error event use a stable code too?
10. **Multi-worker deployment** — `_scan_locks`/`_scan_status` are module-global; uvicorn `--workers > 1` breaks the single-scan guarantee. Document and enforce single-worker, or move the lock to shared storage.
