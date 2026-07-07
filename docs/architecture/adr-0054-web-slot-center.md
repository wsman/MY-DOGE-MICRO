# ADR-0054: Web Slot Center

## Status

Accepted

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 048 adds a read-only Web Slot Center to the existing Admin center. The
view consumes the already feature-gated `/v1/slots` and `/v1/slot-bundles`
surfaces through the platform API/store and renders installed slot, health,
risk, feature flag, and bundle status rows beside the existing capability
registry.

This sprint does not add bundle activation, persistent enable/disable state,
new backend routes, SDK slot clients, SlotLoader, third-party installation,
signing, permission enforcement, active health probes, or production-readiness
changes.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Vue 3 + Pinia + Vite; existing FastAPI `/v1` slot discovery APIs |
| **Domain** | Web operator surface for Slot Platform discovery |
| **Knowledge Risk** | LOW - read-only frontend consumption of existing API rows |
| **References Consulted** | `docs/architecture/adr-0045-slot-discovery-surfaces.md`, `docs/architecture/adr-0052-slot-kernel-bundles-policy.md`, `docs/architecture/adr-0053-ui-slot-consumer.md`, `web/src/views/AdminCenterView.vue`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | AdminCenterView/store Web tests, full Web suite, Web build, docs/maturity validators |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0045 (Slot Discovery Surfaces), ADR-0052 (Slot Kernel, Bundles, Policy, and Lifecycle), ADR-0053 (UI Slot Consumer) |
| **Extends** | ADR-0045 by adding a Web consumer for slot status rows; ADR-0052 by adding a Web consumer for bundle status rows |
| **Supersedes** | None |
| **Enables** | Later operator activation UI, permission/health posture diagnostics, and SlotLoader install previews |
| **Blocks** | None |

## Context

The Slot Platform now exposes built-in slot status through `/v1/slots`,
read-only bundle status through `/v1/slot-bundles`, and UI panel metadata
through `/v1/ui-panels`. Until this sprint, Web had no operator-facing Slot
Center and AdminCenterView showed only capability registry rows.

The roadmap calls for a Web Slot Center after the UI facet consumer and before
runtime permission/health enforcement or SlotLoader work. The right first slice
is read-only discovery: show installed, enabled, disabled, degraded, high-risk,
and bundle state without adding mutation controls.

## Constraints

- Reuse the existing Admin center route instead of adding a new top-level
  operator route.
- Keep `/v1/slots` and `/v1/slot-bundles` as the only backend source.
- Keep the UI read-only; activation belongs to the later SlotLoader/bundle
  activation sprint.
- Keep `DOGE_FEATURE_SLOT_PLATFORM` as the backend API gate.
- Do not add a TypeScript SDK public surface in this sprint.
- Do not claim production readiness or close external/operator gates.

## Decision

Add slot and bundle row types plus `listSlots()` and `listSlotBundles()` to
`web/src/api/platform.ts`.

Add `slotRows`, `slotBundles`, `slotRowsById`, `slotBundlesById`,
`loadSlots()`, and `loadSlotBundles()` to the platform Pinia store.

Update `AdminCenterView.vue` from a capability-only registry to a combined
Capability / Slot Center. The Slot Center section renders:

- summary counts for installed, enabled, disabled, degraded, and high-risk
  slots;
- sorted installed slot rows with type, status, health, risk, owner, maturity,
  tool/capability counts, and feature flags;
- read-only bundle rows with enabled, disabled, and missing counts.

Keep the existing capability registry section on the same page and have the
Refresh action load capabilities, slots, and bundles together.

## Alternatives Considered

### Alternative 1: Add a new `/slots` route

- **Description**: Create a dedicated Slot Center route and nav entry.
- **Pros**: Clearer direct URL.
- **Cons**: More navigation churn for a read-only operator slice.
- **Rejection Reason**: The existing Admin center is the established capability
  and operator diagnostics surface.

### Alternative 2: Add activation buttons now

- **Description**: Render enable/disable or bundle activation actions.
- **Pros**: More complete operator workflow.
- **Cons**: Backend persistence and activation contracts do not exist yet.
- **Rejection Reason**: The roadmap places activation in a later
  SlotLoader/bundle sprint.

### Alternative 3: Depend on the TypeScript SDK

- **Description**: Add public SDK methods for slot discovery and use them in
  Web immediately.
- **Pros**: One shared client surface.
- **Cons**: Expands SDK contract before activation and loader semantics are
  settled.
- **Rejection Reason**: Direct `dogeClient.request()` keeps this Web-only slice
  narrow.

## Consequences

### Positive

- Operators can inspect built-in slot and bundle state in Web.
- Slot Platform feature flags, health, risk, and maturity posture are visible
  without reading CLI output.
- The platform store has reusable read models for future activation and install
  previews.

### Negative

- The Web view will show an API error when the slot platform API is disabled.
- No mutation workflow exists yet; operators still need later activation work.
- Capability and slot rows are separate read models until a future unified
  operator dashboard is warranted.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Web appears to support slot activation | LOW | MEDIUM | No activation controls are rendered and docs mark activation out of scope. |
| Slot API disabled state looks like a page failure | MEDIUM | LOW | Existing Admin alert surfaces the backend message. |
| Operator page becomes too sparse or too card-heavy | LOW | LOW | Rows remain dense, unframed by nested cards, and reuse existing Admin layout. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-048-web-slot-center.md` | Web Admin exposes read-only slot and bundle state. | Adds API/store read plumbing and AdminCenterView Slot Center rows. |
| `docs/progress/runtime-maturity.yaml` | Slot Platform maturity remains experimental. | Records Sprint 048 as local experimental only. |

## Performance Implications

- **CPU**: client-side sorting over the small built-in slot and bundle lists.
- **Memory**: two small arrays in the platform store.
- **Load Time**: Admin refresh now performs two additional read-only API calls.
- **Network**: no polling or streaming; calls happen on mount and manual
  refresh only.

## Migration Plan

1. Add Web API types and request helpers for `/v1/slots` and
   `/v1/slot-bundles`.
2. Add platform store state, indexes, and loaders.
3. Update AdminCenterView with a read-only Slot Center section.
4. Add focused store and AdminCenterView tests.
5. Update governance docs and the Slot Platform roadmap.

## Validation Criteria

- AdminCenterView loads capabilities, slots, and slot bundles on mount.
- Slot Center renders installed, enabled, disabled, degraded, and high-risk
  summary counts.
- Slot rows expose id, type, status, health, risk, owner, maturity, feature
  flags, and tool/capability counts.
- Bundle rows expose status plus enabled, disabled, and missing counts.
- Existing capability registry remains visible.
- No backend route count, SDK contract, bundle activation, SlotLoader,
  permission enforcement, or production maturity change is introduced.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0045: Slot Discovery Surfaces
- ADR-0052: Slot Kernel, Bundles, Policy, and Lifecycle
- ADR-0053: UI Slot Consumer
