# ADR-0041: Python SDK Typed Run Result Models

## Status

Accepted

## Date

2026-07-06

## Decision Makers

wsman (product owner) · Codex implementation agent

## Summary

Sprint 032 implements the Python SDK typed result model slice from
`C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md`.

The decision is to add dict-subclass typed models for Python SDK run REST
responses. The SDK keeps the existing dict-return contract: existing consumers
can continue to use equality with plain dicts, `run["field"]`, `run.get(...)`,
and dict iteration, while new consumers can use typed convenience properties
such as `run.run_id`, `run.status`, and `run.approvals[0].approval_id`.

No daemon route, OpenAPI schema, response payload, TypeScript SDK type, or
runtime behavior changes are introduced.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; httpx-only Python SDK |
| **Domain** | Python SDK run resources |
| **Knowledge Risk** | LOW - return-type-only wrapping of existing JSON payloads |
| **References Consulted** | `packages/doge-sdk-python/doge_sdk/run.py`, `packages/doge-sdk-typescript/src/run.ts`, `tests/contract/test_python_sdk.py`, `packages/doge-sdk-python/README.md`, `examples/python/03_stream_and_approve.py`, `C:\Users\WSMAN\.claude\plans\a038a698-harmonic-mango.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | Python SDK contract tests, run-model unit tests, SDK contract parity, docs/maturity validators, import boundaries, plan closure gate, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0028 (workflow slug/run contract), ADR-0036 (run list and comparison), ADR-0040 (approval policy surfacing) |
| **Enables** | Python SDK consumers can use discoverable run result properties without losing dict compatibility. |
| **Blocks** | None |
| **Ordering Note** | Documents/platform models, citation models, memo export models, and high-level research helpers require separate SDK design. |

## Context

### Problem Statement

The Python SDK run resource currently returns raw dictionaries for
`get`, `list`, `events`, `approve`, `resume`, and `cancel`. The TypeScript SDK
already documents run-resource types (`AgentRun`, `AgentArtifact`,
`AgentApproval`, `AgentEvent`, and `RunListItem`), while Python users get no
attribute-level autocomplete for the same payloads.

At the same time, existing Python consumers rely on raw dict behavior:

- Contract tests assert `client.runs.get(...) == {"run_id": ..., "status": ...}`.
- Contract tests assert `client.runs.list(...) == [{...}]` and
  `client.runs.events(...) == [{...}]`.
- Approval examples use `run.get("approvals", [])` and
  `run["approvals"][0]["approval_id"]`.
- README documents dict access as the canonical approval pattern.

A dataclass or Pydantic result model would break these patterns. A dict subclass
adds typed access while preserving the existing contract.

### Constraints

- Preserve `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.
- Do not add, remove, or rename `/v1` routes or response fields.
- Do not change OpenAPI or TypeScript SDK parity.
- Do not add runtime dependencies to the Python SDK.
- Do not convert streaming `DogeEvent`; it remains a frozen dataclass.
- Do not add catch-all attribute access that hides misspelled fields.
- Do not broaden scope to documents/platform/Citation/MemoExport.

## Decision

Add `packages/doge-sdk-python/doge_sdk/run_models.py` with explicit
dict-subclass models:

```text
Run          -> TypeScript AgentRun
RunListItem  -> TypeScript RunListItem
Artifact     -> TypeScript AgentArtifact
Approval     -> TypeScript AgentApproval
RunEvent     -> TypeScript AgentEvent
```

Each model inherits from `dict` and exposes explicit `@property` accessors.
`Run` copies the incoming payload and wraps known nested lists when they are
present:

```text
events    -> list[RunEvent]
artifacts -> list[Artifact]
approvals -> list[Approval]
```

The wrapper does not insert missing keys. This preserves existing equality
against minimal plain dictionaries returned by tests or older daemon snapshots.

Wire the models into `RunsResource` and `AsyncRunsResource`:

```text
get / approve / resume / cancel -> Run
list                            -> list[RunListItem]
events                          -> list[RunEvent]
stream                          -> DogeEvent unchanged
summary / claims / citations / evaluation -> raw dict/list unchanged
```

Re-export the new model classes from `doge_sdk.__init__`.

## Alternatives Considered

### Alternative 1: Dataclass result models

- **Description**: Convert run responses to frozen dataclasses.
- **Pros**: Stronger static typing and immutable-looking objects.
- **Cons**: Breaks equality with dicts, `run["field"]`, and `run.get(...)`.
- **Rejection Reason**: Existing tests and documented usage require dict
  behavior.

### Alternative 2: Pydantic models

- **Description**: Return Pydantic model instances from the SDK.
- **Pros**: Validation and schema-driven typing.
- **Cons**: Adds a runtime dependency and breaks dict access semantics.
- **Rejection Reason**: The SDK intentionally remains lightweight and currently
  depends only on `httpx`.

### Alternative 3: Catch-all `__getattr__`

- **Description**: Let any dict key become an attribute dynamically.
- **Pros**: Less boilerplate.
- **Cons**: Misspelled attributes fail late and can collide with dict methods.
- **Rejection Reason**: Explicit properties are safer and keep the public shape
  aligned with the TypeScript run-resource model set.

### Alternative 4: Type documents/platform/Citation/MemoExport at the same time

- **Description**: Broaden Python SDK typed models beyond run resources.
- **Pros**: More complete typed SDK surface.
- **Cons**: Turns a safe return-type slice into a cross-SDK modeling sprint.
- **Rejection Reason**: Sprint 032 is intentionally limited to run REST results
  that already have `run.ts` counterparts.

## Consequences

### Positive

- Python SDK users gain attribute-style discovery for common run result fields.
- Existing dict-based code remains valid.
- Sync and async SDK clients stay behaviorally consistent.
- SDK contract parity remains focused on HTTP and OpenAPI/TypeScript surfaces.

### Negative

- Dict subclasses are less strict than schema-validated models.
- Static type checkers may still treat arbitrary dict payloads conservatively.
- Documents/platform/Citation/MemoExport remain raw dict follow-up work.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Dict equality regresses | MEDIUM | HIGH | Do not insert missing keys; preserve contract tests asserting plain dict equality. |
| Dict method collision | LOW | HIGH | Use explicit payload-field properties only; test `get`, `items`, and `keys` remain callable. |
| Nested wrapping breaks dict access | LOW | MEDIUM | Nested models are also dict subclasses; test both `run.approvals[0].approval_id` and `run["approvals"][0]["approval_id"]`. |
| Scope creep | MEDIUM | MEDIUM | Defer documents/platform/Citation/MemoExport and high-level helpers. |

## CDD Requirements Addressed

| CDD Document | Requirement | How This ADR Addresses It |
|--------------|-------------|----------------------------|
| `design/cdd/sprint-032-python-sdk-typed-models.md` | Add typed Python run result models while preserving dict compatibility. | Adds dict-subclass run models and wraps run resource returns. |
| `design/cdd/sprint-026-demo-pack-and-sdk-cookbooks.md` | SDK cookbooks should remain runnable and documented. | README and examples keep dict access working. |
| `design/cdd/sprint-031-approval-policy-surfacing.md` | Approval metadata should remain additive and backward compatible. | Approval model properties tolerate optional explanation metadata. |

## Performance Implications

- **CPU**: Small per-response object wrapping cost for run payloads.
- **Memory**: One shallow copied dict per wrapped run/list/event payload.
- **Network**: None.
- **Package Size**: No new dependency or generated schema bundle.

## Migration Plan

1. Add dict-subclass run model classes.
2. Wrap sync `RunsResource` return values.
3. Wrap async `AsyncRunsResource` return values.
4. Re-export the model classes from the Python SDK package.
5. Update README with additive typed-access guidance.
6. Add unit and contract tests for dict compatibility plus typed properties.
7. Add governance records and local evidence.
8. Run focused Python SDK checks and governance validators.

## Validation Criteria

- Existing Python SDK dict equality tests pass unchanged.
- New model tests prove dict methods and attribute access coexist.
- Nested approvals, artifacts, and events remain dict-compatible.
- Sync and async run resources return typed model objects.
- `DogeEvent` stream objects remain dataclasses and are not dicts.
- SDK contract remains 15/15.
- No Python SDK dependency is added.
- Docs and maturity validators preserve Local Alpha honesty.

## Related Decisions

- ADR-0028: Additive Session Turn Workflow Field
- ADR-0036: Run List And Comparison
- ADR-0040: Approval Policy Surfacing
