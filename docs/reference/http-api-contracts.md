# HTTP API Contracts

Transport, streaming (SSE), CORS, error-envelope, concurrency, and OpenAPI
contracts for the OpenDoge FastAPI backend. The route table and per-route
reference live in [http-api.md](http-api.md); the quick-start narrative lives
in [../API.md](../API.md).

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
