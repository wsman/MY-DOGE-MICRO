# HTTP API Reference (FastAPI)

The local-first HTTP backend of OpenDoge. A single FastAPI application
(`doge.interfaces.api.main`) binds to `127.0.0.1:8901` by default and exposes
**98 HTTP routes**: 34 legacy `/api/*` compatibility routes plus 64 daemon/v1
and health routes.
Per ADR-0024, new platform work should target `/v1/*` through SDK clients.
Legacy `/api/*` remains for local compatibility and emits deprecation metadata
headers.

The recommended Platform Alpha path only needs five `/v1` families:
`sessions`, `runs`, `documents`, `tools`, and `platform`. `audit`,
`enterprise`, `health`, `portfolios`, and `slots` are operator/reference APIs and are
not part of the main user workflow.

> **Stack**: FastAPI 0.123.8, Uvicorn 0.38.0, Pydantic 2.12.4, sse-starlette
> 3.0.3, httpx 0.28.1 (TestClient) — pinned in `pyproject.toml:11-25`. Reverse-documented
> in `design/cdd/fastapi-service.md`; API-surface decision in
> [ADR-0007](architecture/adr-0007-api-surface-and-cors.md).

## Table of Contents

- [Overview](#overview)
- [Recommended v1 Workflow](#recommended-v1-workflow)
- [Base URL & Transports](#base-url--transports)
- [Authentication](#authentication)
- [Full Reference](#full-reference) — route table, primary v1, legacy, operator, SSE, CORS, error, concurrency, OpenAPI
- [Related](#related)

## Overview

| Property | Value | Source |
|---|---|---|
| Application | `FastAPI(title="MY-DOGE API", version="0.1.0")` | `src/doge/interfaces/api/main.py` |
| Bind host | `127.0.0.1` by default; non-loopback requires the remote-bind gate | `src/doge/interfaces/api/main.py` |
| Bind port | `8901` | `src/doge/interfaces/api/main.py` |
| Auth | Mode-driven: `local_demo` no bearer token; `enterprise` bearer provider fail-closed | see [Authentication](#authentication) |
| Routers | legacy `/api/*` routers + v1 daemon routers | `src/doge/interfaces/api/main.py` |
| HTTP routes | 98 (34 legacy `/api/*` routes + 64 daemon/v1 and health routes) | `src/doge/interfaces/api/main.py` |
| Framework | FastAPI 0.123.8 + uvicorn 0.38.0 | `pyproject.toml:19-20` |
| Streaming | sse-starlette 3.0.3 (`EventSourceResponse`) | `pyproject.toml:21` |

The canonical server is started directly:

```bash
python -m uvicorn doge.interfaces.api.main:app --host 127.0.0.1 --port 8901
```

`src/api` remains only as a deprecated compatibility redirect shim. New
integrations should import or launch `doge.interfaces.api`.

## Recommended v1 Workflow

Primary user and SDK flows should stay on this sequence:

1. `POST /v1/sessions`
2. `POST /v1/documents` when a run needs document evidence
3. `POST /v1/sessions/{session_id}/turns`
4. `GET /v1/runs/{run_id}/stream` or `GET /v1/runs/{run_id}/events`
5. `POST /v1/runs/{run_id}/approvals/{approval_id}` or `/resume` when needed
6. `GET /v1/runs/{run_id}/artifacts` and optional summary/citation/eval reads
7. `GET /v1/runs` when the UI or SDK needs compact run history for comparison
8. `GET /v1/research-cases/{case_id}/progress` when a case view needs
   per-step governance progress

`GET /v1/tools`, `GET /v1/capabilities`, read-only `GET /v1/slots`, and
read-only `GET /v1/slot-bundles` support capability discovery. `GET /v1/ui-panels`
is a feature-gated UI-slot metadata surface for the Research workspace.
`DOGE_FEATURE_SLOT_ENFORCEMENT` affects slot status/runtime assembly but does
not add routes. `DOGE_FEATURE_SLOT_LOADER` enables persisted local bundle
activation through `POST /v1/slot-bundles/{bundle_id}/activate` and
`POST /v1/slot-bundles/active/deactivate`. `DOGE_FEATURE_SLOT_INSTALL` enables
local-path slot install through `POST /v1/slots/install`; URL/upload install,
marketplace install, and YAML manifests remain deferred. Audit, enterprise ACL, health/readiness, and portfolio import
endpoints remain documented below as operator/reference APIs, not the default
product path.

Legacy `/api/*` responses include:

- `Deprecation: true`
- `Sunset: Wed, 30 Sep 2026 00:00:00 GMT`
- `Link: <...adr-0024-single-stack-runtime-direction.md>; rel="deprecation"`
- `X-DOGE-Compatibility-Surface: legacy-api`

Two BLAS/OpenMP thread-count shims are set at import via
`os.environ.setdefault` (`src/doge/interfaces/api/main.py`) — `OPENBLAS_NUM_THREADS=1`
and `OMP_NUM_THREADS=1` — shared with the DuckDB/ai_analysis layers.

## Base URL & Transports

**Base URL**: `http://127.0.0.1:8901` — legacy compatibility routes live under
`/api`; preferred daemon/platform routes live under `/v1` plus `/health`.

Two response modes are used (`design/cdd/fastapi-service.md` §9.1):

1. **JSON** (default) — every read/write endpoint except the two SSE streams.
   `Content-Type: application/json`. Request and response bodies are JSON.
2. **Server-Sent Events (SSE)** — three endpoints return an
   `EventSourceResponse` with `Content-Type: text/event-stream`:
  - `POST /api/scan/{market}` (`src/doge/interfaces/api_legacy/routers/scan.py`)
   - `POST /api/macro/run` (`src/doge/interfaces/api_legacy/routers/macro.py`)
   - `GET /api/agent/runs/{run_id}/stream` (`src/doge/interfaces/api_legacy/routers/agent.py`)

   See [SSE Contract](reference/http-api-contracts.md#sse-contract) for the event format.

HTTP/1.1 over loopback, served by uvicorn by default. Remote bind is a
promotion gate and requires explicit TLS termination acknowledgement.

## Authentication

Authentication is mode-driven (`DOGE_AUTH_MODE`, `AuthConfig` in
`src/doge/config/settings.py`):

- `local_demo` (default): no bearer token required. This is safe only for the
  default loopback bind (`127.0.0.1`). Legacy `/api/*` routers are mounted only
  for local loopback demo mode.
- `enterprise`: a bearer provider (OIDC/JWKS or static token) is required.
  Startup fails closed with `RuntimeError` when the provider is deny-all
  (`_validate_api_auth_startup`). Tenant, role, entitlement, approval authority,
  and project claims are resolved through the configured claim names. Legacy
  `/api/*` routers are disabled in enterprise mode.
- Remote non-loopback bind is a promotion gate. It requires
  `DOGE_ALLOW_REMOTE_BIND=1`, `DOGE_AUTH_MODE=enterprise`, a non-deny-all
  provider, explicit CORS allow-list with no `"*"`, and
  `tls_termination_required=True`. `_resolve_bind_host` and
  `_validate_api_remote_bind_startup` enforce this before serving.

## Full Reference

- Route table and per-route reference (all 98 HTTP routes; primary v1
  families `sessions`, `runs`, `documents`, `tools`, `platform`; legacy
  `/api/*`; operator appendix):
  [reference/http-api.md](reference/http-api.md)
- Transport, SSE, CORS, error contract, concurrency, OpenAPI:
  [reference/http-api-contracts.md](reference/http-api-contracts.md)

Exhaustive schemas remain available through `GET /openapi.json`.

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
  (`reference/http-api.md` route table vs live `app.routes`;
  `reference/http-api-contracts.md` error-code table vs shipped behavior).
