# Sprint 037 - Governance Slot Consumer

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-07

## Summary

Sprint 037 implements the governance-facet consumer slice from
`C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md`.

The sprint adds a built-in `governance.tool_policy` slot and wires governance
policy contributions into the slot-aware tool-registry entitlement checker.
The default slot-contributed policy is parity-equivalent with the legacy
`ToolRegistry` defaults, while custom governance slots can further constrain
tool schema discovery and execution.

This sprint makes governance an actual slot contribution point. It does not
complete the full OpenClaw-like Slot Platform.

## Scope

- Add ADR-0046 and this sprint CDD/governance trail.
- Add `src/doge/platform/governance/slot.py`.
- Export the governance slot/checker types from `doge.platform.governance`.
- Register `ToolGovernancePolicySlot` in the built-in slot registry.
- Add `build_slot_aware_entitlement_checker()` in
  `src/doge/bootstrap/runtime_factories/slots.py`.
- Wire the effective entitlement checker into `build_slot_aware_tool_registry()`.
- Add `DOGE_FEATURE_SLOT_GOVERNANCE` lifecycle metadata and settings.
- Expose `feature.slot_platform` and `feature.slot_governance` in the capability
  registry.
- Extend CLI, doged, and `/v1/slots` tests to cover `governance.tool_policy`
  status.
- Add governance slot unit tests and governance parity/constraining tests.
- Update the OpenClaw-like plan file.

## Explicitly Out of Scope

- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, or `SlotLoader`.
- Runtime permission/health enforcement or active health probes.
- Watcher slots or runtime event middleware.
- `/v1/slot-bundles`, bundle activation, YAML manifests, third-party install,
  signing, or enterprise allowlist.
- Web Slot Center or SDK slot client source.
- Persistence schema, ModelRouter/ProfileRegistry, runtime dispatch, external
  auth, or worker behavior changes.
- Production readiness declaration or external/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows the
recent local platform sprint precedent where no new story-status tracking is
introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-037-governance-slot-consumer-manifest.md`.

Initial verification result:

- Focused governance slot / parity / CLI / API / doged / settings /
  capability suite passed: 84 tests.

Final verification results:

- Broader slot/governance regression suite passed: 78 tests.
- Tool-registry regression suite passed: 34 tests.
- SDK contract passed: 15 surfaces / 15 entity parity checks.
- Import boundaries, docs authority/links/maturity, ADR/CDD maturity honesty,
  stale count, ADR index, governance YAML, plan closure, and whitespace checks
  passed.
