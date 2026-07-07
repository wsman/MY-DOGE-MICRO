# Sprint 044 - UI Slot Consumer

Status: Local implementation complete / local verification passed
Date: 2026-07-07

## Summary

Sprint 044 implements the UI facet consumer slice from
`C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md`.

The sprint adds `ui.research_workspace`, a backend `UIPanelRegistry`,
slot-aware UI panel row factories, read-only `/v1/ui-panels`, and a frontend
`panelRegistry.ts` used by `ResearchAgentView.vue`.

This sprint proves UI panel metadata can be contributed and consumed through
the Slot Platform. It does not complete the full OpenClaw-like Slot Platform.

## Scope

- Add ADR-0053 and this sprint CDD/governance trail.
- Add `DOGE_FEATURE_SLOT_UI` lifecycle metadata and settings field.
- Expose `feature.slot_ui` through capability discovery.
- Add `workspace` metadata to `UIPanelContribution` while preserving existing
  positional constructor compatibility.
- Add `doge.platform.workspace.ui_slot.ResearchWorkspaceUISlot`.
- Add `doge.platform.workspace.ui_panels.UIPanelRegistry`.
- Register `ui.research_workspace` in the built-in slot registry and research
  workspace bundle.
- Add `build_slot_aware_ui_panels()` and `build_slot_ui_panel_rows()`.
- Add feature-gated `GET /v1/ui-panels`.
- Add Web `panelRegistry.ts` and slot-driven `ResearchAgentView` panel guards.
- Add UI panel API/store plumbing for future Web consumers.
- Update route authority to 95 HTTP routes.
- Update the OpenClaw-like plan file.

## Explicitly Out of Scope

- Web Slot Center.
- Dynamic component loading from backend metadata.
- Persistent UI layout state or per-user customization.
- Bundle activation and persistent enable/disable state.
- SlotLoader, YAML manifests, third-party install, signing, and enterprise
  allowlist.
- Runtime permission enforcement and active health probes.
- SDK slot client.
- Persistence schema, ModelRouter/ProfileRegistry, external auth, worker
  behavior, or production deployment behavior changes.
- Production readiness declaration or external/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows the
recent local platform sprint precedent where no new story-status tracking is
introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-044-ui-slot-consumer-manifest.md`.

Verification result:

- UI slot/settings/API/CLI focused Python suite passed: 93 tests.
- Focused Web panel/store/ResearchAgentView suite passed: 14 tests.
- API route coverage and route-governance sync passed: 39 tests.
- Full Web suite passed: 163 tests.
- Slot consumer parity suite passed: 195 tests.
- Architecture boundary gates passed: 22 tests.
- SDK contract, Web build, import boundaries, docs authority/links/maturity,
  ADR index, governance YAML, stale-count guard, acceptable-open plan closure,
  and WSL/Windows whitespace checks passed.
