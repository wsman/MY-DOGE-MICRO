# Sprint 035 - Workflow Slot Consumer

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-07

## Summary

Sprint 035 implements the workflow-facet consumer slice from
`C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md`.

The sprint adds a built-in `workflow.templates` slot and routes the workflow
template seeding path through a feature-flagged, slot-aware template definition
factory. Flag-off seeding remains backed by the existing `BUILTIN_TEMPLATES`
list, and flag-on output is parity-tested against that same list.

This sprint proves one additional non-tool facet consumer. It does not complete
the full OpenClaw-like Slot Platform.

## Scope

- Add ADR-0044 and this sprint CDD/governance trail.
- Add `src/doge/platform/workspace/slot.py` with `WorkflowTemplatesSlot`.
- Register `workflow.templates` in `build_builtin_slot_registry()`.
- Add `build_slot_aware_workflow_templates()` in
  `src/doge/bootstrap/runtime_factories/slots.py`.
- Make `seed_workflow_templates()` accept injected template definitions while
  preserving the built-in default.
- Add `WorkspaceContainer.build_workflow_template_definitions()` as the feature
  posture decision point.
- Route CLI `template seed` and MCP `seed_workflow_templates` through the
  workspace-container template definition seam.
- Make `doge slots list` show manifest feature-flag status without resolving
  slots.
- Add workflow slot unit tests, workflow parity/fail-fast contract tests, seeder
  injection tests, workspace-container seam tests, and CLI slot status tests.
- Update active session state, runtime maturity, architecture registry, module
  boundaries, source layout map, and the OpenClaw-like plan file.

## Explicitly Out of Scope

- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, or `SlotLoader`.
- `/v1/slots`, `doged slots`, Web Slot Center, bundle activation, YAML
  manifests, third-party install, signing, or enterprise allowlist.
- Runtime consumers for data, document, gateway, UI, watcher, eval, or
  governance facets.
- Runtime permission/health enforcement or lifecycle hook invocation.
- `/v1` API surface, OpenAPI, SDK package source, Web source, daemon command
  source, persistence schema, ModelRouter/ProfileRegistry, or runtime dispatch
  changes.
- Production readiness declaration or external/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows the
recent local platform sprint precedent where no new story-status tracking is
introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-035-workflow-slot-consumer-manifest.md`.

Verification results:

- Focused workflow-slot suite passed: 88 tests covering slot provider, template
  seeding, CLI slot status, workflow parity, agent-backend parity, and
  tool-registry slot parity.
- Additional platform workflow/MCP/API/architecture regressions passed.
- SDK contract passed: 15 surfaces, 15 entity parity checks.
- Docs authority, docs links, docs maturity claims, import boundaries,
  ADR/CDD maturity honesty, plan closure, governance YAML shape, ADR index,
  stale count, and whitespace checks passed.
- Plan closure posture remains controlled open: 4 open / 2 passed.
