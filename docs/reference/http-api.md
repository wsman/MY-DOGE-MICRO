# HTTP API Reference

Full route table and per-route reference for the MY-DOGE-MICRO FastAPI backend
(90 HTTP routes: 34 legacy `/api/*` + 56 daemon/v1). The quick-start
narrative lives in [../API.md](../API.md); transport, SSE, CORS, error,
concurrency, and OpenAPI contracts live in
[http-api-contracts.md](http-api-contracts.md).

The docs-consistency gate `tests/contract/test_api_doc_route_coverage.py`
asserts the route table below matches the live FastAPI `app.routes`, so this
reference and the code cannot drift.

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

### scan router — prefix `/api/scan` (`src/doge/interfaces/api_legacy/routers/scan.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 3 | GET | `/api/scan/servers` | CN/US TDX server list | `scan.py:70-77` |
| 4 | POST | `/api/scan/servers/test` | Probe server latencies | `scan.py:84-134` |
| 5 | GET | `/api/scan/status` | In-memory scan status | `scan.py:147-149` |
| 6 | POST | `/api/scan/{market}` | Start scan (SSE) | `scan.py:152-268` |

### data router — prefix `/api/data` (`src/doge/interfaces/api_legacy/routers/data.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 7 | GET | `/api/data/{market}/tables` | List tables in market DB | `data.py:22-34` |
| 8 | GET | `/api/data/{market}/table/{table_name}` | Paginated table query | `data.py:37-100` |
| 9 | GET | `/api/data/{market}/ticker/{ticker}/kline` | OHLCV + MA kline (DuckDB) | `data.py:103-143` |
| 10 | GET | `/api/data/{market}/ticker-names` | Ticker→name map | `data.py:191-198` |

### notes router — prefix `/api/notes` (`src/doge/interfaces/api_legacy/routers/notes.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 11 | GET | `/api/notes/ticker/{ticker}` | Price+name+notes context | `notes.py:21-31` |
| 12 | POST | `/api/notes` | Add a note | `notes.py:34-45` |
| 13 | GET | `/api/notes/search` | Keyword search | `notes.py:48-52` |
| 14 | GET | `/api/notes/recent` | Recent notes | `notes.py:55-58` |
| 15 | GET | `/api/notes/tracked` | Tracked tickers | `notes.py:61-64` |
| 16 | DELETE | `/api/notes/{note_id}` | Soft-delete a note | `notes.py:67-79` |

### macro router — prefix `/api/macro` (`src/doge/interfaces/api_legacy/routers/macro.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 17 | GET | `/api/macro/reports` | List macro reports | `macro.py:22-35` |
| 18 | GET | `/api/macro/reports/latest` | Latest macro report | `macro.py:38-53` |
| 19 | GET | `/api/macro/reports/{report_id}` | Single macro report | `macro.py:56-68` |
| 20 | POST | `/api/macro/run` | Run macro analysis (SSE) | `macro.py:71-129` |

### analysis router — prefix `/api/analysis` (`src/doge/interfaces/api_legacy/routers/analysis.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 21 | GET | `/api/analysis/reports` | List research reports | `analysis.py:13-25` |
| 22 | GET | `/api/analysis/reports/{report_id}` | Single research report | `analysis.py:28-40` |

### config router — prefix `/api/config` (`src/doge/interfaces/api_legacy/routers/config.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 23 | GET | `/api/config` | Read `models_config.json` (api_key redacted) | `config.py:48-52` |
| 24 | GET | `/api/config/settings` | Read `user_settings.json` | `config.py:55-59` |
| 25 | PUT | `/api/config/settings` | Update `user_settings.json` | `config.py:66-74` |
| 26 | POST | `/api/config/validate-tdx` | Validate TDX vipdoc path | `config.py:77-88` |

### agent router — prefix `/api/agent` (`src/doge/interfaces/api_legacy/routers/agent.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 27 | POST | `/api/agent/runs` | Create and advance a Research Copilot run | `agent.py` |
| 28 | GET | `/api/agent/runs/{run_id}` | Read run status and metadata | `agent.py` |
| 29 | GET | `/api/agent/runs/{run_id}/events` | Read stored agent events | `agent.py` |
| 30 | GET | `/api/agent/runs/{run_id}/stream` | Stream run events as SSE | `agent.py` |
| 31 | GET | `/api/agent/runs/{run_id}/artifacts` | Read generated artifacts | `agent.py` |
| 32 | GET | `/api/agent/runs/{run_id}/approvals` | Read pending/resolved approvals | `agent.py` |
| 33 | POST | `/api/agent/runs/{run_id}/approvals/{approval_id}` | Legacy approval endpoint; returns 409 and points clients to `/v1` | `agent.py` |

### documents router — prefix `/api/documents` (`src/doge/interfaces/api_legacy/routers/documents.py`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 34 | POST | `/api/documents` | Register a demo document payload | `documents.py` |

### v1 daemon routes — prefix `/v1` plus health (`src/doge/interfaces/gateway/routers/`)

| # | Method | Path | Purpose | file:line |
|---|---|---|---|---|
| 35 | GET | `/health` | Daemon liveness probe | `v1/health.py` |
| 36 | GET | `/health/ready` | Daemon readiness probe | `v1/health.py` |
| 37 | POST | `/v1/sessions` | Create a persisted agent session | `v1/sessions.py` |
| 38 | GET | `/v1/sessions` | List recent sessions | `v1/sessions.py` |
| 39 | GET | `/v1/sessions/{session_id}` | Read a session and turns | `v1/sessions.py` |
| 40 | POST | `/v1/sessions/{session_id}/turns` | Enqueue a session turn; returns 202 + run id | `v1/sessions.py` |
| 41 | GET | `/v1/runs` | List compact persisted runs for comparison | `v1/runs.py` |
| 42 | GET | `/v1/runs/{run_id}` | Read a persisted run | `v1/runs.py` |
| 43 | POST | `/v1/runs/{run_id}/cancel` | Request run cancellation | `v1/runs.py` |
| 44 | GET | `/v1/runs/{run_id}/events` | Read persisted events | `v1/runs.py` |
| 45 | GET | `/v1/runs/{run_id}/stream` | SSE stream with `Last-Event-ID` replay | `v1/runs.py` |
| 46 | GET | `/v1/runs/{run_id}/artifacts` | Read run artifacts | `v1/runs.py` |
| 47 | GET | `/v1/runs/{run_id}/approvals` | Read run approvals | `v1/runs.py` |
| 48 | POST | `/v1/runs/{run_id}/approvals/{approval_id}` | Resolve an approval through the queued continuation path | `v1/runs.py` |
| 49 | POST | `/v1/runs/{run_id}/resume` | Explicitly resume a queued run, optionally resolving one approval first | `v1/runs.py` |
| 50 | GET | `/v1/runs/{run_id}/summary` | Read API-backed run summary snapshot (feature-flagged) | `v1/runs.py` |
| 51 | GET | `/v1/runs/{run_id}/claims` | Read run claims and support status (feature-flagged) | `v1/runs.py` |
| 52 | GET | `/v1/runs/{run_id}/citations` | Read run citations with local provenance and ACL redaction (feature-flagged) | `v1/runs.py` |
| 53 | GET | `/v1/runs/{run_id}/eval` | Read deterministic run eval metrics/checks (feature-flagged) | `v1/runs.py` |
| 54 | POST | `/v1/documents` | Upload a real document file or register a compatible text payload | `v1/documents.py` |
| 55 | GET | `/v1/documents` | List persisted documents | `v1/documents.py` |
| 56 | GET | `/v1/documents/{document_id}` | Read a persisted document | `v1/documents.py` |
| 57 | GET | `/v1/workspaces` | List platform workspaces (feature-flagged) | `v1/platform.py` |
| 58 | POST | `/v1/workspaces` | Create a platform workspace (feature-flagged) | `v1/platform.py` |
| 59 | GET | `/v1/workspaces/{workspace_id}` | Read a platform workspace (feature-flagged) | `v1/platform.py` |
| 60 | GET | `/v1/projects` | List platform projects (feature-flagged) | `v1/platform.py` |
| 61 | POST | `/v1/projects` | Create a platform project (feature-flagged) | `v1/platform.py` |
| 62 | GET | `/v1/projects/{project_id}` | Read a platform project (feature-flagged) | `v1/platform.py` |
| 63 | GET | `/v1/research-cases` | List research cases (feature-flagged) | `v1/platform.py` |
| 64 | POST | `/v1/research-cases` | Create a research case (feature-flagged) | `v1/platform.py` |
| 65 | GET | `/v1/research-cases/{case_id}` | Read a research case (feature-flagged) | `v1/platform.py` |
| 66 | POST | `/v1/research-cases/{case_id}/runs` | Idempotently link a run to a research case (feature-flagged) | `v1/platform.py` |
| 67 | GET | `/v1/home-queue` | Read actionable case/run/data work queue items (feature-flagged) | `v1/platform.py` |
| 68 | GET | `/v1/research-cases/{case_id}/assets` | List assets attached to a research case (feature-flagged) | `v1/platform.py` |
| 69 | POST | `/v1/research-cases/{case_id}/assets` | Attach a document, portfolio, or URL asset to a case (feature-flagged) | `v1/platform.py` |
| 70 | DELETE | `/v1/research-cases/{case_id}/assets/{asset_link_id}` | Remove a case asset link (feature-flagged) | `v1/platform.py` |
| 71 | GET | `/v1/research-cases/{case_id}/decisions` | List recorded case decisions (feature-flagged) | `v1/platform.py` |
| 72 | POST | `/v1/research-cases/{case_id}/decisions` | Record an approve/reject/hold/escalate case decision (feature-flagged) | `v1/platform.py` |
| 73 | POST | `/v1/research-cases/{case_id}/executions/preflight` | Validate template inputs, assets, and capabilities before execution (feature-flagged) | `v1/platform.py` |
| 74 | POST | `/v1/research-cases/{case_id}/executions` | Create a workflow execution, run it, and link it to the case (feature-flagged) | `v1/platform.py` |
| 75 | GET | `/v1/research-cases/{case_id}/executions` | List workflow executions for a case (feature-flagged) | `v1/platform.py` |
| 76 | GET | `/v1/research-cases/{case_id}/executions/{execution_id}` | Read a workflow execution by ID (feature-flagged) | `v1/platform.py` |
| 77 | GET | `/v1/research-cases/{case_id}/review` | Read case review state with latest run summary when enabled (feature-flagged) | `v1/platform.py` |
| 78 | GET | `/v1/research-cases/{case_id}/progress` | Read per-step case governance progress (feature-flagged) | `v1/platform.py` |
| 79 | GET | `/v1/workflow-templates` | List workflow templates (feature-flagged) | `v1/platform.py` |
| 80 | POST | `/v1/workflow-templates` | Create a workflow template definition (feature-flagged) | `v1/platform.py` |
| 81 | GET | `/v1/workflow-templates/{template_id}` | Read a workflow template by ID or slug (feature-flagged) | `v1/platform.py` |
| 82 | GET | `/v1/capabilities` | Read redacted provider, feature, maturity, and tool capability status (feature-flagged) | `v1/platform.py` |
| 83 | GET | `/v1/tools` | List function-tool schemas | `v1/tools.py` |
| 84 | POST | `/v1/portfolios/import` | Import a UTF-8 portfolio CSV and persist holdings | `v1/portfolios.py` |
| 85 | GET | `/v1/audit/events` | List tenant-scoped audit events | `v1/audit.py` |
| 86 | GET | `/v1/audit/events/export` | Export tenant audit events as redacted JSONL | `v1/audit.py` |
| 87 | POST | `/v1/audit/events/retention` | Purge expired tenant audit events by retention policy | `v1/audit.py` |
| 88 | GET | `/v1/enterprise/acl/grants` | List tenant ACL grants for enterprise admins | `v1/enterprise.py` |
| 89 | POST | `/v1/enterprise/acl/grants` | Create a tenant ACL grant | `v1/enterprise.py` |
| 90 | DELETE | `/v1/enterprise/acl/grants` | Revoke a tenant ACL grant | `v1/enterprise.py` |

> The OpenAPI surface also exposes `/openapi.json`, `/docs`,
> `/docs/oauth2-redirect`, `/redoc` (FastAPI defaults) — infrastructure, not
> product endpoints, so not counted in the 90 HTTP routes above.

### Feature-Flagged Platform Surfaces

The backend platformization routes above are additive and default off:

- `DOGE_FEATURE_RUN_SUMMARY_API=1` enables `/v1/runs/{run_id}/summary`,
  `/claims`, `/citations`, and `/eval`.
- `DOGE_FEATURE_PLATFORM_OBJECTS=1` enables workspace, project, research-case,
  case-run link, case asset, workflow execution, decision, review, progress,
  and home queue routes.
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

Python SDK methods mirror these routes with `client.runs.list()`,
`client.runs.resume()`,
`client.runs.summary()`, `client.runs.claims()`, `client.runs.citations()`,
`client.runs.evaluation()`, `client.platform.*`, and
`client.platform.create_research_case_run_from_template()`. Case-centered
execution helpers include `home_queue()`, `preflight_case_execution()`,
`execute_case_template()`, `list_case_executions()`, `get_case_review()`,
`get_case_progress()`, case assets, and case decisions.
`client.capabilities.get()/list()` exposes capability discovery. The
TypeScript SDK mirrors the same surface in camelCase for platform helpers.

## Primary v1 API Reference

This is the recommended Platform Alpha API surface for new CLI, SDK, and Web
work. It is intentionally smaller than the full mounted FastAPI app. Exhaustive
schemas remain available through `GET /openapi.json`; this section documents
the current user-path contract and the feature flags that affect it.

Every primary v1 endpoint accepts the optional `Authorization: Bearer
<DOGE_API_TOKEN>` header when `DOGE_API_TOKEN` is configured, and optional
`X-Request-ID` for traceability. Error responses use the standard envelope in
[Error Contract](http-api-contracts.md#error-contract), except FastAPI request-validation **422**
responses which retain the framework `{"detail": [...]}` shape.

### sessions

Owns local multi-turn research context. SDK mapping: `client.sessions`.

- `POST /v1/sessions`
  - Body: `{"title": "Research session"}`; `title` is optional.
  - Response **200**: serialized `AgentSession` including `session_id`,
    `title`, timestamps, and turns.
  - Common errors: **401** when `DOGE_API_TOKEN` is configured and the bearer
    token is missing or invalid.
- `GET /v1/sessions`
  - Query: `limit: int = 20`.
  - Response **200**: `{"sessions": [AgentSession, ...]}` ordered by recent
    persisted sessions.
- `GET /v1/sessions/{session_id}`
  - Response **200**: one serialized session with turns.
  - Common errors: **404** `"session not found"`.
- `POST /v1/sessions/{session_id}/turns`
  - Headers: optional `Idempotency-Key`.
  - Body: `{"message": str, "market": "us", "language": "en",
    "document_ids": [], "portfolio_id": null, "model_policy": {}}`.
  - Response **202**: `{"status": "accepted", "run_id": "run-..."}`. The run
    executes through the daemon worker and persisted runtime.
  - Common errors: **404** `"session not found"`; **403** when enterprise
    policy denies the turn.

### runs

Owns run status, trace/events, approval continuation, artifacts, and optional
summary/citation/eval reads. SDK mapping: `client.runs`.

- `GET /v1/runs`
  - Query: `limit: int = 20`, optional `session_id`.
  - Response **200**: `{"runs": [RunListItem, ...]}` ordered by recent
    persisted runs. `RunListItem` includes `run_id`, `workflow`, `question`,
    session/market/language/portfolio context, `status`, event/artifact/
    approval counts, and timestamps; it intentionally omits full `events`,
    `artifacts`, and `approvals`.
- `GET /v1/runs/{run_id}`
  - Response **200**: serialized `AgentRun` with status, session/document
    context, events, approvals, and artifacts.
  - Common errors: **404** `"run not found"`.
- `POST /v1/runs/{run_id}/cancel`
  - Body: none.
  - Response **202**: serialized run/cancel result with status such as
    `cancelling`, `cancelled`, or terminal status if already completed.
- `GET /v1/runs/{run_id}/events`
  - Query: `after_sequence: int = 0`.
  - Response **200**: `{"events": [AgentEvent, ...]}` with monotonic per-run
    `sequence`.
- `GET /v1/runs/{run_id}/stream`
  - Headers: optional `Last-Event-ID` for replay.
  - Response **200**: `text/event-stream`; historical events are replayed,
    then live events are forwarded while connected.
- `GET /v1/runs/{run_id}/artifacts`
  - Response **200**: `{"artifacts": [AgentArtifact, ...]}`.
- `GET /v1/runs/{run_id}/approvals`
  - Response **200**: `{"approvals": [AgentApproval, ...]}`.
  - `AgentApproval` fields: `approval_id`, `action`, `risk_level`, `run_id`,
    `status`, `created_at`, `resolved_at`, plus optional explanation fields
    `why_needed`, `impact`, `deny_consequence`, and `publish_target`.
    Empty explanation fields mean no explanation was supplied.
- `POST /v1/runs/{run_id}/approvals/{approval_id}`
  - Body: `{"approved": true}`.
  - Response **202**: serialized run after the approval is resolved and a
    continuation is queued.
  - Common errors: **403** for governance denial; **404** for unknown run or
    approval.
- `POST /v1/runs/{run_id}/resume`
  - Body: `{"approval_id": "appr-...", "approved": true}` or `{}` for an
    already resumable run.
  - Response **202**: serialized run after explicit resume handling.
  - Common errors: **409** when the run is awaiting approval but no approval
    resolution was supplied, or when the run is terminal.
- Feature-flagged run summary reads:
  - `GET /v1/runs/{run_id}/summary`
  - `GET /v1/runs/{run_id}/claims`
  - `GET /v1/runs/{run_id}/citations`
  - `GET /v1/runs/{run_id}/eval`
  - Required flag: `DOGE_FEATURE_RUN_SUMMARY_API=1`; disabled endpoints return
    **404**.
  - `GET /claims` preserves the existing claim fields and additively returns
    `status`, `evidence_refs`, `numeric_check_status`, and `risk_level` for B3
    Phase 1 structured-claim consumers.

Approval explanation metadata is additive under ADR-0029. It gives operators
and SDK consumers approval context without changing approval resolution,
entitlement checks, run continuation, or the external-gate posture.

Structured claim metadata is additive under ADR-0030. It makes memo conclusions
machine-readable for a future conclusion-evidence matrix without changing the
runtime maturity posture or closing external/operator gates.

### documents

Owns local document registration/upload for runtime context. SDK mapping:
`client.documents`.

- `POST /v1/documents`
  - Multipart body: field `file` for real uploads.
  - JSON compatibility body: `{"filename": str, "content": str,
    "document_id": "optional"}`.
  - Response **200**: document metadata including `document_id`, filename,
    hash, MIME type, storage path, parser status, optional `kimi_file_id`,
    content, and timestamps.
  - Common errors: **400** for unsupported/empty/malformed uploads; **413**
    for oversized uploads.
- `GET /v1/documents`
  - Query: `limit: int = 100`.
  - Response **200**: `{"documents": [document metadata, ...]}` filtered by
    enterprise ACL when enterprise context is active.
- `GET /v1/documents/{document_id}`
  - Response **200**: one persisted document metadata record.
  - Common errors: **404** `"document not found"`; **403** when enterprise ACL
    denies access.

### tools

Owns API-level function-tool discovery. This is a primary `/v1` API family, but
there is no first-class Python or TypeScript SDK `tools` resource in Sprint I;
SDK clients should use capability discovery/docs for tool availability.

- `GET /v1/tools`
  - Response **200**: `{"tools": [schema, ...]}` where each schema is OpenAI
    function-tool compatible:
    - `type: "function"`
    - `function.name`
    - `function.description`
    - `function.parameters`
    - `x-doge-category`
    - `x-doge-status`
    - `x-doge-metadata.provider`
    - `x-doge-metadata.method_name`
  - Enterprise requests may receive a filtered list when tool entitlements or
    ACLs deny specific categories.
  - Common errors: **401** when local API token enforcement is enabled.

### platform

Owns workspace/project/case/template/capability helper flows for business
platform integration. SDK mapping: `client.platform` and
`client.capabilities`. The deep endpoint set is feature-flagged and remains
Platform Alpha/Level 3 Experimental.

- Workspace/project/case routes
  - Paths: `GET/POST /v1/workspaces`, `GET /v1/workspaces/{workspace_id}`,
    `GET/POST /v1/projects`, `GET /v1/projects/{project_id}`,
    `GET/POST /v1/research-cases`, and
    `GET /v1/research-cases/{case_id}`.
  - Required flag: `DOGE_FEATURE_PLATFORM_OBJECTS=1`; disabled endpoints
    return **404** `"platform objects API disabled"`.
  - Responses: serialized workspace, project, or research-case records, or
    collection envelopes such as `{"workspaces": [...]}`.
- Case assets, decisions, executions, review, progress, and home queue
  - Paths: `/v1/home-queue`,
    `/v1/research-cases/{case_id}/assets`,
    `/v1/research-cases/{case_id}/decisions`,
    `/v1/research-cases/{case_id}/executions/preflight`,
    `/v1/research-cases/{case_id}/executions`, and
    `/v1/research-cases/{case_id}/review`,
    `/v1/research-cases/{case_id}/progress`.
  - Required flag: `DOGE_FEATURE_PLATFORM_OBJECTS=1`; execution helpers may
    also depend on capability and run-summary flags for richer validation.
- Workflow templates
  - Paths: `GET/POST /v1/workflow-templates` and
    `GET /v1/workflow-templates/{template_id}`.
  - Required flag: `DOGE_FEATURE_WORKFLOW_TEMPLATES=1`; disabled endpoints
    return **404** `"workflow templates API disabled"`.
- Capabilities
  - Path: `GET /v1/capabilities`.
  - Required flag: `DOGE_FEATURE_CAPABILITY_REGISTRY=1`; disabled endpoint
    returns **404** `"capability registry API disabled"`.
  - Response **200**: redacted snapshot containing `snapshot_id`,
    `redaction_version`, `generated_at`, and `capabilities`.

## Legacy API Reference

> **⚠ Not for new work.** The `/api/*` surface is retained for local
> compatibility only and emits deprecation metadata (`Deprecation: true`,
> `Sunset: Wed, 30 Sep 2026`, `X-DOGE-Compatibility-Surface: legacy-api`). Per
> [ADR-0024](../architecture/adr-0024-single-stack-runtime-direction.md), new
> platform work must target `/v1/*` through the daemon gateway and SDK clients.
> Do not add new platform features to these routers.

All request bodies are `application/json`. Path and query params are validated
by FastAPI/Pydantic at the boundary. Every error response uses the documented
`{"error": {"code", "message"}}` envelope — see [Error Contract](http-api-contracts.md#error-contract).

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
`{progress, message}` events (see [SSE Contract](http-api-contracts.md#sse-contract)).

- `{market}` must be `cn` or `us`, else **400** `"market must be 'cn' or 'us'"`
  (`scan.py:154-155`).
- A second concurrent scan for the same market returns **409**
  `"{market} scan already running"` (`scan.py:157-158`) — see
  [Concurrency](http-api-contracts.md#concurrency).
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
[Error Contract](http-api-contracts.md#error-contract)) — no `str(e)` leak.
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
stream of `{progress, message}` events (see [SSE Contract](http-api-contracts.md#sse-contract)). The
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

The legacy Research Copilot endpoints expose the interview-demo agent workflow.
The runtime stores run state in memory for this compatibility demo and returns
operator-safe 404 errors when a run or approval id is unknown. New daemon,
SDK, and platform integrations should use `/v1/sessions`, `/v1/runs`, and the
SDK clients backed by persisted runtime state.

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
Returns `{"approvals": [...]}`. Approval objects may include the additive
ADR-0029 explanation fields `why_needed`, `impact`, `deny_consequence`, and
`publish_target` when the producer supplied them.

#### `POST /api/agent/runs/{run_id}/approvals/{approval_id}` — `agent.py`
Body: `{"approved": true|false}`. This legacy endpoint does not continue the
run; known runs return **409** with guidance to use the daemon `/v1` API. Unknown
run id → **404**.

### documents router

#### `POST /api/documents` — `documents.py`
Registers a demo document payload without multipart requirements. Body:
`{"filename": "annual-report.pdf", "content": "..."}`. Returns a deterministic
document id and metadata.

## Operator/Reference API Appendix

These routes remain mounted for local operations, diagnostics, governance
inspection, and compatibility workflows. They are not the primary user path and
are not promoted as SDK-first resources in Sprint I. See the route table above
for the canonical method/path enumeration and `GET /openapi.json` for exhaustive
schemas.

### health

- `GET /health` reports daemon liveness.
- `GET /health/ready` reports database, migration, queue, worker, outbox,
  document storage, and model-provider readiness.
- `GET /api/health` is a legacy liveness helper under the compatibility
  `/api/*` surface.
- Health routes are intended for local operator checks and daemon startup
  verification, not for research workflow orchestration.

### portfolios

- `POST /v1/portfolios/import` imports a UTF-8 CSV portfolio into local
  persisted holdings and returns an additive `summary` with holdings count,
  concentration, sector exposure, unit-price gaps, and a suggested portfolio
  risk review run.
- This route is useful for operator seeding and local workflow setup. It is not
  a primary SDK resource in Sprint I and does not imply portfolio management
  platform maturity.

### audit

- `GET /v1/audit/events` lists tenant-scoped audit events.
- `GET /v1/audit/events/export` exports redacted JSONL audit records.
- `POST /v1/audit/events/retention` purges expired events by retention policy.
- Audit routes are operator/reference APIs for governance evidence and local
  inspection. They do not close production SIEM/WORM evidence gates.

### enterprise

- `GET /v1/enterprise/acl/grants` lists tenant ACL grants for enterprise admins.
- `POST /v1/enterprise/acl/grants` creates a tenant ACL grant.
- `DELETE /v1/enterprise/acl/grants` revokes a tenant ACL grant.
- Enterprise ACL routes are alpha governance surfaces. They do not by
  themselves prove production SSO, tenant isolation, or remote deployment
  readiness.
