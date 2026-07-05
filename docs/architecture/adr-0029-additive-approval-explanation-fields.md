# ADR-0029: Additive optional `AgentApproval` explanation fields

## Status

Accepted

## Date

2026-07-05

## Decision Makers

wsman (product owner) · Codex documentation/governance agent

## Summary

`AgentApproval` currently tells an operator the action, risk level, status, run,
and timestamps. Sprint 022 records an additive contract decision to carry four
optional explanation strings with each approval:

- `why_needed`
- `impact`
- `deny_consequence`
- `publish_target`

Sprint 022 implements the target contract across runtime, persistence, API,
TypeScript SDK types, Web approval cards, tests, and governance records.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python >=3.10, FastAPI 0.123.8, Pydantic 2.12.4, SQLite local persistence; TypeScript SDK + Vue 3 web client |
| **Domain** | API Design / Agent Runtime / SDK / Web |
| **Knowledge Risk** | LOW — additive optional string fields on an existing serialized dataclass and response surface |
| **References Consulted** | `docs/reference/python/VERSION.md`, `design/cdd/sdk-daemon-client-interfaces.md`, `docs/architecture/runtime-contracts.md`, `docs/reference/http-api.md`, `docs/progress/runtime-maturity.yaml`, `C:\Users\WSMAN\.claude\plans\agent-quizzical-wolf.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | OpenAPI `ApprovalResponse` schema check; TypeScript SDK parity check; runtime golden contract update; repository/migration round-trip tests; approval resolve preservation test; Web rendering test |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0007 (API surface contract), ADR-0011 (agent runtime levels), ADR-0024 (single-stack runtime direction), ADR-0028 (additive request-contract precedent) |
| **Enables** | Web approval detail rows and SDK/API consumers that need structured approval context |
| **Blocks** | Future changes that would remove or rename the four explanation fields without a new ADR |
| **Ordering Note** | This ADR was accepted before the Sprint 022 code slices landed; local acceptance still depends on the verification suite recorded in the sprint manifest. |

## Context

### Problem Statement

Approval prompts are currently terse. Operators can see that an approval is
pending and whether it is high risk, but the approval object does not carry a
structured explanation of why the approval is needed, what decision area it
affects, what denial does, or where a publish action would go.

That creates a governance-trust gap in the Local Alpha workflow: the user can
resolve approvals, but the approval card does not preserve enough context for a
reviewer to understand the prompt without reconstructing it from surrounding
events.

### Constraints

- Runtime posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.
- The change must be additive: no existing `AgentApproval` field is removed,
  renamed, or made newly required.
- Empty string means "no explanation supplied" and allows older or partial
  producers to remain compatible.
- No approval-resolution semantics change.
- No entitlement or policy-decision semantics change.
- No external/operator gate is closed by this ADR.

### Requirements

- Add four optional string fields to the `AgentApproval` contract:
  `why_needed`, `impact`, `deny_consequence`, and `publish_target`.
- Preserve existing approval creation and resolution behavior for callers that
  do not provide the fields.
- Expose the fields through `/v1` approval reads and full-run responses after
  implementation.
- Keep TypeScript SDK fields optional so consumers tolerate older daemon
  snapshots.
- Update the runtime contract fixture and parity tooling in the implementation
  slice, not only prose.

## Decision

Extend `AgentApproval` with four optional explanation fields, all defaulting to
the empty string.

### Field Semantics

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `why_needed` | string | `""` | Human-readable reason the approval pause exists. |
| `impact` | string | `""` | Area affected by the approval decision, such as publication, compliance, or portfolio action. |
| `deny_consequence` | string | `""` | Expected result if the operator denies the approval. |
| `publish_target` | string | `""` | Destination, audience, or distribution target when the approval relates to publishing. |

### Architecture

```text
Tool/provider metadata
  -> ToolResult.data explanation keys
  -> RunStepper approval creation
  -> AgentApproval dataclass
  -> SQLite approvals row
  -> /v1 serialized approval/read responses
  -> TypeScript SDK AgentApproval
  -> Web approval detail rows
```

### Key Interfaces

```python
@dataclass
class AgentApproval:
    approval_id: str
    action: str
    risk_level: str
    run_id: str
    status: str = "pending"
    created_at: datetime = field(default_factory=utc_now)
    resolved_at: datetime | None = None
    why_needed: str = ""
    impact: str = ""
    deny_consequence: str = ""
    publish_target: str = ""
```

```typescript
export interface AgentApproval {
  approval_id: string
  action: string
  risk_level: string
  run_id: string
  status: string
  created_at: string
  resolved_at?: string | null
  why_needed?: string
  impact?: string
  deny_consequence?: string
  publish_target?: string
}
```

## Alternatives Considered

### Alternative 1: Keep explanation copy only in Web

- **Description**: Infer approval explanation rows from the action/risk level
  in the Web component.
- **Pros**: No API or persistence change.
- **Cons**: Loses provenance, cannot support SDK/CLI consumers, and cannot
  preserve provider-specific publish targets.
- **Rejection Reason**: The explanation belongs to the approval record, not to
  a single renderer.

### Alternative 2: Single `explanation` JSON blob

- **Description**: Add one JSON object with all explanation details.
- **Pros**: Flexible.
- **Cons**: Conflicts with the current flat approval schema convention and makes
  parity checks less direct.
- **Rejection Reason**: Four flat optional fields are simpler to migrate, test,
  and expose through typed SDK surfaces.

### Alternative 3: Four flat optional fields

- **Description**: Add the four named fields directly to `AgentApproval`.
- **Pros**: Additive, explicit, easy to hide when empty, and compatible with
  current dataclass serialization.
- **Cons**: Requires coordinated schema, migration, contract, SDK, and Web
  updates.
- **Rejection Reason**: Chosen.

## Consequences

### Positive

- Operators and SDK consumers can inspect why an approval is needed before
  resolving it.
- The approval object carries the same context across API, SDK, and Web
  surfaces.
- Empty defaults preserve existing producers and historical rows.

### Negative

- Runtime implementation requires a SQLite migration and contract fixture
  update.
- SDK parity must expand to include `AgentApproval`, which increases contract
  gate coverage.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Docs claim fields before code lands | LOW | MEDIUM | Sprint 022 implementation and validators landed with this ADR; future docs must keep the implementation evidence linked. |
| API/SDK drift | LOW | MEDIUM | Add `ApprovalResponse` to OpenAPI and SDK parity checks in implementation slice. |
| Empty fields clutter UI | LOW | LOW | UI hides rows when field value is empty. |

## CDD Requirements Addressed

| CDD Document | Requirement | How This ADR Addresses It |
|--------------|-------------|----------------------------|
| `design/cdd/sprint-022-approval-explanation.md` | Add structured approval explanation metadata without changing approval resolution semantics. | Defines four optional fields and their non-semantic role. |
| `design/cdd/sdk-daemon-client-interfaces.md` | Clients must surface approval-required states without auto-resuming. | Adds context for approval prompts while preserving explicit user resolution. |

## Performance Implications

- **CPU**: No meaningful change expected.
- **Memory**: Four small strings per approval object.
- **Load Time**: No expected effect.
- **Network**: Slightly larger approval payloads when fields are populated.

## Migration Plan

1. Add the fields to the domain dataclass and `AgentRun.add_approval`.
2. Populate the fields from approval-producing tool/provider results.
3. Add four nullable/defaulted SQLite columns for fresh and existing local
   databases.
4. Add `ApprovalResponse` / `ApprovalListResponse` and bind the approval-list
   route to the response model.
5. Update TypeScript SDK `AgentApproval` with optional fields and run parity
   tooling.
6. Update Web approval card rendering and focused tests.
7. Update runtime contract fixture and repository/migration tests.

**Rollback plan**: Stop populating the fields and remove them from response
models, SDK types, and UI rendering. Existing SQLite columns may remain harmless
empty metadata until a later cleanup decision.

## Validation Criteria

- `AgentApproval` accepts the four fields and preserves defaults for old call
  sites.
- Existing approval resolution keeps the explanation fields unchanged.
- Fresh and migrated SQLite approval rows round-trip all four fields.
- `/v1/runs/{run_id}/approvals` OpenAPI schema includes the four fields.
- TypeScript SDK `AgentApproval` parity includes the four optional fields.
- Runtime golden contract includes the four fields.
- Web approval card renders populated explanation rows and hides empty rows.
- `validate_plan_closure_gate.py --allow-open` remains controlled-open at
  4 open / 2 passed.

## Related

- ADR-0007: API Surface and CORS
- ADR-0011: Agent Runtime Levels
- ADR-0024: Single-Stack Runtime Direction
- ADR-0028: Additive Optional `workflow` field on the session-turn request
- `design/cdd/sprint-022-approval-explanation.md`
- `production/sprints/sprint-022-approval-explanation.md`
