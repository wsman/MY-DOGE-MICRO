# ADR-0053: UI Slot Consumer

## Status

Accepted

## Date

2026-07-07

## Decision Makers

wsman (product owner) / implementation agent

## Summary

Sprint 044 consumes the `ui` slot facet without changing the Research workspace
user experience. The sprint adds a built-in `ui.research_workspace` slot that
contributes panel metadata, a backend `UIPanelRegistry`, a feature-gated
`GET /v1/ui-panels` read API, and a frontend `panelRegistry.ts` used by
`ResearchAgentView.vue` to decide which existing panels render.

The sprint keeps all panels enabled by default through a local frontend
fallback. It does not add Web Slot Center, dynamic component loading, bundle
activation, persistent UI layout state, third-party slots, signing, permission
enforcement, or production-readiness changes.

## Status Update - 2026-07-08

ADR-0058 makes `DOGE_FEATURE_SLOT_PLATFORM` default-on for local runs, but does
not promote `DOGE_FEATURE_SLOT_UI`. UI panel metadata remains explicitly gated
by `DOGE_FEATURE_SLOT_UI=1`; the frontend fallback remains the default UI path.

## Technology Compatibility

| Field | Value |
|-------|-------|
| **Stack** | Python 3.10+; FastAPI; Vue 3 + Pinia + Vite |
| **Domain** | Slot Platform UI facet, Research workspace panel metadata |
| **Knowledge Risk** | LOW - additive metadata registry and existing component render guards |
| **References Consulted** | `docs/architecture/adr-0042-slot-platform.md`, `docs/architecture/adr-0043-slot-contribution-facets.md`, `docs/architecture/adr-0045-slot-discovery-surfaces.md`, `docs/architecture/adr-0052-slot-kernel-bundles-policy.md`, `web/src/views/ResearchAgentView.vue`, `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md` |
| **Post-Cutoff APIs Used** | None |
| **Verification Required** | UI slot unit/contract/API tests, ResearchAgentView and panel registry tests, route authority, web build, import/docs/maturity validators |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0042 (Slot Platform Foundation), ADR-0043 (Slot Contribution Facets), ADR-0045 (Slot Discovery Surfaces), ADR-0052 (Slot Kernel, Bundles, Policy, and Lifecycle) |
| **Extends** | ADR-0043 by consuming the `ui_panels` facet; ADR-0052 by resolving UI contributions through `SlotKernel` |
| **Supersedes** | None |
| **Enables** | Web Slot Center, slot-aware workspace preflight, bundle-based UI diagnostics |
| **Blocks** | None |

## Context

`ResearchAgentView.vue` already contains a mature local analyst/developer
workspace: guided flow, scenario picker, documents, portfolio import, evidence
matrix, citation drilldown, approval cards, quality panels, comparison, cost
diagnostics, and timeline. Until this sprint, those panels were statically
assembled inside the view and the `ui_panels` facet had no runtime consumer.

The Slot Platform roadmap calls for every facet to have at least one real
consumer before loader, enforcement, third-party, and Slot Center work. UI is
the remaining facet with user-visible composition impact, so it needs a
conservative metadata-first seam that preserves existing Web behavior.

## Constraints

- Keep `DOGE_FEATURE_SLOT_PLATFORM` and the new `DOGE_FEATURE_SLOT_UI` default
  `false`.
- Preserve `ResearchAgentView` Analyst/Developer parity and accessibility
  behavior when no remote panel metadata is loaded.
- Keep backend UI contributions as metadata only; do not import Vue or frontend
  modules into Python platform contracts.
- Keep dynamic component loading out of scope.
- Keep `doge.platform.slots` pure and framework-free.
- Do not add Web Slot Center, bundle activation, persistent UI layout state,
  SlotLoader, signing, third-party install, permission enforcement, active
  health probes, external gate closure, or production-readiness claims.

## Decision

Add `DOGE_FEATURE_SLOT_UI` lifecycle metadata and `FeatureConfig.slot_ui`.
Expose `feature.slot_ui` through capability discovery.

Extend `UIPanelContribution` with a defaulted `workspace` field while preserving
the existing positional constructor order.

Add `doge.platform.workspace.ui_slot.ResearchWorkspaceUISlot`. It declares
`ui.research_workspace`, type `ui`, feature flags `slot_platform` and
`slot_ui`, and contributes the current Research workspace panel set.

Add `doge.platform.workspace.ui_panels.UIPanelRegistry`. It rejects duplicate
panel IDs within a workspace and filters rows by workspace, zone, and mode.

Add `build_slot_aware_ui_panels()` and `build_slot_ui_panel_rows()` to
`doge.bootstrap.runtime_factories.slots`. These resolve `SlotType.UI` through
`SlotKernel.resolve_contributions()`.

Add `GET /v1/ui-panels` to the existing slots router. The endpoint is read-only
and requires both `DOGE_FEATURE_SLOT_PLATFORM=1` and `DOGE_FEATURE_SLOT_UI=1`.
Route authority moves from 94 to 95 HTTP routes.

Add `web/src/views/panelRegistry.ts`. It defines the default Research workspace
panel metadata, accepts remote panel metadata from the platform store, filters
by Analyst/Developer mode, and returns visible panel IDs.

Update `ResearchAgentView.vue` to call `showPanel(panel_id)` around existing
panels. The default registry includes every current panel, so rendering remains
unchanged when the backend route is disabled or not loaded.

## Alternatives Considered

### Alternative 1: Build Web Slot Center first

- **Description**: Add a dedicated Slot Center view before wiring UI panels.
- **Pros**: More visible operator feature.
- **Cons**: Slot Center would display metadata without proving the UI facet is
  actually consumable by the main workspace.
- **Rejection Reason**: The roadmap orders UI facet consumer before Slot Center.

### Alternative 2: Dynamically import components from backend metadata

- **Description**: Treat `component_module` as a runtime import path and render
  panels from a fully dynamic list.
- **Pros**: More plugin-like.
- **Cons**: Higher frontend risk, harder bundling guarantees, and a larger
  security surface.
- **Rejection Reason**: Built-in metadata and static component imports preserve
  parity while proving the contract.

### Alternative 3: Reuse the split-tree view registry

- **Description**: Add agent panel metadata to `web/src/views/registry.ts`.
- **Pros**: Existing registry file.
- **Cons**: That registry owns top-level workspace views, not internal agent
  panel zones.
- **Rejection Reason**: Internal panel composition needs a separate registry.

## Consequences

### Positive

- The `ui` facet now has a backend and frontend consumer.
- Research workspace panel metadata is discoverable through `/v1/ui-panels`.
- Analyst/Developer panel visibility is represented as slot metadata.
- Frontend rendering can remain static while becoming slot-driven.
- Route, CLI/API/doged slot status, and capability discovery include the UI
  feature posture.

### Negative

- The backend API exists before Web automatically loads remote panel metadata.
- Static imports remain in `ResearchAgentView.vue`.
- Panel metadata is not persisted or user-customizable.
- UI slots are metadata only; no permission or health enforcement is added.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Research workspace loses panels in Analyst mode | LOW | HIGH | Default frontend registry includes all current Analyst panels; view tests cover Analyst/Developer visibility. |
| Backend metadata diverges from frontend defaults | MEDIUM | MEDIUM | Shared panel IDs are tested in Python and TypeScript; API rows are covered. |
| `/v1/ui-panels` suggests Slot Center is complete | LOW | MEDIUM | Docs and CDD state Web Slot Center remains out of scope. |

## CDD Requirements Addressed

| CDD System | Requirement | How This ADR Addresses It |
|------------|-------------|--------------------------|
| `design/cdd/sprint-044-ui-slot-consumer.md` | UI slots can contribute Research workspace panel metadata consumed by backend and Web. | Adds UI slot provider, panel registry, API rows, frontend registry, and ResearchAgentView guards. |
| `design/cdd/fastapi-service.md` | API route table is the auditable contract. | Updates route authority to 95 HTTP routes including `/v1/ui-panels`. |
| `docs/progress/runtime-maturity.yaml` | Slot Platform maturity remains experimental. | Records Sprint 044 as local experimental only. |

## Performance Implications

- **CPU**: in-memory panel filtering over a 20-row default set.
- **Memory**: one short-lived registry for API/factory calls and a small
  frontend default registry.
- **Load Time**: no dynamic component import change; existing static component
  imports remain.
- **Network**: one optional read-only `/v1/ui-panels` call for future Web
  consumers.

## Migration Plan

1. Add `DOGE_FEATURE_SLOT_UI`.
2. Add `ui.research_workspace` slot provider.
3. Add `UIPanelRegistry` and slot-aware UI panel factory helpers.
4. Add read-only `/v1/ui-panels`.
5. Add frontend `panelRegistry.ts`.
6. Wrap existing `ResearchAgentView` panels with `showPanel(panel_id)`.
7. Update route authority, docs, tests, and runtime maturity evidence.
8. Keep Web Slot Center and dynamic component loading deferred.

## Validation Criteria

- `ui.research_workspace` manifest is type `ui` and declares `slot_platform`
  plus `slot_ui`.
- `build_slot_aware_ui_panels()` returns no registry until both flags are on.
- UI panel duplicate IDs fail fast.
- `/v1/ui-panels` is 404 when `slot_ui` is off and returns Research workspace
  panel rows when enabled.
- `ResearchAgentView` renders the same Analyst/Developer panels by default.
- Frontend panel registry tests cover default and remote metadata filtering.
- API route authority and entities registry agree on 95 HTTP routes.
- Maturity posture remains `production_ready: false`,
  `stable_declaration: forbidden`, and `level_3_sdk_platform: experimental`.

## Related Decisions

- ADR-0042: Slot Platform Foundation
- ADR-0043: Slot Contribution Facets
- ADR-0045: Slot Discovery Surfaces
- ADR-0052: Slot Kernel, Bundles, Policy, and Lifecycle
