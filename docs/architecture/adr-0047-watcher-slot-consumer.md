# ADR-0047: Watcher Slot Consumer

## Status

Accepted

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 038 consumes the `watcher` slot facet at the runtime event recording
seam. `TransitionRecorder` now accepts a narrow runtime event watcher protocol
and invokes it after each event is appended to the active transaction but before
the event is staged to the outbox or committed.

The built-in `watcher.runtime_events` slot contributes an allow-only watcher
behind `DOGE_FEATURE_SLOT_PLATFORM` + `DOGE_FEATURE_SLOT_WATCHER`, preserving
current behavior while proving the middleware path. Custom watcher slots can
return `block`, `pause`, or `fail` decisions; these fail closed by raising before
commit, rolling back the transaction, and preventing outbox/publish side
effects.

## Status Update - 2026-07-08

ADR-0058 supersedes the Sprint 038 default-off posture for
`DOGE_FEATURE_SLOT_PLATFORM` and `DOGE_FEATURE_SLOT_WATCHER`: both are now on by
default for local runs. The built-in watcher remains allow-only; concrete
cost/secret/citation/tenant/Python-executor watcher policies remain future work.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; existing runtime transaction factory; existing slot facet dataclasses |
| **Domain** | Agent Runtime, runtime event middleware, safety watcher composition |
| **Knowledge Risk** | LOW - local runtime/service protocol work over existing dataclasses |
| **References Consulted** | `docs/architecture/adr-0011-agent-runtime-levels.md`, `docs/architecture/adr-0025-streaming-semantics.md`, `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0043-slot-contribution-facets.md`, `docs/architecture/adr-0046-governance-slot-consumer.md`, `src/doge/application/agent/transition_recorder.py`, `src/doge/platform/slots/facets.py`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | watcher slot unit tests, watcher parity/blocking contract tests, transition recorder tests, CLI/API/doged slot status tests, settings/capability tests, import boundaries, docs validators, maturity honesty, plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0011 (Agent Runtime Levels), ADR-0025 (Runtime Streaming Semantics), ADR-0042 (Slot Platform Foundation), ADR-0043 (Slot Contribution Facets), ADR-0046 (Governance Slot Consumer) |
| **Extends** | ADR-0043 by adding a runtime consumer for the `watchers` facet |
| **Supersedes** | None |
| **Enables** | Runtime permission/health enforcement, later cost/secret/citation watchers, and SlotKernel watcher orchestration |
| **Blocks** | None |

## Context

The Slot Platform roadmap requires watcher slots to observe runtime event state
without being ordinary tools or prompt-visible skills. Before this sprint,
`WatcherContribution` existed as a typed facet, but no runtime component
consumed it.

The runtime event recorder is the narrowest useful seam because it already owns
transactional event append, outbox staging, commit, rollback, and post-commit
publish. Invoking watchers there allows a blocking decision to prevent the event
from being committed or published.

## Constraints

- Keep `DOGE_FEATURE_SLOT_PLATFORM` and `DOGE_FEATURE_SLOT_WATCHER` default
  `false`.
- Preserve flag-off runtime event behavior.
- Keep `TransitionRecorder` independent of `SlotRegistry` and `doge.platform`.
- Invoke watcher decisions before outbox staging and before transaction commit.
- Fail closed on blocking decisions or watcher failures.
- Do not add new `RunStatus` values or mutate the run state for `pause` in this
  sprint.
- Do not add Web Slot Center, SDK slot client, bundle activation, third-party
  install, permission/health enforcement, or active health probes.
- Do not close external/operator gates or change production maturity posture.

## Decision

Add `IRuntimeEventWatcher` to `doge.core.ports.runtime_services`. It exposes one
method:

```python
def enforce(self, event: AgentEvent) -> None: ...
```

Update `TransitionRecorder` to accept `event_watcher` as an optional
constructor dependency. The default no-op watcher preserves all existing direct
unit-test construction paths. During `record()`, each persisted event is passed
to `event_watcher.enforce(persisted_event)` after `tx.append_event(event)` and
before `tx.stage_outbox(persisted_event)`.

Add `doge.platform.runtime.watchers.RuntimeEventWatcherMiddleware`. It evaluates
slot-contributed `WatcherContribution` objects and supports these actions:

- `allow`: continue
- `warn`: continue, no persistence side effect in this sprint
- `pause`: raise `WatcherDecisionError`
- `block`: raise `WatcherDecisionError`
- `fail`: raise `WatcherDecisionError`

Unknown actions raise `SlotConfigurationError`. Watcher exceptions are converted
to `WatcherDecisionError(action="fail")` so watcher failures fail closed and the
runtime transaction rolls back.

Add `doge.platform.runtime.slot.RuntimeEventWatcherSlot`, the built-in
`watcher.runtime_events` slot. It contributes an allow-only watcher so enabling
`DOGE_FEATURE_SLOT_WATCHER` proves the middleware path while preserving runtime
event behavior.

Add `build_slot_aware_runtime_event_watcher()` in
`src/doge/bootstrap/runtime_factories/slots.py`. It resolves watcher slots whose
feature flags are satisfied, rejects duplicate watcher IDs, and returns
`RuntimeEventWatcherMiddleware` or `None` when no watchers are enabled.

Update `build_agent_runtime_kernel()` to pass the slot-aware watcher middleware
into `TransitionRecorder` only when `DOGE_FEATURE_SLOT_PLATFORM` is enabled.

Add `DOGE_FEATURE_SLOT_WATCHER` lifecycle metadata and expose
`feature.slot_watcher` through the capability registry.

## Alternatives Considered

### Alternative 1: Invoke watchers after commit and publish

- **Description**: Let watchers observe events after `tx.commit()` and after
  outbox/publisher side effects.
- **Pros**: Cannot interfere with runtime persistence.
- **Cons**: Cannot block dangerous state transitions or event side effects.
- **Rejection Reason**: Watchers need to be a safety middleware, not only a
  passive audit stream.

### Alternative 2: Put watcher evaluation directly in `TransitionRecorder`

- **Description**: Import SlotRegistry and watcher contribution types directly
  in application runtime code.
- **Pros**: Fewer bootstrap functions.
- **Cons**: Violates the separation where application runtime depends on core
  ports, while slot assembly belongs to bootstrap/platform.
- **Rejection Reason**: `TransitionRecorder` should depend on a narrow protocol,
  not on the slot platform.

### Alternative 3: Implement concrete cost/secret/citation watchers now

- **Description**: Add multiple business/safety watchers in the same sprint.
- **Pros**: More visible product value.
- **Cons**: Conflates the consumer seam with policy design and increases risk
  before the middleware contract is proven.
- **Rejection Reason**: Sprint 038 proves the runtime watcher consumer; concrete
  high-risk watchers belong in later policy/enforcement sprints.

## Consequences

### Positive

- The `watcher` facet now has a real runtime consumer.
- Blocking watcher decisions roll back the transaction before outbox/publish.
- `TransitionRecorder` remains testable and independent of slot internals.
- Built-in watcher behavior is parity-preserving.
- Duplicate watcher IDs fail fast during middleware assembly.

### Negative

- `warn` decisions are observed only in memory and are not persisted yet.
- `pause` currently fails closed instead of transitioning to a new pause state.
- Concrete cost, secret-leak, citation, tenant-boundary, and Python-executor
  watchers remain future work.
- Watcher middleware is still assembled ad hoc by runtime factories rather than
  a first-class `SlotKernel`.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Watcher middleware changes event persistence unexpectedly | LOW | HIGH | Default watcher is allow-only and focused tests prove append/outbox/commit/publish behavior is preserved. |
| Blocking decisions occur after side effects | LOW | HIGH | Middleware is invoked before `stage_outbox()` and before `commit()`. |
| Bad watcher code breaks runtime runs | MEDIUM | MEDIUM | Watcher exceptions fail closed with `WatcherDecisionError`; concrete third-party watchers remain out of scope. |
| Operators mistake watcher slot for complete permission enforcement | LOW | MEDIUM | ADR/CDD/evidence keep permission/health enforcement and concrete watcher policies out of scope. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-038-watcher-slot-consumer.md` | Watcher slots can observe and block runtime events through a controlled runtime middleware. | Adds runtime watcher middleware at `TransitionRecorder.record()`. |
| `design/cdd/bc-06-agent-runtime.md` | Runtime owns sessions, runs, events, and safe transition recording. | Keeps watcher invocation in the runtime recorder transaction path. |
| `design/cdd/bc-08-governance-evaluation.md` | Governance and evaluation own safety monitoring and maturity gates. | Enables future safety watchers without prompt-visible tool behavior. |

## Performance Implications

- **CPU**: one small watcher loop per persisted runtime event when slot watcher
  is enabled.
- **Memory**: negligible; stores a tuple of watcher contributions.
- **Load Time**: imports one platform runtime slot and watcher middleware when
  the built-in registry is built.
- **Network**: none.

## Migration Plan

1. Add the runtime event watcher protocol.
2. Add optional watcher injection to `TransitionRecorder`.
3. Add watcher middleware and built-in allow-only watcher slot.
4. Register the watcher slot in the built-in registry.
5. Add `build_slot_aware_runtime_event_watcher()`.
6. Wire runtime kernel construction to pass watcher middleware when the slot
   platform is enabled.
7. Add `DOGE_FEATURE_SLOT_WATCHER` and capability discovery rows.
8. Keep concrete policy watchers, permission enforcement, SlotKernel, bundles,
   Web, SDK, loader, signing, and third-party work deferred.

## Validation Criteria

- `watcher.runtime_events` manifest is typed as `watcher`, declares
  `slot_platform` + `slot_watcher`, and provides `runtime_event.observe`.
- With slot watcher off, runtime factory returns no watcher middleware.
- With built-in slot watcher on, `TransitionRecorder` append/outbox/commit/publish
  behavior is unchanged.
- A custom blocking watcher rolls back the transaction before outbox staging and
  before publish.
- Duplicate watcher IDs fail fast.
- CLI/API/doged slot discovery lists `watcher.runtime_events` disabled until
  `DOGE_FEATURE_SLOT_WATCHER=1`.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0011: Agent Runtime Levels
- ADR-0025: Runtime Streaming Semantics
- ADR-0042: Slot Platform Foundation
- ADR-0043: Slot Contribution Facets
- ADR-0046: Governance Slot Consumer
