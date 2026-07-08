# ADR-0052: Slot Kernel, Bundles, Policy, and Lifecycle

## Status

Accepted

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 043 promotes the Slot Platform from ad hoc consumer helpers toward a
first-class orchestration layer. The sprint adds pure platform contracts for
`SlotKernel`, `SlotPolicy`, `SlotBundle`, and `SlotLifecycle`, then routes the
existing slot-aware consumers through `SlotKernel.resolve_contributions()`.

The sprint also opens a read-only `GET /v1/slot-bundles` discovery route for
built-in scenario bundles. It does not add bundle activation, disk manifest
loading, third-party install, signing, runtime permission enforcement, SDK slot
clients, or Web Slot Center.

## Status Update - 2026-07-08

ADR-0058 makes SlotKernel-backed built-in contribution resolution the local
default for the promoted built-in consumers. This is not persistent bundle
activation: `DOGE_FEATURE_SLOT_LOADER` stays default-off and active bundle state
remains process-local when explicitly enabled.

ADR-0060 later supersedes the last sentence above: `slot_loader` now defaults on
for manifest-only loading, and operator-selected bundle activation is persisted
in SQLite. This ADR still owns the `SlotKernel`/`SlotPolicy`/`SlotBundle`
contract shape.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; existing FastAPI route layer; existing slot manifest/facet contracts |
| **Domain** | Slot Platform orchestration, API discovery, governance diagnostics |
| **Knowledge Risk** | LOW - in-process dataclasses and routing over existing local seams |
| **References Consulted** | `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0043-slot-contribution-facets.md`, `docs/architecture/adr-0045-slot-discovery-surfaces.md`, `docs/architecture/adr-0051-eval-slot-consumer.md`, `src/doge/bootstrap/runtime_factories/slots.py`, `src/doge/platform/slots/registry.py`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | slot kernel/bundle/policy tests, all slot consumer parity tests, API route coverage, governance route sync, import boundaries, docs validators, maturity honesty, plan closure, whitespace checks |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0042 (Slot Platform Foundation), ADR-0043 (Slot Contribution Facets), ADR-0045 (Slot Discovery Surfaces), ADR-0051 (Eval Slot Consumer) |
| **Extends** | ADR-0042 by adding the first-class kernel, bundle, policy, and lifecycle orchestration contracts |
| **Supersedes** | None |
| **Enables** | UI slot consumer, runtime permission/health enforcement, SlotLoader, bundle activation, and Web Slot Center |
| **Blocks** | Third-party slot install should not proceed before SlotPolicy and lifecycle contracts remain covered by tests |

## Context

Sprints 033-042 proved several concrete slot consumer shapes: tools, models,
workflows, governance policies, watchers, documents, data sources, gateway
routes, and eval suites. Each consumer assembled the built-in registry and
resolved contributions independently in `bootstrap/runtime_factories/slots.py`.

That made the Slot Platform real but not yet first-class. The next step is to
centralize registry, policy, bundle, lifecycle, and contribution resolution
behind one kernel while preserving the parity of all existing consumers.

## Constraints

- Keep `DOGE_FEATURE_SLOT_PLATFORM` default `false`.
- Keep `doge.platform.slots` pure and framework-free.
- Preserve tool/model/workflow/data/document/governance/watcher/gateway/eval
  parity.
- Keep bundle discovery read-only.
- Do not add activation, persistence, disk manifest loading, signing, or
  third-party install.
- Do not enforce runtime permissions or active health checks in this sprint.
- Do not add SDK slot clients or Web Slot Center.
- Do not close external/operator gates or change production maturity posture.

## Decision

Add `SlotPolicy` in `doge.platform.slots.policy`. It evaluates whether a
manifest is enabled by explicit allow/deny lists and feature flags.

Add `SlotBundle` and `SlotBundleStatus` in `doge.platform.slots.bundles`.
Bundles are named, read-only scenario groupings over registered slot IDs.

Add `SlotLifecycle`, `SlotLifecycleState`, and `SlotLifecycleRecord` in
`doge.platform.slots.lifecycle`. Lifecycle invokes `ISlot.start()` and
`ISlot.stop()` once per kernel instance and records local state.

Add `SlotKernel` in `doge.platform.slots.kernel`. It owns:

- a `SlotRegistry`;
- a `SlotPolicy`;
- a `SlotLifecycle`;
- registered `SlotBundle` definitions;
- policy-aware status rows;
- bundle status rows;
- type-filtered contribution resolution.

Add `build_builtin_slot_kernel()` to
`src/doge/bootstrap/runtime_factories/slots.py`, wrapping the existing built-in
slot registry and built-in bundles. Existing `build_slot_aware_*` consumers now
resolve contributions through `SlotKernel.resolve_contributions()` rather than
hand-scanning the registry.

Add `build_slot_bundle_rows()` and `GET /v1/slot-bundles`. The endpoint returns
read-only built-in bundle status and remains gated by `DOGE_FEATURE_SLOT_PLATFORM`.

Update route authority from 93 to 94 HTTP routes: 34 legacy `/api/*` routes and
60 daemon/v1/health routes.

## Alternatives Considered

### Alternative 1: Keep ad hoc consumer helpers only

- **Description**: Leave each `build_slot_aware_*` function to scan the registry.
- **Pros**: No refactor risk.
- **Cons**: No first-class lifecycle, bundle, or policy concept.
- **Rejection Reason**: The roadmap requires SlotKernel to become the common
  orchestration layer before UI, loader, and third-party work expand the surface.

### Alternative 2: Add bundle activation now

- **Description**: Add `POST /v1/slot-bundles/{bundle_id}/activate` and CLI
  activation.
- **Pros**: More complete user-facing bundle story.
- **Cons**: Requires persistence, operator authorization, conflict rules, and
  rollback semantics.
- **Rejection Reason**: Sprint 043 is a first-class read/control contract slice;
  activation belongs with SlotLoader and policy persistence.

### Alternative 3: Put SlotKernel in bootstrap

- **Description**: Keep kernel orchestration beside runtime factories.
- **Pros**: Fewer pure-package exports.
- **Cons**: Makes the core slot contract depend on process wiring and weakens
  reuse by CLI/API/Web discovery.
- **Rejection Reason**: Kernel, policy, bundle, and lifecycle contracts are pure
  platform concepts; concrete slot providers and service wiring remain in
  bootstrap and their owning modules.

## Consequences

### Positive

- Slot orchestration has a first-class kernel.
- Policy and bundle concepts are explicit and testable.
- Lifecycle start/stop hooks have a tested invocation path.
- Existing consumers share the same contribution resolver.
- `/v1/slot-bundles` exposes scenario groupings without enabling activation.

### Negative

- Runtime factories still construct a fresh kernel per helper call.
- Lifecycle is an explicit kernel API, not yet a process-level long-lived
  resource manager.
- Bundle status is feature-flag/policy read state only; it is not an activation
  state.
- Permissions and health remain declarative.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Kernel refactor changes existing consumers | MEDIUM | HIGH | Run all slot consumer parity tests and route coverage. |
| Bundle API looks like activation exists | LOW | MEDIUM | Endpoint is read-only; docs and CDD keep activation out of scope. |
| Custom test registries fail due built-in bundles | LOW | MEDIUM | Bootstrap filters built-in bundles to those fully supported by the current registry; direct `SlotKernel` remains strict. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-043-slot-kernel-bundles-policy.md` | SlotKernel, SlotPolicy, SlotBundle, and SlotLifecycle become first-class. | Adds pure platform contracts and routes existing consumers through the kernel. |
| `design/cdd/bc-08-governance-evaluation.md` | Governance & Evaluation owns policy and maturity guardrails. | Adds policy rules without declaring production readiness or external gate closure. |
| `docs/progress/runtime-maturity.yaml` | Slot Platform maturity must remain experimental until external gates close. | Records Sprint 043 as local experimental only. |

## Performance Implications

- **CPU**: small in-memory policy and type filtering over the built-in registry.
- **Memory**: one short-lived kernel and bundle row list per factory/API call.
- **Load Time**: imports the new pure slot modules.
- **Network**: none.

## Migration Plan

1. Add `SlotPolicy`.
2. Add `SlotBundle` and bundle status contracts.
3. Add `SlotLifecycle`.
4. Add `SlotKernel`.
5. Export the new contracts from `doge.platform.slots`.
6. Add built-in bundle definitions and `build_builtin_slot_kernel()`.
7. Refactor existing slot-aware consumers to resolve through the kernel.
8. Add `build_slot_bundle_rows()` and `GET /v1/slot-bundles`.
9. Update route authority from 93 to 94 HTTP routes.
10. Keep activation, loaders, signing, SDK, Web Slot Center, permissions, and
    active health enforcement deferred.

## Validation Criteria

- `SlotPolicy` honors feature flags and explicit allow/deny lists.
- `SlotBundle` rejects invalid IDs, empty slot sets, and overlap.
- `SlotKernel` resolves policy-enabled contributions by type.
- `SlotKernel` reports policy-aware slot status.
- `SlotKernel.start()` and `SlotKernel.stop()` invoke lifecycle hooks in
  deterministic order.
- Built-in bundle rows are discoverable.
- `/v1/slot-bundles` returns read-only bundle status when slot platform is on.
- Existing slot-aware tool/model/workflow/governance/watcher/document/data/
  gateway/eval parity tests continue to pass.
- Route authority and governance entity route lists agree on 94 HTTP routes.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0042: Slot Platform Foundation
- ADR-0043: Slot Contribution Facets
- ADR-0045: Slot Discovery Surfaces
- ADR-0051: Eval Slot Consumer
