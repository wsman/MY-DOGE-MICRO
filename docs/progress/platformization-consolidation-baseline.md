# Platformization Consolidation Baseline

> Date: 2026-06-23
> Source plan: `C:\Users\Aby\.claude\plans\d91dc3b-python-typescript-sdk-federated-bird.md`
> Phase: 0 — Baseline Compatibility Snapshot
> Status: Captured

## Purpose

This document freezes the current observable behavior before bounded-context
consolidation, facade-package work, provider-only tool execution, RuntimeKernel
decomposition, platform-service extraction, or web navigation consolidation.

It is a compatibility baseline, not production-readiness evidence.
`docs/progress/runtime-maturity.yaml` remains authoritative:

- `production_ready: false`
- `stable_declaration: forbidden`
- Level 3 SDK/platform posture: `experimental`

## Current Worktree Note

At capture time, `git status --short` reported existing unrelated web config
changes:

```text
 M web/tsconfig.app.json
 M web/vite.config.ts
```

This baseline does not modify those files.

## API Route Baseline

Canonical router wiring is in `src/doge/interfaces/api/main.py`.

### Legacy Local API

| Prefix | Router | Notes |
|--------|--------|-------|
| `/api/scan` | `scan.router` | Scanner server/status/market scan routes. |
| `/api/data` | `data.router` | Market table, ticker kline, and ticker-name routes. |
| `/api/notes` | `notes.router` | Ticker notes, search, recent, tracked, delete. |
| `/api/macro` | `macro.router` | Macro report list/latest/detail/run. |
| `/api/analysis` | `analysis.router` | Analysis report list/detail. |
| `/api/config` | `config.router` | Settings and TDX validation. |
| `/api/agent` | `agent.router` | Legacy research-agent run/event/stream/artifact/approval routes. |
| `/api/documents` | `documents.router` | Legacy document upload. |
| `/api/health` | `main.health` | Returns `{"status": "ok"}`. |
| `/api/stats` | `main.stats` | Schema-browser database stats. |

### v1 Runtime and Platform API

All routes below are mounted under `/v1` unless noted.

| Route | Response Shape / Behavior | Feature Gate |
|-------|---------------------------|--------------|
| `POST /sessions` | Session object. | None |
| `GET /sessions` | `{"sessions": [...]}`. | None |
| `GET /sessions/{session_id}` | Session object. | None |
| `POST /sessions/{session_id}/turns` | Accepted run/turn response. | None |
| `GET /runs/{run_id}` | Run object. | None |
| `POST /runs/{run_id}/cancel` | Cancelled/queued run object from worker. | None |
| `GET /runs/{run_id}/events` | `{"events": [...]}` filtered by `after_sequence`. | None |
| `GET /runs/{run_id}/stream` | SSE; replays events after `Last-Event-ID`. | None |
| `GET /runs/{run_id}/artifacts` | `{"artifacts": [...]}`. | None |
| `GET /runs/{run_id}/summary` | `{"summary": {...}}`. | `DOGE_FEATURE_RUN_SUMMARY_API` |
| `GET /runs/{run_id}/claims` | `{"summary_id": "...", "claims": [...]}`. | `DOGE_FEATURE_RUN_SUMMARY_API` |
| `GET /runs/{run_id}/citations` | `{"summary_id": "...", "citations": [...]}`. | `DOGE_FEATURE_RUN_SUMMARY_API` |
| `GET /runs/{run_id}/eval` | `{"summary_id": "...", "eval": {...}}`. | `DOGE_FEATURE_RUN_SUMMARY_API` |
| `GET /runs/{run_id}/approvals` | `{"approvals": [...]}`. | None |
| `POST /runs/{run_id}/approvals/{approval_id}` | Run object after approval resolution. | None |
| `POST /documents` | Document object. | None |
| `GET /documents` | `{"documents": [...]}`. | None |
| `GET /documents/{document_id}` | Document object. | None |
| `POST /portfolios/import` | Portfolio import response. | None |
| `GET /tools` | Tool schema list. | None |
| `GET /audit/events` | Tenant-scoped audit events. | Enterprise auth context |
| `GET /audit/events/export` | Redacted JSONL export with integrity headers. | Enterprise auth context |
| `POST /audit/events/retention` | Audit retention purge result. | Enterprise auth context |
| `GET /enterprise/acl/grants` | `{"grants": [...]}`. | Enterprise admin role |
| `POST /enterprise/acl/grants` | Created ACL grant. | Enterprise admin role |
| `DELETE /enterprise/acl/grants` | Revoke response. | Enterprise admin role |
| `/health` and `/health/ready` | Health/readiness responses, mounted without `/v1`. | None |

### v1 Platform Objects

`src/doge/interfaces/api/routers/v1/platform.py` currently performs repository,
runtime, ACL, audit, and feature-flag orchestration inline.

| Route | Response Shape / Behavior | Feature Gate |
|-------|---------------------------|--------------|
| `GET /capabilities` | Redacted capability snapshot with `snapshot_id` and `capabilities`. | `DOGE_FEATURE_CAPABILITY_REGISTRY` |
| `GET /workspaces` | `{"workspaces": [...]}`. | `DOGE_FEATURE_PLATFORM_OBJECTS` |
| `POST /workspaces` | Workspace object; grants creator access and audits `workspace_create`. | `DOGE_FEATURE_PLATFORM_OBJECTS` |
| `GET /workspaces/{workspace_id}` | Workspace object. | `DOGE_FEATURE_PLATFORM_OBJECTS` |
| `GET /projects` | `{"projects": [...]}` with optional `workspace_id`. | `DOGE_FEATURE_PLATFORM_OBJECTS` |
| `POST /projects` | Project object; validates workspace read access. | `DOGE_FEATURE_PLATFORM_OBJECTS` |
| `GET /projects/{project_id}` | Project object. | `DOGE_FEATURE_PLATFORM_OBJECTS` |
| `GET /research-cases` | `{"research_cases": [...]}` with optional `project_id`. | `DOGE_FEATURE_PLATFORM_OBJECTS` |
| `POST /research-cases` | Research case object; validates project read access. | `DOGE_FEATURE_PLATFORM_OBJECTS` |
| `GET /research-cases/{case_id}` | Research case object. | `DOGE_FEATURE_PLATFORM_OBJECTS` |
| `POST /research-cases/{case_id}/runs` with `run_id` | Case-run link object. | `DOGE_FEATURE_PLATFORM_OBJECTS` |
| `POST /research-cases/{case_id}/runs` with `template_id` | Case-run link plus `template_id` and `template_slug`. | `DOGE_FEATURE_PLATFORM_OBJECTS` + `DOGE_FEATURE_WORKFLOW_TEMPLATES` |
| `GET /workflow-templates` | `{"workflow_templates": [...]}`. | `DOGE_FEATURE_WORKFLOW_TEMPLATES` |
| `POST /workflow-templates` | Workflow template object. | `DOGE_FEATURE_WORKFLOW_TEMPLATES` |
| `GET /workflow-templates/{template_id}` | Workflow template object. | `DOGE_FEATURE_WORKFLOW_TEMPLATES` |

Feature-disabled platform routes currently return 404 with details such as
`platform objects API disabled`, `workflow templates API disabled`,
`capability registry API disabled`, or `run summary API disabled`.

## Web Route Baseline

`web/src/router/index.ts` preserves both legacy and platform routes.

| Route | Name | Notes |
|-------|------|-------|
| `/` | redirect | Current post-defaultization behavior redirects to `/home`; `VITE_DOGE_FEATURE_PLATFORM_SHELL=0` rolls back to `/research-agent`. Baseline-era behavior was opt-in platform routing. |
| `/scanner` | `scanner` | Legacy market scanner. |
| `/cn-archive` | `cn-archive` | Legacy CN archive. |
| `/us-archive` | `us-archive` | Legacy US archive. |
| `/insights` | `insights` | Legacy insights. |
| `/analysis` | `analysis` | Legacy analysis. |
| `/research-agent` | `research-agent` | Must remain directly reachable per ADR-0020. |
| `/workspaces` | `workspace-list` | Platform shell route. |
| `/workspaces/:workspaceId` | `workspace-detail` | Platform shell route. |
| `/projects/:projectId` | `project-detail` | Platform shell route. |
| `/cases/:caseId` | `case-detail` | Platform shell route. |
| `/templates` | `template-center` | Platform shell route. |
| `/runs/:runId?` | `run-detail` | Platform shell route. |
| `/admin` | `admin-center` | Platform shell route. |

When `platformShellEnabled` is false, navigation guards redirect platform route
names to `/research-agent`.

## SDK Public Surface Baseline

### Python SDK

`packages/doge-sdk-python/doge_sdk/client.py` exposes:

- `DogeClient`
- `AsyncDogeClient`
- `sessions.create/list/get/create_turn`
- `runs.get/summary/claims/citations/evaluation/events/stream/approve/cancel`
- `documents.create/list/get`
- `platform.list_workspaces/create_workspace/get_workspace`
- `platform.list_projects/create_project/get_project`
- `platform.list_research_cases/create_research_case/get_research_case`
- `platform.link_research_case_run`
- `platform.create_research_case_run_from_template`
- `platform.list_workflow_templates/create_workflow_template/get_workflow_template`
- `capabilities.get/list`

Auth/request behavior:

- `Authorization: Bearer ...` is sent when `api_token` is configured.
- `X-Request-ID` is sent when `request_id` is configured.
- SSE stream replay uses `Last-Event-ID`.
- API and SSE errors redact bearer tokens, key-value API secrets, and
  provider-shaped secret values.

### TypeScript SDK

`packages/doge-sdk-typescript/src/client.ts` exposes:

- `DogeClient`
- `SessionsResource`
- `RunsResource`
- `DocumentsResource`
- `PlatformResource`
- `CapabilitiesResource`

Observed contract tests cover:

- session creation and turns
- run summary/claims/citations/eval
- run SSE stream reconnect using `Last-Event-ID`
- mid-stream drop recovery
- platform object and workflow-template helpers
- bearer/request-id pass-through
- secret redaction in JSON and SSE errors

The TypeScript package build currently emits ESM with `.js` relative
specifier imports.

## Runtime Baseline

`RuntimeKernel` public methods:

- `create_run`
- `run_to_pause_or_completion`
- `queue_run`
- `step`
- `resolve_approval`
- `cancel_run`
- `finalize_cancelled`
- `get_run`
- `list_events`
- `list_runs`
- `list_artifacts`

Run statuses from `RunStatus`:

- `created`
- `queued`
- `running`
- `awaiting_approval`
- `cancelling`
- `cancelled`
- `completed`
- `failed`

Event types from `EventType`:

- `run_created`
- `run_queued`
- `model_response`
- `tool_call`
- `tool_result`
- `approval_requested`
- `approval_resolved`
- `artifact_created`
- `run_cancelled`
- `error`

SSE stream close statuses:

- `awaiting_approval`
- `completed`
- `failed`
- `cancelled`

SSE terminal/close event names:

- `approval_requested`
- `artifact_created`
- `error`
- `run_cancelled`

Current RuntimeKernel responsibilities include state-machine coordination,
context/web-search handling, model routing, tool schema filtering, tool
execution, ACL checks, audit emission, budget checks, approval handling,
artifact creation, and eval metric assembly.

## Audit Event Baseline

Platform and run-summary routes currently emit:

- `capability_list`
- `workspace_list`
- `workspace_create`
- `workspace_read`
- `project_list`
- `project_create`
- `project_read`
- `research_case_list`
- `research_case_create`
- `research_case_read`
- `research_case_run_link`
- `research_case_run_create`
- `workflow_template_list`
- `workflow_template_create`
- `workflow_template_read`
- `run_summary_read`
- `run_claims_read`
- `run_citations_read`
- `run_eval_read`

RuntimeKernel currently emits governance audit actions:

- `model_route`
- `tool_execute`
- `tool_denied`

Enterprise access helpers also emit ACL/authorization-denial audit events for
access failures and creator grants where applicable.

## Feature Flag Baseline

Backend feature flags are defined by `FeatureConfig` in
`src/doge/config/settings.py`:

| Setting | Env Var | Default |
|---------|---------|---------|
| `settings.features.run_summary_api` | `DOGE_FEATURE_RUN_SUMMARY_API` | `false` |
| `settings.features.platform_objects` | `DOGE_FEATURE_PLATFORM_OBJECTS` | `false` |
| `settings.features.workflow_templates` | `DOGE_FEATURE_WORKFLOW_TEMPLATES` | `false` |
| `settings.features.capability_registry` | `DOGE_FEATURE_CAPABILITY_REGISTRY` | `false` |

Frontend feature flag:

| Setting | Env Var | Default |
|---------|---------|---------|
| `platformShellEnabled` | `VITE_DOGE_FEATURE_PLATFORM_SHELL` | default-on for unset/empty values; explicit `0`, `false`, or `off` disables |

## Governance Baseline

- ADR-0012 through ADR-0014 are Accepted.
- ADR-0015 through ADR-0020 remain Proposed.
- `docs/archive/audits/adr-0016-0020-disposition-review-2026-06-23.md` records
  Keep Proposed for ADR-0016 through ADR-0020.
- `docs/architecture/tr-registry.yaml` uses a flat project-wide `TR-001`
  numbering stream.
- Existing TR-059 through TR-070 cover current platformization slices.
- `design/cdd/module-index.md` still enumerates 20 mixed modules and 0 approved
  CDDs at this baseline point.
- External release/production gates remain outside this consolidation plan:
  live Kimi, financial provider approval, analyst benchmark, enterprise
  production validation, and SDK registry publication.

## Verification Commands

All Phase 0 verification commands passed on 2026-06-23.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/contract/test_v1_api.py tests/contract/test_platform_api.py tests/contract/test_agent_router.py tests/contract/test_python_sdk.py -q
```

Result:

```text
32 passed in 10.30s
```

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/agent/test_runtime_kernel.py tests/unit/agent/test_tool_service.py tests/unit/agent/test_tool_registry.py -q
```

Result:

```text
36 passed in 9.19s
```

Initial TypeScript/Web commands failed when `npm` could not find `node` through
the process `PATH`. Re-running with the known temporary Node directory prepended
to `PATH` succeeded:

```powershell
$env:PATH='C:\Users\Aby\AppData\Local\Temp\codex-node-v24.17.0\node-v24.17.0-win-x64;' + $env:PATH
npm test
```

from `packages/doge-sdk-typescript`:

```text
1 file passed, 13 tests passed
```

```powershell
$env:PATH='C:\Users\Aby\AppData\Local\Temp\codex-node-v24.17.0\node-v24.17.0-win-x64;' + $env:PATH
npm run build
```

from `packages/doge-sdk-typescript`: passed.

```powershell
$env:PATH='C:\Users\Aby\AppData\Local\Temp\codex-node-v24.17.0\node-v24.17.0-win-x64;' + $env:PATH
npm test -- --run
```

from `web`:

```text
13 files passed, 81 tests passed
```

```powershell
$env:PATH='C:\Users\Aby\AppData\Local\Temp\codex-node-v24.17.0\node-v24.17.0-win-x64;' + $env:PATH
npm run build
```

from `web`: passed.

## Phase 0 Exit Criteria

- Baseline document exists: satisfied by this file.
- Verification commands and results are recorded: satisfied.
- Existing failing tests recorded: none in the required Phase 0 command set.
- Architecture refactor may proceed only after this baseline is accepted for
  Phase A work.
