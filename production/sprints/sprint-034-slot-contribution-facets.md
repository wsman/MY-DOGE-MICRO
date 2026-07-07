# Sprint 034 - Slot Contribution Facets

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-07

## Summary

Sprint 034 implements the contribution-facet slice from
`C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md`.

The sprint widens the Slot Platform contract so `SlotContribution` can carry all
planned non-tool facets, and it adds one runtime proof: `model.kimi_agent_sdk`
contributes the existing `kimi_agent_sdk` backend through the slot registry when
`DOGE_FEATURE_SLOT_PLATFORM` is enabled.

This sprint completes contribution facets plus the model-backend slot proof. It
does not complete the full OpenClaw-like Slot Platform.

## Scope

- Add ADR-0043 and this sprint CDD/governance trail.
- Add `src/doge/platform/slots/facets.py`.
- Widen `SlotContribution` with model, workflow, data, document, gateway, UI,
  watcher, eval, and governance facet fields.
- Make `SlotContext.tool_application_service` optional and add well-known
  service-id constants.
- Add no-op `ISlot.start()` and `ISlot.stop()` lifecycle hooks.
- Make `MarketCoreSlot` fail fast when resolved without a tool service.
- Add `src/doge/bootstrap/runtime_factories/builtin_model_slot.py` with
  `ModelKimiAgentSdkSlot`.
- Register the model slot in `build_builtin_slot_registry()`.
- Add `build_slot_aware_agent_backends()` and the `build_agent_backends()` flag
  branch.
- Filter tool/model contribution resolution by `SlotType`.
- Add facet, built-in model slot, agent-backend parity, duplicate-backend, and
  tool-executor fail-fast tests.
- Update active session state, runtime maturity, architecture registry, module
  boundaries, source layout map, and the Sprint 034 plan file.

## Explicitly Out of Scope

- Runtime consumers for workflow, data, document, gateway, UI, watcher, eval, and
  governance facets.
- Slot lifecycle hook invocation.
- `/v1` API surface or OpenAPI changes.
- SDK source, Web source, daemon command source, persistence, ModelRouter,
  ProfileRegistry, or runtime dispatch changes.
- `/v1/slots`, `doged slots`, Web Slot Center, YAML manifests, bundles,
  third-party install, and signature policy.
- Production readiness declaration or external/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows the
recent local platform sprint precedent where no new story-status tracking is
introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-034-slot-contribution-facets-manifest.md`.

Verification results:

- Focused slot/model suite passed: 72 tests covering slot facets, slot boundary,
  agent-backend parity, and tool-registry slot parity.
- Existing settings, agent, tool-registry, golden runtime contract, and
  architecture regressions passed: 408 tests, 108 existing deprecation warnings.
- SDK contract passed: 15 surfaces, 15 entity parity checks.
- Docs authority, docs links (101 markdown files), docs maturity claims, import boundaries,
  ADR/CDD maturity honesty, plan closure, governance YAML shape, ADR index, stale
  count, and whitespace checks passed.
- Plan closure posture remains controlled open: 4 open / 2 passed.
