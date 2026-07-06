# ADR-0036: Run List And Comparison

## Status

Accepted

## Date

2026-07-05

## Decision Makers

wsman (product owner) · Codex implementation agent

## Summary

Sprint 027 implements the B6 run comparison item from
`C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md`.

The key decision is to expose a compact persisted-run list through the existing
daemon run boundary and SDK resources, then render it as a lightweight Web
comparison panel. The new list endpoint returns counts and metadata only; it
does not duplicate full run events, artifacts, approvals, summaries, or memo
content.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10; FastAPI 0.123.8; Pydantic 2.12.4; TypeScript ~6.0.2; Vue 3.5.32; Naive UI 2.44.1 |
| **Domain** | API Design / SDK / Frontend |
| **Knowledge Risk** | LOW - uses existing FastAPI router, runtime `list_runs`, SDK client, and Vue component patterns |
| **References Consulted** | `docs/reference/python/VERSION.md`, `design/cdd/fastapi-service.md`, `docs/reference/http-api.md`, `docs/registry/entities.yaml`, `packages/doge-sdk-python/README.md`, `packages/doge-sdk-typescript/README.md`, `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Focused v1 contract, Python SDK, TypeScript SDK, Web component/view tests, SDK contract parity, route coverage, governance docs tests, docs/maturity validators, plan closure gate |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0024 (Single Stack Runtime Direction), ADR-0025 (Streaming Semantics), ADR-0032 (Workspace Mode and Memo Export), ADR-0035 (Demo Pack And SDK Cookbooks) |
| **Enables** | Sprint 027 run comparison and future analyst history review flows |
| **Blocks** | None |
| **Ordering Note** | This ADR adds a compact list contract first; richer run diffing, memo comparison, and research-case timeline views require separate design. |

## Context

### Problem Statement

The Web workspace can inspect a single run, stream events, view artifacts, and
export memo evidence, but it cannot show nearby historical runs for comparison.
B6 asked for run-retention comparison with a gateway endpoint and UI affordance.

### Constraints

- Preserve the current local maturity posture: `production_ready: false`,
  `stable_declaration: forbidden`, and Level 3 `experimental`.
- Use persisted runtime state already owned by the agent runtime boundary.
- Keep the list response compact to avoid returning duplicated trace/artifact
  payloads in a history panel.
- Keep `/v1/runs/{run_id}` as the full run read contract.
- Maintain SDK contract parity for new OpenAPI response entities.
- Do not close external/operator gates or claim production readiness.

### Requirements

- Add `GET /v1/runs` with `limit` and optional `session_id`.
- Return `{"runs": [RunListItem, ...]}` with run metadata and event/artifact/
  approval counts.
- Add Python and TypeScript SDK list helpers.
- Render recent runs in the Web Research Agent quality pane.
- Highlight the current run when it appears in the list.
- Keep route registries, API docs, and governance tests synchronized.

## Decision

Add `RunListItemResponse` and `RunListResponse` Pydantic models to the gateway
response-model file and expose `GET /v1/runs` from the existing v1 run router.
The route calls the persisted runtime's existing `list_runs(scope, session_id,
limit)` method and maps each run to a compact row:

```text
GET /v1/runs?limit=20&session_id=ses-...
  -> persisted runtime list_runs(...)
  -> RunListItemResponse[]
```

Python SDK:

```python
client.runs.list(limit=20, session_id=None)
```

TypeScript SDK:

```typescript
client.runs.list({ limit: 20, sessionId: 'ses-...' })
```

The Web API wrapper exposes `listAgentRuns(limit)` and
`RunComparisonPanel.vue` renders recent rows in the Research Agent quality pane.
It uses the existing status label/tone helper and does not introduce new run
status values.

### Architecture Diagram

```text
ResearchAgentView
  -> RunComparisonPanel
    -> web api listAgentRuns()
      -> TypeScript SDK client.runs.list()
        -> GET /v1/runs
          -> persisted runtime list_runs()
```

### Key Interfaces

```http
GET /v1/runs?limit=20&session_id=ses-...
```

```json
{
  "runs": [
    {
      "run_id": "run-...",
      "workflow": "investment_research",
      "question": "Analyze ...",
      "session_id": "ses-...",
      "market": "us",
      "language": "en",
      "portfolio_id": null,
      "status": "completed",
      "event_count": 12,
      "artifact_count": 2,
      "approval_count": 0,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

## Alternatives Considered

### Alternative 1: Reuse `GET /v1/sessions` for comparison

- **Description**: Expand session list rows with latest run data.
- **Pros**: No new route.
- **Cons**: Mixes session and run ownership; cannot filter directly by run
  history; weak SDK ergonomics.
- **Rejection Reason**: B6 is a run comparison feature, and the runtime already
  owns a run list method.

### Alternative 2: Return full `AgentRun` rows from list

- **Description**: `GET /v1/runs` returns full run objects.
- **Pros**: No separate compact schema.
- **Cons**: Heavy payloads, duplicated event/artifact arrays, and higher UI
  rendering risk.
- **Rejection Reason**: The comparison panel only needs metadata and counts.

### Alternative 3: Web-only local cache comparison

- **Description**: Compare only runs seen during the current browser session.
- **Pros**: No backend or SDK change.
- **Cons**: Does not use persisted run retention and loses history on reload.
- **Rejection Reason**: B6 explicitly calls for a retained comparison surface.

## Consequences

### Positive

- Web users can compare the current run against recent persisted runs.
- SDK consumers gain a compact history primitive without loading full traces.
- OpenAPI and TypeScript SDK parity now cover `RunListItemResponse`.
- API route authority includes the compact run-list route.

### Negative

- Route count and registry governance had to include the new compact run-list route.
- The initial UI is a compact list, not a semantic diff.
- The list does not yet expose pagination cursors beyond `limit`.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| History payload grows too large | LOW | MEDIUM | Default `limit=20`; Web panel requests 8 rows and uses compact counts. |
| Users expect memo-level diffing | MEDIUM | LOW | Document this sprint as compact comparison only; defer richer diffing. |
| SDK parity drifts | LOW | MEDIUM | SDK contract check includes route surface and `RunListItemResponse` parity. |

## CDD Requirements Addressed

| CDD Document | Requirement | How This ADR Addresses It |
|--------------|-------------|----------------------------|
| `design/cdd/fastapi-service.md` | `/v1/*` daemon routes must stay documented and route-covered. | Adds `GET /v1/runs`, updates route authority, and keeps route coverage tests aligned. |
| `design/cdd/bc-06-agent-runtime.md` | Agent runtime state should expose recoverable sessions, runs, events, approvals, and artifacts. | Uses persisted runtime `list_runs` to expose recoverable run history. |
| `design/cdd/sprint-ux-5-workspace-modes-and-export.md` | Analyst mode should emphasize reviewable outputs while diagnostics remain controlled. | Places recent run comparison in the quality pane without expanding developer diagnostics. |

## Performance Implications

- **CPU**: Small serialization pass over at most `limit` runs.
- **Memory**: Bounded by compact list rows.
- **Load Time**: One additional Web panel request on Research Agent mount.
- **Network**: Compact JSON; no event/artifact payload arrays.

## Migration Plan

1. Add compact run-list response models.
2. Add `GET /v1/runs` before the dynamic `/v1/runs/{run_id}` route.
3. Add Python and TypeScript SDK list helpers.
4. Add Web API wrapper and `RunComparisonPanel`.
5. Update API docs, route registries, SDK docs, and route-count tests.
6. Record Sprint 027 CDD, sprint record, and evidence manifest.

## Validation Criteria

- `GET /v1/runs` returns compact rows and omits full event/artifact arrays.
- Python SDK builds the correct list request.
- TypeScript SDK builds the correct list request and exports `RunListItem`.
- Web comparison panel renders compact rows and highlights the current run.
- `ResearchAgentView` mounts with the comparison panel mock path intact.
- SDK contract check includes the compact run-list route and response type.
- API doc route coverage and S017 planning docs tests pass with the compact run-list route represented.

## Related Decisions

- ADR-0024: Single Stack Runtime Direction
- ADR-0025: Runtime Streaming Semantics
- ADR-0032: Workspace Mode and Memo Export
- ADR-0035: Demo Pack And SDK Cookbooks
