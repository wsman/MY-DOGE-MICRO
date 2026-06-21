# CDD: FastAPI Service (Module #9)

> **Module #9** — Category: **Interface**
> **Slug**: `fastapi-service`
> **Status**: In Review
> **Last Verified**: 2026-06-21
> **Notes**: Major release-follow-up update; canonical app, 51 product routes, Research Copilot compatibility routes, document routes, daemon `/v1/*` routes, SSE behavior, and shipped error envelope are reflected here.
> **Depends on**: #1 `runtime-configuration`, #2 `market-data-storage`, #4 `macro-strategy-engine`, #5 `micro-momentum-scanner`, #13 `research-copilot-agent-runtime`, #14 `document-evidence-pipeline`
> **Depended on by**: #11 `vue-web-console`, #10 `pyqt-desktop-dashboard`, #15 `sdk-daemon-client-interfaces`
> **Source files reverse-documented**: `src/doge/interfaces/api/main.py`, `src/doge/interfaces/api/routers/{scan,data,notes,macro,analysis,config,agent,documents}.py`, `src/doge/interfaces/api/routers/v1/*.py`; `src/api/*` is compatibility shim history only.
> **Related ADRs**: [ADR-0007](../../docs/architecture/adr-0007-api-surface-and-cors.md), [ADR-0011](../../docs/architecture/adr-0011-agent-runtime-levels.md), [ADR-0001](../../docs/architecture/adr-0001-brownfield-clean-architecture.md), [ADR-0002](../../docs/architecture/adr-0002-centralized-configuration.md)

---

## 1. Overview

The FastAPI Service is the local-first HTTP interface layer of MY-DOGE-MICRO.
The canonical application is `doge.interfaces.api.main:app`, launched on
`127.0.0.1:8901`. It exposes **51 product routes**:

- 34 legacy `/api/*` product routes, including top-level helpers, market scan,
  data browsing, notes, macro reports, analysis reports, config, Research
  Copilot demo routes, and document registration.
- 17 daemon/v1 routes for health/readiness, sessions, runs, documents, tool
  schemas, approvals, cancellation, artifacts, and SSE replay.

The API remains local-first and unauthenticated. ADR-0007 allows permissive CORS
only because `_resolve_bind_host()` rejects non-loopback binds. Rebinding to any
remote interface requires CORS allow-list hardening and auth first.

## 2. User Promise / JTBD

An operator can drive the platform through a local HTTP API: start scans and
watch progress, browse local market data, manage notes, read reports, upload or
register documents, and run Research Copilot sessions without exposing the
service to the network by default.

Developers can target the `/v1/*` daemon routes for runtime clients while
existing product screens continue to consume the `/api/*` routes.

## 3. Detailed Behavior

### 3.1 Application Construction

- `FastAPI(title="MY-DOGE API", version="0.1.0", lifespan=lifespan)` starts
  the daemon worker on lifespan entry and stops it on exit.
- `_PROJECT_ROOT` is derived from `get_settings().project_root`; the name stays
  monkeypatchable for tests, but the legacy dirname walk is gone.
- BLAS/OpenMP environment defaults are set at import:
  `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`.
- `CORSMiddleware` keeps `allow_origins=["*"]`, `allow_methods=["*"]`,
  `allow_headers=["*"]` under the ADR-0007 loopback guarantee.
- `HTTPException` is reshaped into
  `{"error": {"code": <string-enum>, "message": <operator-safe-detail>}}`.
- otherwise-unhandled exceptions are logged server-side and returned as
  `{"error": {"code": "internal_error", "message": "internal server error"}}`.
- FastAPI/Pydantic 422 validation responses intentionally remain FastAPI's
  default `{"detail": [...]}` shape.

### 3.2 Legacy `/api/*` Product Routes

These routes remain public product routes for the web console and existing
operator workflows:

- top-level helpers: `GET /api/health`, `GET /api/stats`.
- scan router: server list/test/status and `POST /api/scan/{market}` SSE scan.
- data router: table listing/query, ticker kline, ticker names.
- notes router: ticker context, add/search/recent/tracked notes, soft delete.
- macro router: report list/latest/read and `POST /api/macro/run` SSE.
- analysis router: research report list/read.
- config router: model config, user settings, TDX validation.
- agent router: compatibility Research Copilot run/event/stream/artifact/
  approval routes under `/api/agent`.
- documents router: compatibility document registration under `/api/documents`.

### 3.3 Daemon `/v1/*` Routes

New runtime clients use daemon routes:

- `GET /health`, `GET /health/ready`.
- `POST /v1/sessions`, `GET /v1/sessions`,
  `GET /v1/sessions/{session_id}`,
  `POST /v1/sessions/{session_id}/turns`.
- `GET /v1/runs/{run_id}`, `POST /v1/runs/{run_id}/cancel`,
  `GET /v1/runs/{run_id}/events`,
  `GET /v1/runs/{run_id}/stream`,
  `GET /v1/runs/{run_id}/artifacts`,
  `GET /v1/runs/{run_id}/approvals`,
  `POST /v1/runs/{run_id}/approvals/{approval_id}`.
- `POST /v1/documents`, `GET /v1/documents`,
  `GET /v1/documents/{document_id}`.
- `GET /v1/tools`.

### 3.4 Streaming

Three product endpoints stream with `EventSourceResponse`:

- `POST /api/scan/{market}` for market scan progress.
- `POST /api/macro/run` for macro report progress.
- `GET /api/agent/runs/{run_id}/stream` for compatibility agent events.

Daemon runtime streaming uses `GET /v1/runs/{run_id}/stream` and supports
persisted event replay via `Last-Event-ID`.

### 3.5 Concurrency

- Scan concurrency is serialized by per-market in-process locks. A second scan
  for the same market returns `409 conflict`.
- Daemon run concurrency is managed by the runtime worker and persisted run
  state. Cancellation is requested through `/v1/runs/{run_id}/cancel`.
- Uvicorn multi-worker deployment is out of scope; in-process locks and event
  bus semantics assume a single local service process.

## 4. Contracts / Data Model

### 4.1 Full Route Table

The route table is canonical in [docs/API.md](../../docs/API.md) and is guarded
by `tests/contract/test_api_doc_route_coverage.py`. The current count is exactly
**51 product routes**:

| Range | Surface | Count |
|---|---|---:|
| 1-2 | top-level `/api` helpers | 2 |
| 3-26 | legacy scan/data/notes/macro/analysis/config routers | 24 |
| 27-33 | `/api/agent` compatibility routes | 7 |
| 34 | `/api/documents` compatibility route | 1 |
| 35-51 | health and `/v1/*` daemon routes | 17 |

### 4.2 Error Contract

| Situation | Response |
|---|---|
| Explicit bad request | `400 {"error": {"code": "bad_request", "message": ...}}` |
| Missing resource | `404 {"error": {"code": "not_found", "message": ...}}` |
| Scan conflict | `409 {"error": {"code": "conflict", "message": ...}}` |
| Unhandled internal exception | `500 {"error": {"code": "internal_error", "message": "internal server error"}}` |
| Pydantic/FastAPI validation | `422 {"detail": [...]}` |

Raw exception text, stack traces, DB paths, SQL fragments, or API keys must not
be returned over HTTP.

### 4.3 Document and Runtime Data

The API itself does not own runtime state. It routes to Module #13 and #14:

- sessions, turns, runs, events, approvals, and artifacts live in the agent
  runtime persistence boundary.
- uploaded/registered documents, pages, chunks, and evidence live in the
  document evidence boundary.

## 5. Edge Cases

- Missing local DB files must return empty lists or operator-safe errors, not
  process crashes.
- Missing provider credentials must not prevent no-network health, docs, or
  mocked tests from passing.
- Unsupported document uploads must preserve metadata consistency and report an
  operator-safe error.
- SSE reconnect must replay persisted daemon events without duplicating terminal
  states in clients.
- Non-loopback bind requests must fail closed until auth and CORS hardening are
  designed and implemented.

## 6. Dependencies

- Runtime Configuration (#1): project root, DB directory, bind-host policy.
- Market Data Storage (#2): schema browsing and market data reads.
- Macro Strategy Engine (#4): macro report generation.
- Micro Momentum Scanner (#5): market scan workflow.
- Research Insight Knowledge Base (#7): notes and report metadata.
- Research Copilot Agent Runtime (#13): sessions, runs, approvals, events.
- Document Evidence Pipeline (#14): document upload and evidence metadata.
- SDK And Daemon Client Interfaces (#15): `/v1/*` daemon contract consumers.

## 7. Configuration

| Knob | Current source | Note |
|---|---|---|
| bind host | `DOGE_BIND_HOST`, default `127.0.0.1` | Non-loopback rejected by `_resolve_bind_host()`. |
| bind port | hardcoded `8901` | Future API config may own this. |
| CORS origins | `["*"]` | Accepted only with loopback guarantee. |
| DB paths | `get_settings().db.*` and repository deps | Some legacy routers still carry migration debt. |
| document storage | local data directory | See Module #14. |

## 8. Acceptance Criteria

- [x] `docs/API.md` enumerates exactly 51 product routes.
- [x] `tests/contract/test_api_doc_route_coverage.py` verifies docs-vs-live route
      coverage.
- [x] HTTPException and unhandled exceptions use the shipped non-leaking error
      envelope except default 422 validation responses.
- [x] ADR-0007 is Accepted with loopback-guaranteed posture.
- [x] `/api/agent`, `/api/documents`, `/v1/*`, daemon SSE, approvals,
      cancellation, and document upload/read routes are represented in the CDD.
- [ ] All legacy routers route reads/writes through repositories/use cases with
      no direct SQLite/DuckDB access in interface code.
- [ ] CORS and auth are redesigned before any non-loopback deployment.
- [ ] Runtime maturity claims remain blocked by
      `docs/progress/runtime-maturity.yaml` while `production_ready: false`.

## 9. Integration Requirements

- `/api/*` routes remain product/compatibility routes.
- `/v1/*` routes are the daemon/SDK-facing runtime contract.
- API docs, CDD, ADR-0007, ADR-0011, and TR registry must stay synchronized when
  a product route is added or removed.
- New error responses must use operator-safe messages and string-enum codes.
- New streaming endpoints must document replay/cancellation/terminal semantics.

## 10. UI Requirements

The web console may consume both legacy `/api/*` screens and daemon `/v1/*`
runtime flows. UI copy must distinguish preview/experimental runtime capability
from production readiness while the maturity registry forbids promotion.

## 11. Open Questions

1. Should 422 validation responses be normalized into the same error envelope?
2. Which `/v1/*` DTO fields are frozen as SDK contract fields?
3. Should scan/macro SSE streams adopt the daemon run-event schema?
4. Which repository methods are still missing before direct interface DB access
   can be removed completely?
5. What evidence is required to promote Level 2 daemon maturity?
