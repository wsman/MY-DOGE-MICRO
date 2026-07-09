# ADR-0070: Slot Watcher Provider Facet

## Status

Accepted

## Date

2026-07-09

## Decision Makers

wsman (product owner) / implementation agent

## Summary

P10 opens the third previously restricted installed-provider facet: `watchers`.
Installed third-party providers may now contribute runtime event watchers when
they pass the existing ADR-0064/0065 provider execution chain and when
`DOGE_FEATURE_SLOT_WATCHER` is enabled.

Watcher callables are wrapped in the existing slot permission context before
the middleware invokes them. The middleware already fails closed on watcher
exceptions, missing decisions, unsupported actions, and blocking decisions.

This ADR does not open gateway routes or governance policies. It does not add
marketplace behavior, YAML manifests, URL/upload install, OS/container/WASM
sandboxing, transitive dependency signing, or production maturity.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; existing Slot Platform contracts and runtime watcher middleware |
| **Domain** | Slot Platform runtime watcher provider facet |
| **Knowledge Risk** | HIGH - watcher callables participate in runtime event commit decisions and still execute in-process |
| **References Consulted** | `docs/reference/python/VERSION.md`, `docs/architecture/adr-0047-watcher-slot-consumer.md`, `docs/architecture/adr-0064-slot-provider-execution.md`, `docs/architecture/adr-0065-provider-package-identity.md`, `docs/architecture/adr-0069-slot-ui-panel-provider-facet.md`, `design/cdd/sprint-038-watcher-slot-consumer.md`, `C:\Users\WSMAN\.claude\plans\openclaw-rippling-sparkle.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | provider watcher tests, runtime watcher parity tests, slot API/CLI regression, governance validators, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0043 (Slot Contribution Facets), ADR-0047 (Watcher Slot Consumer), ADR-0064 (Slot Provider Execution), ADR-0065 (Provider Package Identity), ADR-0066 (Code-String Isolation Prototype), ADR-0067 (Install Surfaces), ADR-0068 (Eval Suite Provider Facet), ADR-0069 (UI Panel Provider Facet) |
| **Extends** | ADR-0064 by moving only `watchers` from restricted provider facets into the installed-provider allowlist |
| **Supersedes** | ADR-0064's "watchers are not executable from installed third-party providers" statement, only for the default-off local provider path |
| **Enables** | Later governance policy and route facet decisions |
| **Blocks** | Any claim that P10 enables route injection, governance policy mutation, provider sandboxing, external gate closure, or production maturity |

## Context

ADR-0047 already introduced a slot-aware `RuntimeEventWatcherMiddleware`. That
middleware evaluates watcher decisions before event commit/outbox publish and
fails closed for exceptions, unsupported actions, missing decisions, and
blocking actions.

Opening watcher providers is riskier than eval/UI metadata because watcher code
is an in-process callable participating in runtime commit decisions. P10
therefore keeps all ADR-0064/0065 gates, requires the existing `slot_watcher`
flag, and wraps provider watcher callables in the slot permission context before
execution.

## Constraints

- Keep all provider execution gates from ADR-0064/0065.
- Require the existing `slot_watcher` feature flag for watcher resolution.
- Allow only `SlotType.WATCHER` providers to contribute `watchers`.
- Keep `routes` and `governance_policies` restricted.
- Preserve fail-closed watcher behavior.
- Execute watcher callables with active slot permission context when runtime
  interception is enabled.
- Keep `production_ready: false`, `stable_declaration: forbidden`, and
  `level_3_sdk_platform: experimental`.

## Decision

`InstalledProviderSlot` now treats `SlotType.WATCHER` as provider-executable
and maps it to the single allowed contribution field `watchers`.

`build_slot_aware_runtime_event_watcher()` now wraps each contributed
`WatcherContribution.on_event` callable in a slot-scoped wrapper. When
`slot_runtime_interception` is enabled, watcher code runs with
`slot_permission_context(slot_id, permissions, enforce=True, audit_sink=...)`.

Contribution validation still rejects:

- any route contribution;
- any governance policy contribution;
- any contribution field that belongs to a different slot type.

## Alternatives Considered

### Alternative 1: Keep watchers restricted

- **Pros**: Avoids expanding runtime commit-decision code.
- **Cons**: Prevents signed local providers from contributing policy-like
  runtime event checks.
- **Rejection Reason**: Existing watcher middleware already has a fail-closed
  model and can be wrapped in slot scope.

### Alternative 2: Allow watchers only after out-of-process provider isolation

- **Pros**: Stronger containment.
- **Cons**: Blocks a local alpha facet that can still be operator-gated and
  fail-closed.
- **Rejection Reason**: This ADR keeps local alpha scope honest and does not
  claim sandboxing.

### Alternative 3: Open governance policies together with watchers

- **Pros**: More complete policy surface.
- **Cons**: Governance policies can mutate entitlement behavior and need their
  own escalation analysis.
- **Rejection Reason**: P10 requires one facet at a time.

## Consequences

### Positive

- Signed local providers can contribute runtime event watchers through the
  governed provider path.
- Watcher callable execution now carries slot permission context.
- Existing fail-closed watcher behavior remains in force.

### Negative

- Provider watcher code still runs in-process when default-off gates are
  enabled.
- Watchers can intentionally block runtime events once installed and enabled by
  the operator.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Provider watcher blocks important runtime events | MEDIUM | HIGH | Provider execution is default-off/operator-gated; watcher decisions fail closed and are visible through existing errors. |
| Watcher code bypasses in-process guards | MEDIUM | HIGH | Slot scope wraps watcher callables for guarded ports, but ADR states this is not malicious-code containment. |
| Remaining restricted facets open accidentally | LOW | HIGH | Tests keep route facets rejected after watcher expansion; `_RESTRICTED_FACETS` still blocks routes/governance. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/p10-watcher-provider-facet.md` | Allow watcher provider facets only after fail-closed behavior and slot scope are explicit. | Opens only `watchers` and wraps `on_event` in slot permission context. |
| `design/cdd/sprint-038-watcher-slot-consumer.md` | Watchers can block runtime events before outbox/publish. | Reuses the existing middleware and fail-closed decision model. |
| `design/cdd/p5-slot-provider-execution.md` | Restricted facets must fail closed unless a later ADR accepts one. | Supersedes only the watcher restriction and keeps route/governance restrictions. |

## Validation Criteria

- Installed signed watcher provider resolves through
  `build_slot_aware_runtime_event_watcher`.
- Provider watcher decisions run with active slot permission context.
- Built-in watcher tests and watcher parity tests pass.
- Route facets remain rejected after watcher expansion.
- Slot API/CLI regression passes.
- Governance validators pass and maturity posture remains unchanged.

## Related Decisions

- [ADR-0047: Watcher Slot Consumer](adr-0047-watcher-slot-consumer.md)
- [ADR-0064: Slot Provider Execution](adr-0064-slot-provider-execution.md)
- [ADR-0065: Provider Package Identity](adr-0065-provider-package-identity.md)
- [ADR-0069: Slot UI Panel Provider Facet](adr-0069-slot-ui-panel-provider-facet.md)
