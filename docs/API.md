# HTTP API Reference (FastAPI)

The local-first HTTP backend of MY-DOGE-MICRO. A single FastAPI application
(`doge.interfaces.api.main`) binds to `127.0.0.1:8901` and exposes **87 product routes**:
34 legacy `/api/*` routes plus 53 daemon/v1 routes (`sessions`, `runs`,
`documents`, `tools`, `health`, case workflow, portfolio import, audit, and enterprise ACL).
It is the surface the
Vue web console (`web/`) and optionally the PyQt desktop dashboard call to
trigger market scans, browse persisted data, manage stock notes, read macro and
research reports, run the Research Copilot demo workflow, and configure the TDX
install.

> **Stack**: FastAPI 0.123.8, Uvicorn 0.38.0, Pydantic 2.12.4, sse-starlette
> 3.0.3, httpx 0.28.1 (TestClient) — pinned in `pyproject.toml:11-25`. Reverse-documented
> in `design/cdd/fastapi-service.md`; API-surface decision in
> [ADR-0007](architecture/adr-0007-api-surface-and-cors.md).

## Table of Contents

- [Overview](#overview)
- [Base URL & Transports](#base-url--transports)
- [Authentication](#authentication)
- [Route Table](#route-table)
- [Per-Endpoint Reference](#per-endpoint-reference)
  - [scan router](#scan-router)
  - [data router](#data-router)
  - [notes router](#notes-router)
  - [macro router](#macro-router)
  - [analysis router](#analysis-router)
  - [config router](#config-router)
  - [agent router](#agent-router)
  - [documents router](#documents-router)
- [SSE Contract](#sse-contract)
- [CORS](#cors)
- [Error Contract](#error-contract)
- [Concurrency](#concurrency)
- [OpenAPI](#openapi)

## Overview

| Property | Value | Source |
|---|---|---|
| Application | `FastAPI(title="MY-DOGE API", version="0.1.0")` | `src/doge/interfaces/api/main.py` |
| Bind host | `127.0.0.1` (loopback only) | `src/doge/interfaces/api/main.py` |
| Bind port | `8901` | `src/doge/interfaces/api/main.py` |
| Auth | None (local-first) | see [Authentication](#authentication) |
| Routers | legacy `/api/*` routers + v1 daemon routers | `src/doge/interfaces/api/main.py` |
| Product routes | 76 (34 legacy routes + 42 v1/health routes) | `src/doge/interfaces/api/main.py` |
| Framework | FastAPI 0.123.8 + uvicorn 0.38.0 | `pyproject.toml:19-20` |
| Streaming | sse-starlette 3.0.3 (`EventSourceResponse`) | `pyproject.toml:21` |

The canonical server is started directly:

```bash
python -m uvicorn doge.interfaces.api.main:app --host 127.0.0.1 --port 8901
```

`src/api` remains only as a deprecated compatibility redirect shim. New
integrations should import or launch `doge.interfaces.api`.

Two BLAS/OpenMP thread-count shims are set at import via
`os.environ.setdefault` (`src/doge/interfaces/api/main.py`) — `OPENBLAS_NUM_THREADS=1`
and `OMP_NUM_THREADS=1` — shared with the DuckDB/ai_analysis layers.

## Base URL & Transports

**Base URL**: `http://127.0.0.1:8901` — all product routes live under the
`/api` prefix.

Two response modes are used (`design/cdd/fastapi-service.md` §9.1):

1. **JSON** (default) — every read/write endpoint except the two SSE streams.
   `Content-Type: application/json`. Request and response bodies are JSON.
2. **Server-Sent Events (SSE)** — three endpoints return an
   `EventSourceResponse` with `Content-Type: text/event-stream`:
  - `POST /api/scan/{market}` (`src/doge/interfaces/api/routers/scan.py`)
   - `POST /api/macro/run` (`src/doge/interfaces/api/routers/macro.py`)
   - `GET /api/agent/runs/{run_id}/stream` (`src/doge/interfaces/api/routers/agent.py`)

   See [SSE Contract](#sse-contract) for the event format.

HTTP/1.1 over loopback, served by uvicorn. No HTTPS termination in the service
itself (local-first; a reverse proxy would own TLS if ever needed).

## Authentication

**None.** This is a local-first API with no remote clients in scope. Safety
rests entirely on the loopback bind:

- The server binds to `127.0.0.1` (`src/doge/interfaces/api/main.py`), so no remote client
  can reach it in the default configuration.
- `.claude/rules/api-code.md`'s "auth failure" contract-test case is therefore
  N/A and intentionally skipped (documented in `tests/test_api_routers.py:5-8`).

> **WARNING — rebinding is a security event.** If you change the bind host to
> `0.0.0.0` (or any non-loopback interface) the API becomes reachable from the
> LAN **with no authentication and with permissive CORS**
> (`allow_origins=["*"]`, `src/doge/interfaces/api/main.py`). Binding off-loopback REQUIRES
> both (a) tightening CORS to an explicit origin allow-list and (b) adding an
> auth layer — see [CORS](#cors) and ADR-0007 §Decision 2 + Migration Plan
> step 3. Neither exists today.

## Route Table

The canonical enumeration (also `design/cdd/fastapi-service.md` §4.1). The
docs-consistency gate test `tests/contract/test_api_doc_route_coverage.py`
asserts this table matches `app.routes` on the live FastAPI app, so the doc and
code cannot drift.

### Top-level helpers (registered on `app` directly)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 1 | GET | `/api/health` | Liveness probe → `{"status":"ok"}` | `src/doge/interfaces/api/main.py` |
| 2 | GET | `/api/stats` | Per-DB per-table row counts | `src/doge/interfaces/api/main.py` |

### scan router — prefix `/api/scan` (`src/doge/interfaces/api/routers/scan.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 3 | GET | `/api/scan/servers` | CN/US TDX server list | `scan.py:70-77` |
| 4 | POST | `/api/scan/servers/test` | Probe server latencies | `scan.py:84-134` |
| 5 | GET | `/api/scan/status` | In-memory scan status | `scan.py:147-149` |
| 6 | POST | `/api/scan/{market}` | Start scan (SSE) | `scan.py:152-268` |

### data router — prefix `/api/data` (`src/doge/interfaces/api/routers/data.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 7 | GET | `/api/data/{market}/tables` | List tables in market DB | `data.py:22-34` |
| 8 | GET | `/api/data/{market}/table/{table_name}` | Paginated table query | `data.py:37-100` |
| 9 | GET | `/api/data/{market}/ticker/{ticker}/kline` | OHLCV + MA kline (DuckDB) | `data.py:103-143` |
| 10 | GET | `/api/data/{market}/ticker-names` | Ticker→name map | `data.py:191-198` |

### notes router — prefix `/api/notes` (`src/doge/interfaces/api/routers/notes.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 11 | GET | `/api/notes/ticker/{ticker}` | Price+name+notes context | `notes.py:21-31` |
| 12 | POST | `/api/notes` | Add a note | `notes.py:34-45` |
| 13 | GET | `/api/notes/search` | Keyword search | `notes.py:48-52` |
| 14 | GET | `/api/notes/recent` | Recent notes | `notes.py:55-58` |
| 15 | GET | `/api/notes/tracked` | Tracked tickers | `notes.py:61-64` |
| 16 | DELETE | `/api/notes/{note_id}` | Soft-delete a note | `notes.py:67-79` |

### macro router — prefix `/api/macro` (`src/doge/interfaces/api/routers/macro.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 17 | GET | `/api/macro/reports` | List macro reports | `macro.py:22-35` |
| 18 | GET | `/api/macro/reports/latest` | Latest macro report | `macro.py:38-53` |
| 19 | GET | `/api/macro/reports/{report_id}` | Single macro report | `macro.py:56-68` |
| 20 | POST | `/api/macro/run` | Run macro analysis (SSE) | `macro.py:71-129` |

### analysis router — prefix `/api/analysis` (`src/doge/interfaces/api/routers/analysis.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 21 | GET | `/api/analysis/reports` | List research reports | `analysis.py:13-25` |
| 22 | GET | `/api/analysis/reports/{report_id}` | Single research report | `analysis.py:28-40` |

### config router — prefix `/api/config` (`src/doge/interfaces/api/routers/config.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 23 | GET | `/api/config` | Read `models_config.json` (api_key redacted) | `config.py:48-52` |
| 24 | GET | `/api/config/settings` | Read `user_settings.json` | `config.py:55-59` |
| 25 | PUT | `/api/config/settings` | Update `user_settings.json` | `config.py:66-74` |
| 26 | POST | `/api/config/validate-tdx` | Validate TDX vipdoc path | `config.py:77-88` |

### agent router — prefix `/api/agent` (`src/doge/interfaces/api/routers/agent.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 27 | POST | `/api/agent/runs` | Create and advance a Research Copilot run | `agent.py` |
| 28 | GET | `/api/agent/runs/{run_id}` | Read run status and metadata | `agent.py` |
| 29 | GET | `/api/agent/runs/{run_id}/events` | Read stored agent events | `agent.py` |
| 30 | GET | `/api/agent/runs/{run_id}/stream` | Stream run events as SSE | `agent.py` |
| 31 | GET | `/api/agent/runs/{run_id}/artifacts` | Read generated artifacts | `agent.py` |
| 32 | GET | `/api/agent/runs/{run_id}/approvals` | Read pending/resolved approvals | `agent.py` |
| 33 | POST | `/api/agent/runs/{run_id}/approvals/{approval_id}` | Approve or deny a high-risk action | `agent.py` |

### documents router — prefix `/api/documents` (`src/doge/interfaces/api/routers/documents.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 34 | POST | `/api/documents` | Register a demo document payload | `documents.py` |

### v1 daemon routes — prefix `/v1` plus health (`src/doge/interfaces/api/routers/v1/`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 35 | GET | `/health` | Daemon liveness probe | `v1/health.py` |
| 36 | GET | `/health/ready` | Daemon readiness probe | `v1/health.py` |
| 37 | POST | `/v1/sessions` | Create a persisted agent session | `v1/sessions.py` |
| 38 | GET | `/v1/sessions` | List recent sessions | `v1/sessions.py` |
| 39 | GET | `/v1/sessions/{session_id}` | Read a session and turns | `v1/sessions.py` |
| 40 | POST | `/v1/sessions/{session_id}/turns` | Enqueue a session turn; returns 202 + run id | `v1/sessions.py` |
| 41 | GET | `/v1/runs/{run_id}` | Read a persisted run | `v1/runs.py` |
| 42 | POST | `/v1/runs/{run_id}/cancel` | Request run cancellation | `v1/runs.py` |
| 43 | GET | `/v1/runs/{run_id}/events` | Read persisted events | `v1/runs.py` |
| 44 | GET | `/v1/runs/{run_id}/stream` | SSE stream with `Last-Event-ID` replay | `v1/runs.py` |
| 45 | GET | `/v1/runs/{run_id}/artifacts` | Read run artifacts | `v1/runs.py` |
| 46 | GET | `/v1/runs/{run_id}/approvals` | Read run approvals | `v1/runs.py` |
| 47 | POST | `/v1/runs/{run_id}/approvals/{approval_id}` | Resolve an approval and resume | `v1/runs.py` |
| 48 | GET | `/v1/runs/{run_id}/summary` | Read API-backed run summary snapshot (feature-flagged) | `v1/runs.py` |
| 49 | GET | `/v1/runs/{run_id}/claims` | Read run claims and support status (feature-flagged) | `v1/runs.py` |
| 50 | GET | `/v1/runs/{run_id}/citations` | Read run citations with local provenance and ACL redaction (feature-flagged) | `v1/runs.py` |
| 51 | GET | `/v1/runs/{run_id}/eval` | Read deterministic run eval metrics/checks (feature-flagged) | `v1/runs.py` |
| 52 | POST | `/v1/documents` | Upload a real document file or register a compatible text payload | `v1/documents.py` |
| 53 | GET | `/v1/documents` | List persisted documents | `v1/documents.py` |
| 54 | GET | `/v1/documents/{document_id}` | Read a persisted document | `v1/documents.py` |
| 55 | GET | `/v1/workspaces` | List platform workspaces (feature-flagged) | `v1/platform.py` |
| 56 | POST | `/v1/workspaces` | Create a platform workspace (feature-flagged) | `v1/platform.py` |
| 57 | GET | `/v1/workspaces/{workspace_id}` | Read a platform workspace (feature-flagged) | `v1/platform.py` |
| 58 | GET | `/v1/projects` | List platform projects (feature-flagged) | `v1/platform.py` |
| 59 | POST | `/v1/projects` | Create a platform project (feature-flagged) | `v1/platform.py` |
| 60 | GET | `/v1/projects/{project_id}` | Read a platform project (feature-flagged) | `v1/platform.py` |
| 61 | GET | `/v1/research-cases` | List research cases (feature-flagged) | `v1/platform.py` |
| 62 | POST | `/v1/research-cases` | Create a research case (feature-flagged) | `v1/platform.py` |
| 63 | GET | `/v1/research-cases/{case_id}` | Read a research case (feature-flagged) | `v1/platform.py` |
| 64 | POST | `/v1/research-cases/{case_id}/runs` | Idempotently link a run to a research case (feature-flagged) | `v1/platform.py` |
| 65 | GET | `/v1/home-queue` | Read actionable case/run/data work queue items (feature-flagged) | `v1/platform.py` |
| 66 | GET | `/v1/research-cases/{case_id}/assets` | List assets attached to a research case (feature-flagged) | `v1/platform.py` |
| 67 | POST | `/v1/research-cases/{case_id}/assets` | Attach a document, portfolio, or URL asset to a case (feature-flagged) | `v1/platform.py` |
| 68 | DELETE | `/v1/research-cases/{case_id}/assets/{asset_link_id}` | Remove a case asset link (feature-flagged) | `v1/platform.py` |
| 69 | GET | `/v1/research-cases/{case_id}/decisions` | List recorded case decisions (feature-flagged) | `v1/platform.py` |
| 70 | POST | `/v1/research-cases/{case_id}/decisions` | Record an approve/reject/hold/escalate case decision (feature-flagged) | `v1/platform.py` |
| 71 | POST | `/v1/research-cases/{case_id}/executions/preflight` | Validate template inputs, assets, and capabilities before execution (feature-flagged) | `v1/platform.py` |
| 72 | POST | `/v1/research-cases/{case_id}/executions` | Create a workflow execution, run it, and link it to the case (feature-flagged) | `v1/platform.py` |
| 73 | GET | `/v1/research-cases/{case_id}/executions` | List workflow executions for a case (feature-flagged) | `v1/platform.py` |
| 74 | GET | `/v1/research-cases/{case_id}/executions/{execution_id}` | Read a workflow execution by ID (feature-flagged) | `v1/platform.py` |
| 75 | GET | `/v1/research-cases/{case_id}/review` | Read case review state with latest run summary when enabled (feature-flagged) | `v1/platform.py` |
| 76 | GET | `/v1/workflow-templates` | List workflow templates (feature-flagged) | `v1/platform.py` |
| 77 | POST | `/v1/workflow-templates` | Create a workflow template definition (feature-flagged) | `v1/platform.py` |
| 78 | GET | `/v1/workflow-templates/{template_id}` | Read a workflow template by ID or slug (feature-flagged) | `v1/platform.py` |
| 79 | GET | `/v1/capabilities` | Read redacted provider, feature, maturity, and tool capability status (feature-flagged) | `v1/platform.py` |
| 80 | GET | `/v1/tools` | List function-tool schemas | `v1/tools.py` |
| 81 | POST | `/v1/portfolios/import` | Import a UTF-8 portfolio CSV and persist holdings | `v1/portfolios.py` |
| 82 | GET | `/v1/audit/events` | List tenant-scoped audit events | `v1/audit.py` |
| 83 | GET | `/v1/audit/events/export` | Export tenant audit events as redacted JSONL | `v1/audit.py` |
| 84 | POST | `/v1/audit/events/retention` | Purge expired tenant audit events by retention policy | `v1/audit.py` |
| 85 | GET | `/v1/enterprise/acl/grants` | List tenant ACL grants for enterprise admins | `v1/enterprise.py` |
| 86 | POST | `/v1/enterprise/acl/grants` | Create a tenant ACL grant | `v1/enterprise.py` |
| 87 | DELETE | `/v1/enterprise/acl/grants` | Revoke a tenant ACL grant | `v1/enterprise.py` |

> The OpenAPI surface also exposes `/openapi.json`, `/docs`,
> `/docs/oauth2-redirect`, `/redoc` (FastAPI defaults) — infrastructure, not
> product endpoints, so not counted in the 87 product routes above.

### Feature-Flagged Platform Surfaces

The backend platformization routes above are additive and default off:

- `DOGE_FEATURE_RUN_SUMMARY_API=1` enables `/v1/runs/{run_id}/summary`,
  `/claims`, `/citations`, and `/eval`.
- `DOGE_FEATURE_PLATFORM_OBJECTS=1` enables workspace, project, research-case,
  case-run link, case asset, workflow execution, decision, review, and home
  queue routes.
- `DOGE_FEATURE_WORKFLOW_TEMPLATES=1` enables workflow-template routes.
  `POST /v1/research-cases/{case_id}/runs` also accepts `template_id` under
  this flag to create and link a run from a workflow template.
- `DOGE_FEATURE_CAPABILITY_REGISTRY=1` enables `/v1/capabilities`, including
  provider-split feature/provider/maturity records and default tool capability
  metadata sourced from `ToolRegistry` without executing tools.
- The Web platform shell is default-on for local Web builds. `/` opens `/home`;
  `/research-agent` remains directly reachable. Set
  `VITE_DOGE_FEATURE_PLATFORM_SHELL=0` to roll the root route back to the
  legacy Research Agent entry.

Feature flag lifecycle metadata and defaultization/removal gates are recorded in
`docs/archive/audits/feature-flag-deprecation-plan-2026-06-23.md` and
`docs/archive/audits/platform-shell-defaultization-2026-06-24.md`.

Python SDK methods mirror these routes with `client.runs.summary()`,
`client.runs.claims()`, `client.runs.citations()`,
`client.runs.evaluation()`, `client.platform.*`, and
`client.platform.create_research_case_run_from_template()`. Case-centered
execution helpers include `home_queue()`, `preflight_case_execution()`,
`execute_case_template()`, `list_case_executions()`, `get_case_review()`,
case assets, and case decisions. `client.capabilities.get()/list()` exposes
capability discovery. The TypeScript SDK mirrors the same surface in camelCase
for platform helpers.

## Per-Endpoint Reference

All request bodies are `application/json`. Path and query params are validated
by FastAPI/Pydantic at the boundary. Every error response uses the stable
`{"error": {"code", "message"}}` envelope — see [Error Contract](#error-contract).

### Pydantic request models

```python
# scan.py:141-144
class ScanRequest(BaseModel):
    tdx_path: str = ""
    use_server: bool = True
    server: Optional[str] = None   # specific server IP; null = auto-select

# scan.py:80-81
class ServerTestRequest(BaseModel):
    market: str

# notes.py:12-18
class NoteCreate(BaseModel):
    ticker: str
    content: str
    market: str = "cn"
    note_type: str = "comment"
    title: Optional[str] = None
    tags: Optional[str] = None

# macro.py:18-19
class MacroRunRequest(BaseModel):
    profile_name: Optional[str] = None
    market: str = "cn"
    custom_prompt: Optional[str] = None

# config.py:62-63
class SettingsUpdate(BaseModel):
    tdx_path: Optional[str] = None
```

### scan router

#### `GET /api/scan/servers` — `scan.py:70-77`
Returns the CN/US TDX server lists with fixed ports (CN 7709, US 7727). The
canonical router reads them through the `ITDXServerList` port and
`ConfigTDXServerList` adapter, which source values from `Settings().tdx`. The
router no longer imports the legacy `src.micro.tdx_downloader` helper.

**200** body:
```json
{"cn": [{"host": "180.153.18.170", "port": 7709, "latency_ms": null}],
 "us": [{"host": "112.74.214.43", "port": 7727, "latency_ms": null}]}
```

#### `POST /api/scan/servers/test` — `scan.py:84-134`
Body: `ServerTestRequest`. Rejects `market not in {cn,us}` with **400**
(`scan.py:87-88`). Otherwise concurrently probes each server with
`opentdx.TdxClient` (per-server connect timeout 5s, pool timeout 15s) and
returns results in original server order.
**200** body: `{"results": [{"host", "ok", "latency_ms", "error"?}]}`.

#### `GET /api/scan/status` — `scan.py:147-149`
Returns the in-memory `_scan_status = {cn, us}` map.
**200** body: `{"cn": "idle"|"running", "us": "idle"|"running"}`.

#### `POST /api/scan/{market}` — `scan.py:152-268`
Body: `ScanRequest`. Starts a market scan and returns an SSE stream of
`{progress, message}` events (see [SSE Contract](#sse-contract)).

- `{market}` must be `cn` or `us`, else **400** `"market must be 'cn' or 'us'"`
  (`scan.py:154-155`).
- A second concurrent scan for the same market returns **409**
  `"{market} scan already running"` (`scan.py:157-158`) — see
  [Concurrency](#concurrency).
- The worker prefers a TDX server download through `ScanMarketUseCase` and the
  `TDXDataSource` adapter. If the server path is unavailable, it falls back to
  local `.day` files through the same use case, then best-effort refreshes the
  DuckDB views. Refresh failures are logged and surfaced through terminal SSE
  state rather than hidden behind router imports.
- Terminal events: `progress=100` (`"done"`) or `progress=-1`
  (`"error: {e}"`).

### data router

`market` is resolved against `_DB_MAP` (`data.py:13-17`): `{cn, us, research}`.
The kline and ticker-names endpoints accept only `{cn, us}`.

#### `GET /api/data/{market}/tables` — `data.py:22-34`
- `market not in _DB_MAP` → **400** (`data.py:24-25`).
- DB file absent → **200** `{"tables": []}` (graceful empty, not an error).
- Else **200** `{"tables": [<name>, ...]}` sorted by name.

#### `GET /api/data/{market}/table/{table_name}` — `data.py:37-100`
Paginated table query. Query params (`data.py:41-45`):
- `page: int = Query(1, ge=1)` — page number, ≥ 1.
- `page_size: int = Query(50, ge=1, le=500)` — rows per page, 1..500.
- `search: Optional[str] = None` — LIKE filter across first 5 columns.
- `sort_by: Optional[str] = None` — column to sort by (must be a real column).
- `sort_order: str = Query("asc", pattern="^(asc|desc)$")` — direction.

Errors: invalid market → **400**; DB absent → **404** `"database not found"`;
table absent → **404** `"table '{table_name}' not found"`. The `table_name` is
validated against `sqlite_master` before any SQL interpolation (no SQL
injection via table name — `data.py:57-61`).
**200** body: `{"columns", "rows", "total", "page", "page_size"}`.

#### `GET /api/data/{market}/ticker/{ticker}/kline` — `data.py:103-143`
OHLCV kline via DuckDB. Query param: `days: int = Query(120, ge=1, le=365)`
(`data.py:104`) — lookback window, 1..365 days.

`market not in {cn,us}` → **400**. CN reads the `vw_daily_enriched_cn` view
(with MA/ATR columns); US reads raw `us.stock_prices` (with `amount`). Any
internal exception surfaces through the global handler (see
[Error Contract](#error-contract)) — no `str(e)` leak.
**200** body: `{"data": [{date, open, high, low, close, volume, ...}]}` sorted
by date ascending.

#### `GET /api/data/{market}/ticker-names` — `data.py:191-198`
Ticker→name mapping. `market not in {cn,us}` → **400**. Reads a local
`<data>/<market>_ticker_names.json` cache (in-process
`_ticker_names_cache`, `data.py:147`); for `cn` with no cache it synchronously
calls `akshare.stock_info_a_code_name()` (network) and writes the cache; `us`
has no online fallback.
**200** body: `{"names": {<ticker>: <name>}, "count": int}`.

### notes router

All handlers import `stock_notes` lazily via the fully-qualified
`from src.ai_analysis.stock_notes import ...` path. Notes are soft-deleted
(`deleted_at` nullable; all read queries filter `deleted_at IS NULL`).

#### `GET /api/notes/ticker/{ticker}` — `notes.py:21-31`
Stock overview: price + name + notes for `{ticker}`. Converts the `price_data`
DataFrame to records. Any internal error surfaces through the global handler.
**200** body: `{ticker, market, name_cn?, name_en?, sector?, industry?,
price_data?, notes: [...], note_count_total}`.

#### `POST /api/notes` — `notes.py:34-45`
Body: `NoteCreate` (`ticker`, `content` required). Inserts a note.
**200** body: `{"id": int}`.

#### `GET /api/notes/search` — `notes.py:48-52`
Query param: `q: str = Query(..., min_length=1)` (`notes.py:49`) — missing or
empty `q` → **422**.
**200** body: `{"results": [{ticker, created_at, note_type, title, content}]}`.

#### `GET /api/notes/recent` — `notes.py:55-58`
Query params: `days: int = 7`, `limit: int = 100`.
**200** body: `{"results": [{ticker, market, created_at, ...}]}`.

#### `GET /api/notes/tracked` — `notes.py:61-64`
Lists tickers that have notes, with counts.
**200** body: `{"tickers": [{ticker, market, n, last_note}]}`.

#### `DELETE /api/notes/{note_id}` — `notes.py:67-79`
Soft-deletes a note. Returns **200** `{"ok": true}` when a note was affected;
**404** `"note not found"` when no active note with `note_id` exists (missing
id, already deleted, or never existed). A double delete (after the first
soft-deletes) → **404**.

### macro router

Read handlers use the report repository dependency. `POST /api/macro/run`
streams progress while invoking `GenerateMacroReportUseCase`, which queries the
DuckDB market views, calls the configured `ILLMClient`, and persists through
`IReportRepository`. The API no longer imports `src/macro.*`.

#### `GET /api/macro/reports` — `macro.py:22-35`
Lists macro reports (id/date/timestamp/tags/analyst/risk_signal/volatility), most
recent first. DB absent → **200** `{"reports": []}`.
**200** body: `{"reports": [{...}]}`.

#### `GET /api/macro/reports/latest` — `macro.py:38-53`
Latest report by `date DESC, timestamp DESC`. DB absent or empty table → **404**
`"no reports"`.
**200** body: full `macro_reports` row (dict).

#### `GET /api/macro/reports/{report_id}` — `macro.py:56-68`
Single report by id. Absent → **404** `"not found"`.
**200** body: full `macro_reports` row (dict).

#### `POST /api/macro/run` — `macro.py:71-129`
Body: `MacroRunRequest` (all fields optional; `{}` is valid). Returns an SSE
stream of `{progress, message}` events (see [SSE Contract](#sse-contract)). The
worker emits progress `10/40/80/100` (fetch market views / generate AI report /
archive / done) or `progress=-1` with fixed message `"macro run failed"` on
error.

### analysis router

Both handlers open `research_insights.db` directly.

#### `GET /api/analysis/reports` — `analysis.py:13-25`
Lists research reports (id/date/timestamp/tags/analyst/title), most recent first.
DB absent → **200** `{"reports": []}`.
**200** body: `{"reports": [{...}]}`.

#### `GET /api/analysis/reports/{report_id}` — `analysis.py:28-40`
Single research report by id. Absent → **404** `"not found"`.
**200** body: full `research_reports` row (dict).

### config router

Helpers `_read_json`/`_write_json` (`config.py:17-26`) read/write JSON files
under `_PROJECT_ROOT`.

#### `GET /api/config` — `config.py:48-52`
Reads `models_config.json`. **The `api_key` field is redacted from every
profile before the response is returned** (S002-013, `_redact_api_keys`
`config.py:29-45`) — neither the real key nor the placeholder sentinel is
echoed to any HTTP client. File absent → **200** `{}`.
**200** body: `models_config.json` contents with `api_key` stripped.

#### `GET /api/config/settings` — `config.py:55-59`
Reads `user_settings.json`. File absent → **200** `{}`.

#### `PUT /api/config/settings` — `config.py:66-74`
Body: `SettingsUpdate`. Merges `tdx_path` (if provided) into
`user_settings.json` and writes it back.
**200** body: `{"ok": true, "settings": <merged dict>}`.

#### `POST /api/config/validate-tdx` — `config.py:77-88`
Body: `SettingsUpdate`. `tdx_path` falsy → **400** `"tdx_path required"`.
Returns `{valid: true, vipdoc_path}` if `<path>/vipdoc` exists or `<path>`
itself is named `vipdoc`, else `{valid: false, message: "vipdoc directory not found"}`
(**200** in both cases — an invalid path is not an error).

### agent router

The Research Copilot endpoints expose the interview-demo agent workflow. The
runtime stores run state in memory for the demo and returns operator-safe 404
errors when a run or approval id is unknown.

#### `POST /api/agent/runs` — `agent.py`
Body: arbitrary JSON matching the demo request shape (`workflow`, `question`,
`document_ids`, `portfolio_id`, `market`, `language`, `model_policy`). Creates a
run and advances it until completion or approval pause.

**200** body: serialized `AgentRun` with `status`, `events`, `artifacts`, and
`approvals`.

#### `GET /api/agent/runs/{run_id}` — `agent.py`
Returns a serialized run. Unknown id → **404** `"run not found"`.

#### `GET /api/agent/runs/{run_id}/events` — `agent.py`
Returns `{"events": [...]}` for the run.

#### `GET /api/agent/runs/{run_id}/stream` — `agent.py`
Returns stored run events as SSE (`event: agent_event`, JSON payload per event).

#### `GET /api/agent/runs/{run_id}/artifacts` — `agent.py`
Returns `{"artifacts": [...]}`.

#### `GET /api/agent/runs/{run_id}/approvals` — `agent.py`
Returns `{"approvals": [...]}`.

#### `POST /api/agent/runs/{run_id}/approvals/{approval_id}` — `agent.py`
Body: `{"approved": true|false}`. Resolves an approval and returns the updated
run. Unknown run or approval id → **404**.

### documents router

#### `POST /api/documents` — `documents.py`
Registers a demo document payload without multipart requirements. Body:
`{"filename": "annual-report.pdf", "content": "..."}`. Returns a deterministic
document id and metadata.

#### `POST /v1/documents` — `v1/documents.py`
Preferred daemon document endpoint. Accepts either:

- `multipart/form-data` with field `file` for a real uploaded file.
- Backward-compatible JSON `{"filename": "...", "content": "...", "document_id": "optional"}` for text registration.

Successful responses include `document_id`, `filename`, `original_filename`,
`file_hash`, `mime_type`, `size_bytes`, `storage_path`, `kimi_file_id`,
`parsing_status`, `parser_error`, `content`, `created_at`, and `updated_at`.
Unsupported file types, empty files, and oversized uploads return **400** via
the standard error envelope.

When the default composition root is used, successful registration also triggers
local page/chunk extraction for agent context. The public v1 API does not expose
page/chunk/evidence read endpoints yet; those records are currently consumed by
the runtime context builder.

#### `GET /v1/documents` / `GET /v1/documents/{document_id}` — `v1/documents.py`
List recent persisted document metadata or retrieve one document. Unknown
document id returns **404**.

## SSE Contract

Three endpoints stream Server-Sent Events via `sse_starlette.sse.EventSourceResponse`:

- `POST /api/scan/{market}` (`scan.py:152-268`)
- `POST /api/macro/run` (`macro.py:71-129`)
- `GET /api/agent/runs/{run_id}/stream` (`agent.py`)

Each SSE event has the shape (emitted at `scan.py:264` and `macro.py:125`):

```
event: progress
data: {"progress": <int>, "message": "<str>"}
```

**Terminal sentinels** — the stream closes as soon as an event with
`progress in {100, -1}` is emitted (`scan.py:265-266`, `macro.py:126-127`):

| `progress` | Meaning |
|---|---|
| `100` | Success (`message: "done"` for scan; macro emits `"done"` from the worker). Stream closes. |
| `-1` | Error. `message` carries `"error: {e}"`. Stream closes. |
| `0..99` | Intermediate progress; client should keep the connection open. |

> **Scan progress markers**: the scan worker emits `0`/`2`/`5`/`100` plus
> download-driver callbacks; the macro worker emits `10`/`40`/`80`/`100`;
> the agent stream emits stored `agent` events rather than numeric progress.

**Single-scan-per-market lock** (scan only): `POST /api/scan/{market}` acquires
`_scan_locks[market]` non-blocking (`scan.py:157`); if a scan for that market is
already in flight, the request is rejected with **409** (no SSE stream starts).
See [Concurrency](#concurrency).

> **SSE error-payload note**: the `progress=-1` event places the raw exception
> text into the in-band `message` field (`scan.py:251-254`, `macro.py:115-118`).
> This is a stream payload, not an HTTP error response — it is tracked as a
> separate open question (fastapi-service.md §9 open question 9) and is NOT
> covered by the HTTP [Error Contract](#error-contract) envelope. The S002-010
> guarantee is that a dropped scan surfaces a terminal `-1` event within 30s
> rather than hanging in a `"running"` state.

## CORS

**Current state** (`src/doge/interfaces/api/main.py`):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # local-first; safe only under loopback bind
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`OPTIONS` preflight from a browser is answered permissively. This is safe
**only because** the server binds to `127.0.0.1` (`src/doge/interfaces/api/main.py`); no
remote client can reach it in the default deployment. The Vue web console is
served from the same origin or a `localhost` dev server, so `*` is operationally
equivalent to `http://localhost:*`.

**Hardening target (gated before any non-loopback bind)**: replace `["*"]` with an
explicit allow-list of localhost origins (e.g. `http://localhost:5173`,
`http://127.0.0.1:5173`, the Tauri/desktop origin), gated behind a new
`APIConfig.cors_origins` setting. ADR-0007 is Accepted with a
loopback-guaranteed posture; do not treat the tightened CORS list as the current
contract.

## Error Contract

**Shipped (S002-009, ADR-0007 Decision 3).** Every error response uses a single
stable, non-leaking envelope:

```json
{"error": {"code": "<stable-code>", "message": "<operator-safe message>"}}
```

implemented by two global exception handlers in `doge.interfaces.api.main`:

- `@app.exception_handler(HTTPException)` (`src/doge/interfaces/api/main.py`) — reshapes
  every `HTTPException(4xx/5xx, detail)` into the envelope, passing
  `exc.detail` (operator-authored fixed text) through unchanged as `message`.
- `@app.exception_handler(Exception)` (`src/doge/interfaces/api/main.py`) — catch-all for
  any otherwise-unhandled exception. The raw exception (type, message,
  traceback) is logged server-side via
  `logging.getLogger("doge.api").exception(...)` and is **never returned**; the
  response body is the fixed `{"error": {"code": "internal_error", "message":
  "internal server error"}}`.

The `code` field is a **string enum** (`src/doge/interfaces/api/main.py`), not a numeric
string, so UI consumers (and the S002-010 SSE client) can branch on
`error.error.code`:

| HTTP status | `code` |
|---|---|
| 400 | `bad_request` |
| 404 | `not_found` |
| 409 | `conflict` |
| 422 | `unprocessable` |
| 500 | `internal_error` |
| (any other) | `http_{status}` fallback |

> **422 special case**: FastAPI's default `RequestValidationError` handler is
  intentionally left as-is (emits `{"detail": [...]}`). Enveloping Pydantic
  validation errors was out of scope for S002-009; existing tests assert the
  **422** status code only (`src/doge/interfaces/api/main.py`). S002-011 owns any
  follow-on.

### Status codes by situation

| Situation | Status | `code` | Example `message` |
|---|---|---|---|
| Success | 200 | — (no envelope) | endpoint-specific body |
| Invalid `market` path/query param | 400 | `bad_request` | `"market must be 'cn' or 'us'"` |
| `validate-tdx` with no `tdx_path` | 400 | `bad_request` | `"tdx_path required"` |
| Resource not found (table/report/note) | 404 | `not_found` | `"note not found"` / `"not found"` / `"no reports"` / `"database not found"` |
| Concurrent scan on same market | 409 | `conflict` | `"{market} scan already running"` |
| Missing/invalid Pydantic body or query param | 422 | `unprocessable` (default `{"detail":[...]}`) | Pydantic validation array |
| Internal handler exception | 500 | `internal_error` | `"internal server error"` |

The BLOCKING contract regression is
`tests/contract/test_api_error_envelope.py` — it asserts the stable envelope
shape on the 400/404/409 paths and a no-`str(e)`-leak guarantee on the
`get_kline` and five `notes` internal-error paths (each underlying dependency is
monkeypatched to raise `RuntimeError("boom /secret/path leak")` and the response
is asserted to carry neither the path nor the exception type).

**Retry semantics**: the API itself performs **no retry**. Scan/macro SSE
workers do not retry upstream (TDX/yfinance/LLM) failures — they surface
`progress=-1` and close. The macro data-fetch retry (`max_retries=3`, owned by
Module #4) happens inside the worker thread before any LLM call. Clients that
need retries must implement them at the HTTP layer.

## Concurrency

- **Per-market scan lock**: `_scan_locks = {cn: Lock, us: Lock}` (`scan.py:46`)
  serializes scans — at most **one in-flight scan per market per process**.
  Acquired non-blocking at `scan.py:157`; a second concurrent scan for the same
  market gets **409**. The lock is released and `_scan_status[market]` reset to
  `"idle"` in the worker thread's `finally` (`scan.py:255-257`).
- **SSE worker threads**: scan (`scan.py:259`) and macro-run (`macro.py:120`)
  spawn a `threading.Thread(daemon=True)` and bridge progress to the async
  event loop via `asyncio.run_coroutine_threadsafe(queue.put(...), loop)`
  (`scan.py:166-172`, `macro.py:80-86`).
- **SQLite reads**: each read opens a fresh `sqlite3.connect(...)` and closes
  it in the same handler — no pooling, no WAL, no `busy_timeout`. Concurrent
  reads are safe; concurrent writer+reader can hit `database is locked`.
- **Single-process assumption**: `_scan_locks`/`_scan_status` are module-global.
  uvicorn `--workers > 1` would break the single-scan-per-market guarantee
  (each worker has its own lock map). The deployment assumption is a single
  uvicorn worker (`python -m uvicorn doge.interfaces.api.main:app --host 127.0.0.1 --port 8901`).

## OpenAPI

FastAPI auto-generates the OpenAPI schema at runtime. Available at:

- `GET /docs` — interactive Swagger UI.
- `GET /redoc` — ReDoc UI.
- `GET /openapi.json` — raw OpenAPI 3.x schema.
- `GET /docs/oauth2-redirect` — OAuth2 redirect helper (unused; no auth).

These are infrastructure routes, not product endpoints (not counted in the 26).
They are available in every environment by default — convenient for local dev;
would be disabled behind a flag in a multi-tenant deployment (not applicable
here).

---

## Related

- `design/cdd/fastapi-service.md` — the Module #9 CDD this reference serves
  (route table §4.1, schemas §4.2, response shapes §4.3, edge cases §5,
  integration requirements §9).
- [ADR-0007](architecture/adr-0007-api-surface-and-cors.md) — API surface
  enumeration, CORS local-first rationale, error-envelope decision.
- `src/doge/interfaces/api/main.py` — application construction (app, CORS, exception handlers,
  routers, bind).
- `src/doge/interfaces/api/routers/{scan,data,notes,macro,analysis,config}.py` — the six
  routers.
- `tests/test_api_routers.py` — 57-case router contract suite (every endpoint:
  success + validation failure + edge case).
- `tests/contract/test_api_error_envelope.py` — S002-009 BLOCKING contract
  regression (stable envelope + no-`str(e)`-leak).
- `tests/contract/test_config_router_api_key_redaction.py` — S002-013
  `api_key`-redaction regression for `GET /api/config`.
- `tests/contract/test_api_doc_route_coverage.py` — docs-consistency gate
  (this doc's route table vs live `app.routes`; this doc's error-code table vs
  shipped behavior).
