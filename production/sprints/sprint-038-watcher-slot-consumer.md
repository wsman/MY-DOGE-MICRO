# Sprint 038 - Watcher Slot Consumer

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-07

## Summary

Sprint 038 implements the watcher-facet consumer slice from
`C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md`.

The sprint adds a built-in `watcher.runtime_events` slot and wires watcher
contributions into the runtime event recorder through a narrow
`IRuntimeEventWatcher` protocol. The built-in watcher is allow-only and parity
preserving; custom watchers can block events before outbox staging and publish.

This sprint makes watcher slots an actual runtime middleware contribution point.
It does not complete the full OpenClaw-like Slot Platform.

## Scope

- Add ADR-0047 and this sprint CDD/governance trail.
- Add `IRuntimeEventWatcher`.
- Add optional watcher injection to `TransitionRecorder`.
- Add `src/doge/platform/runtime/watchers.py`.
- Add `src/doge/platform/runtime/slot.py`.
- Register `RuntimeEventWatcherSlot` in the built-in slot registry.
- Add `build_slot_aware_runtime_event_watcher()` in
  `src/doge/bootstrap/runtime_factories/slots.py`.
- Wire runtime kernel construction to pass watcher middleware when the slot
  platform is enabled.
- Add `DOGE_FEATURE_SLOT_WATCHER` lifecycle metadata and settings.
- Expose `feature.slot_watcher` in the capability registry.
- Extend CLI, doged, and `/v1/slots` tests to cover `watcher.runtime_events`
  status.
- Add watcher slot unit tests and watcher parity/blocking tests.
- Update the OpenClaw-like plan file.

## Explicitly Out of Scope

- Concrete cost, secret-leak, high-risk action, citation, tenant-boundary, or
  Python-executor watcher policies.
- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, or `SlotLoader`.
- Runtime permission/health enforcement or active health probes.
- `/v1/slot-bundles`, bundle activation, YAML manifests, third-party install,
  signing, or enterprise allowlist.
- Web Slot Center or SDK slot client source.
- Persistence schema, ModelRouter/ProfileRegistry, external auth, or worker
  behavior changes.
- Production readiness declaration or external/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows the
recent local platform sprint precedent where no new story-status tracking is
introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-038-watcher-slot-consumer-manifest.md`.

Initial verification result:

- Focused watcher slot / parity / recorder / CLI / API / doged / settings /
  capability suite passed: 94 tests.

Final broad validation is recorded in the evidence manifest.
