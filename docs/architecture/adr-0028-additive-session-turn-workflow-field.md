# ADR-0028: Additive Optional `workflow` field on the session-turn request

## Status

Accepted

## Date

2026-07-05

## Last Verified

2026-07-04

## Decision Makers

wsman (product owner) · Claude implementation agent

## Summary

The session-turn request path hard-codes `'investment_research'` as the run
workflow in its four upper layers, so the Web ScenarioPicker cannot drive a
different shipped template. This ADR records an additive, backward-compatible
optional `workflow` request field on `POST /v1/sessions/{session_id}/turns`
threaded through the turn handler, worker, and execute-run use case — the two
lower persistence layers already accept `workflow`.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10, FastAPI 0.123.8, Pydantic 2.12.4, SQLite local persistence; TypeScript SDK + Vue 3 web client |
| **Domain** | API Design / Agent Runtime / SDK |
| **Knowledge Risk** | LOW — additive optional Pydantic field on a pinned FastAPI/Pydantic stack; lower layers already accept the param |
| **References Consulted** | `docs/reference/python/VERSION.md`, `design/cdd/sprint-ux-1-first-run-coherence.md`, `docs/architecture/adr-0007-api-surface-and-cors.md`, `docs/architecture/adr-0011-agent-runtime-levels.md`, `docs/architecture/adr-0018-workflow-template-system.md`, `standards/coding-standards.md`, `docs/progress/runtime-maturity.yaml` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Contract test asserting turn-body `workflow` field parity; default-preserves-current-behavior test; non-default workflow persistence test; `tools/ci/sdk-contract-check.py` extended for turn-body field |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0007 (API surface contract), ADR-0011 (agent runtime levels), ADR-0018 (workflow template system) |
| **Enables** | Sprint UX-1 Slice I + Slice G (ScenarioPicker drives the workflow); future per-template runs from SDK/Web |
| **Blocks** | None (decision is Accepted; implementation proceeds slice-by-slice under the UX-1 CDD) |
| **Ordering Note** | Slice I (backend threading + contract test) must merge before Slice G (frontend ScenarioPicker) can satisfy its acceptance criterion. The `/v1/runs/{id}/quality` and `/v1/runs/{id}/export` additives planned for UX-2/UX-3 are governed by a separate consolidated ADR, not this one. |

## Context

### Problem Statement

Sprint UX-1 must let a Web operator pick one of the four shipped scenario
templates (`daily_market_brief`, `earnings_review`, `portfolio_risk_review`,
`investment_committee_memo` from `src/doge/platform/workspace/template_seed.py`)
and have that choice drive the run actually created. Today the Web
`createAgentRun()` declares a `workflow` field on its request interface but
drops it, and the daemon turn path re-hard-codes `'investment_research'` in
multiple upper layers, so the picker cannot influence the persisted run.

### Current State

Verified against the working tree at `a2f616b` (2026-07-04):

- `CreateTurnRequest` (`src/doge/interfaces/gateway/routers/sessions.py:31-37`)
  — Pydantic body; no `workflow` field. FastAPI auto-generates its OpenAPI
  schema component.
- `SubmitSessionTurnCommand` (`src/doge/interfaces/api/handlers/sessions.py:25-36`)
  — no `workflow` field; handler builds the command without it.
- `AsyncioWorker.enqueue_run` (`src/doge/application/agent/worker.py:109-121`)
  — no `workflow` param; literal `workflow="investment_research"` at `:129`
  when calling the unit of work.
- `ExecuteRun.execute` (`src/doge/application/use_cases/run_use_cases.py:20-30`)
  — no `workflow` param; literal `"workflow": "investment_research"` at `:35`
  inside the `runtime.create_run` payload.
- `IAgentUnitOfWork.enqueue_run_and_turn`
  (`src/doge/core/ports/unit_of_work.py:13-26`) — **already accepts**
  `workflow: str = "investment_research"` (`:18`).
- `SQLiteAgentUnitOfWork.enqueue_run_and_turn`
  (`src/doge/infrastructure/database/sqlite_uow.py:38-51`) — **already
  accepts** `workflow: str = "investment_research"` (`:43`).
- `AgentRun.workflow` (`src/doge/core/domain/agent_models.py:135`) — already a
  **required** `str` field with no default (unchanged by this ADR).
- Python `Session.run` (`packages/doge-sdk-python/doge_sdk/session.py:18-28`)
  and TypeScript `Session.run`
  (`packages/doge-sdk-typescript/src/session.ts:26-38`) forward unknown kwargs
  via `**kwargs` / `...rest`, so `workflow` already reaches the wire if a
  caller sets it; an explicit typed param is additive clarity only.
- Web `createAgentRun` (`web/src/api/agent.ts:30-41`) declares
  `CreateAgentRunRequest.workflow: string` but never forwards it; the
  hard-coded `'investment_research'` literal lives at
  `web/src/stores/agent.ts:27`.

### Constraints

- Runtime remains Local Alpha: `production_ready: false`,
  `stable_declaration: forbidden`, Level 1/2 Alpha, Level 3 `experimental` —
  unchanged.
- The `/v1` daemon contract must stay compatible with existing SDK and Web
  clients (additive only; no breaking change).
- API-contract work is BLOCKING and requires a schema-diff review
  (`standards/coding-standards.md`: API Contract row).
- No external gate (S017-003 / W3-live / AUTH-prod / S017-007) is closed or
  referenced as evidence.

### Requirements

- An operator-selected workflow slug must reach the persisted `AgentRun`.
- Omitting the field must reproduce today's behavior exactly
  (`'investment_research'`).
- The OpenAPI schema diff must be documented and contract-tested.
- No SDK breaking signature change; no CLI exit-code change.

## Decision

Thread an optional `workflow: str = "investment_research"` through the four
upper turn-path layers. Leave `AgentRun.workflow` and the two lower
persistence layers unchanged (they already accept `workflow`). Add an explicit
optional `workflow` kwarg to the SDK `Session.run` surfaces for typed clarity
(the kwargs/rest plumbing already forwards it). Web `createAgentRun` forwards
`payload.workflow` instead of dropping it.

### Architecture

```
Web createAgentRun (forwards payload.workflow)
  |
  v
SDK Session.run(workflow?) ----------+
  |                                   | (kwargs / rest already pass it)
  v                                   |
POST /v1/sessions/{id}/turns          |
  body: CreateTurnRequest(workflow="investment_research")   <-- additive field
  |
  v
SubmitSessionTurnCommand(workflow="investment_research")    <-- additive field
  |
  v
AsyncioWorker.enqueue_run(workflow="investment_research")    <-- additive param
  |
  v
IAgentUnitOfWork.enqueue_run_and_turn(workflow=...)         <-- already accepts
  |
  v
SQLiteAgentUnitOfWork.enqueue_run_and_turn(workflow=...)    <-- already accepts
  |
  v
ExecuteRun.execute(workflow=...) --> runtime.create_run(workflow=...)  <-- additive param, removes literal at :35
  |
  v
AgentRun.workflow (required field, unchanged)
```

### Key Interfaces

```python
# CreateTurnRequest — additive optional field
class CreateTurnRequest(BaseModel):
    message: str
    market: str = "us"
    language: str = "en"
    document_ids: list[str] = Field(default_factory=list)
    portfolio_id: str | None = None
    model_policy: dict[str, Any] = Field(default_factory=dict)
    workflow: str = "investment_research"   # ADDITIVE (ADR-0028)

# SubmitSessionTurnCommand — additive field, same default
# AsyncioWorker.enqueue_run / ExecuteRun.execute — additive keyword-only param, same default
```

```python
# SDK (Python) — explicit optional kwarg; **kwargs already forwarded it
def run(self, question, *, execution_profile="financial_research",
        model_policy=None, workflow: str | None = None, **kwargs) -> str: ...
```

```typescript
// SDK (TypeScript) — explicit optional; ...rest already forwarded it
async run(question: string, options: { execution_profile?: string,
  model_policy?: Record<string, unknown>, workflow?: string } = {}): Promise<string>
```

### Implementation Guidelines

- Every added `workflow` parameter defaults to `"investment_research"` so
  absent callers reproduce today's behavior byte-for-byte.
- Remove the two hard-coded literals (`worker.py:129`, `run_use_cases.py:35`)
  in favor of the threaded value.
- Do **not** alter `AgentRun.workflow` (already required) or the two lower
  persistence layers (already accept `workflow`).
- Extend `tools/ci/sdk-contract-check.py` to assert the turn-request body
  carries `workflow`, and add a focused contract test under `tests/contract/`
  (default preserves current behavior; non-default workflow persists).
- Update OpenAPI/SDK parity tooling only if request-body field parity is
  enforced; today only path/method and response-entity parity are checked.

## Alternatives Considered

### Alternative 1: Frontend-only (remove the Web literal, thread nothing)

- **Description**: Surface the four templates in the picker and remove the
  hard-coded `'investment_research'` literal at `stores/agent.ts:27` without
  touching the backend.
- **Pros**: Zero backend change; no ADR.
- **Cons**: Does not satisfy the requirement — `createAgentRun` already drops
  the field and the daemon re-hard-codes it, so the picker would change UI
  state but not the persisted run.
- **Estimated Effort**: Smaller, but non-functional.
- **Rejection Reason**: Hollow win; the picker must actually drive the run.

### Alternative 2: Add a default to `AgentRun.workflow`

- **Description**: Make the domain field optional with a default.
- **Pros**: Localized.
- **Cons**: Unnecessary — the field is already required and the persistence
  path already accepts `workflow`; changing the dataclass default would be a
  broader domain-model churn for no benefit.
- **Estimated Effort**: Similar, with wider blast radius.
- **Rejection Reason**: Does not address the actual gap (the upper layers).

### Alternative 3: Threading the workflow slug end-to-end (chosen)

- **Description**: Additive optional `workflow` on the request, command,
  worker, and execute-run use case; SDK explicit param; Web forwards it.
- **Pros**: Satisfies the requirement; additive and backward-compatible;
  lower layers already accept it.
- **Cons**: One OpenAPI schema diff to document and contract-test.
- **Estimated Effort**: Small, focused.
- **Rejection Reason**: Chosen.

## Consequences

### Positive

- The ScenarioPicker (and SDK callers) can drive any shipped template.
- The `'investment_research'` literal is removed from two layers, leaving the
  default in one place per layer.
- Lower layers needed no change.

### Negative

- One additive OpenAPI property on `CreateTurnRequest` requires a schema-diff
  note (this ADR) and a contract test.

### Neutral

- SDK `Session.run` gains an explicit optional `workflow` kwarg; the existing
  kwargs/rest plumbing already forwarded it, so this is typed clarity only.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| OpenAPI schema drift between server and SDK | LOW | MEDIUM | Extend `tools/ci/sdk-contract-check.py` turn-body assertion + focused contract test in Slice I |
| Unknown workflow slug silently persisted | LOW | LOW | Default `'investment_research'` is the only guaranteed value; unknown slugs are accepted today already (no validation regression) |
| Caller depends on the field being absent | LOW | LOW | Optional with default; absent callers reproduce prior behavior |

## Performance Implications

| Metric | Before | Expected After | Budget |
|--------|--------|---------------|--------|
| CPU | baseline | unchanged (one extra dict key) | n/a |
| Memory | baseline | unchanged | n/a |
| Network | baseline | +~30 bytes per turn request when set | MCP 30s latency budget unaffected |

## Migration Plan

1. Add `workflow` field/param (default `'investment_research'`) to
   `CreateTurnRequest`, `SubmitSessionTurnCommand`, `AsyncioWorker.enqueue_run`,
   `ExecuteRun.execute`; thread through the handler; remove the two literals.
2. Add explicit optional `workflow` kwarg to Python and TypeScript
   `Session.run`.
3. Web `createAgentRun` forwards `payload.workflow`; `stores/agent.ts:27`
   literal replaced by the ScenarioPicker selection (Slice G).
4. Extend `tools/ci/sdk-contract-check.py` + add the focused contract test.
5. Update docs (`docs/API.md` turn-request body; SDK READMEs).

**Rollback plan**: Revert the additive field/params and restore the two
hard-coded literals; the lower layers and `AgentRun.workflow` are untouched,
so rollback is a clean subtractive change with no data migration.

## Validation Criteria

- [x] `CreateTurnRequest` carries optional `workflow` defaulting to
  `'investment_research'`; FastAPI exposes it in `/openapi.json`.
- [x] A turn submitted without `workflow` produces a persisted `AgentRun`
  whose `workflow == 'investment_research'` (byte-for-byte current behavior).
- [x] A turn submitted with `workflow='portfolio_risk_review'` produces a
  persisted `AgentRun` whose `workflow == 'portfolio_risk_review'`.
- [x] `tools/ci/sdk-contract-check.py` asserts the turn-body `workflow` field.
- [x] No SDK breaking signature change; no CLI exit-code change.
- [x] No production-ready / stable / GA language; no external gate closed.

## CDD Requirements Addressed

| CDD Document | System | Requirement | How This ADR Satisfies It |
|-------------|--------|-------------|--------------------------|
| `design/cdd/sprint-ux-1-first-run-coherence.md` | Sprint UX-1 / ScenarioPicker (WEB-10) | Selecting one of the four shipped scenario templates must drive the workflow of the run actually created. | Threads an additive optional `workflow` through the turn path so the Web ScenarioPicker (and SDK callers) drive the persisted `AgentRun.workflow`. |
| `design/cdd/sdk-daemon-client-interfaces.md` | sdk-daemon-client-interfaces | SDK and daemon `/v1` contracts stay compatible for runtime clients. | Additive optional field with a default; existing callers unchanged. |

> TR-IDs for the new UX-1 requirements are not yet minted; they are appended by
> `/architecture-review` (TR-071+) per the tr-registry workflow. This ADR is the
> governing record until then.

## Related

- ADR-0007: API Surface and CORS (route-table contract)
- ADR-0011: Agent Runtime Levels
- ADR-0018: Workflow Template System
- `design/cdd/sprint-ux-1-first-run-coherence.md` (Slice I + Slice G)
- Implementation: `src/doge/interfaces/gateway/routers/sessions.py`,
  `src/doge/interfaces/api/handlers/sessions.py`,
  `src/doge/application/agent/worker.py`,
  `src/doge/application/use_cases/run_use_cases.py`,
  `packages/doge-sdk-python/doge_sdk/session.py`,
  `packages/doge-sdk-typescript/src/session.ts`, `web/src/api/agent.ts`,
  `web/src/stores/agent.ts`
