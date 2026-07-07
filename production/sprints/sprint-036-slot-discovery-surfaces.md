# Sprint 036 - Slot Discovery Surfaces

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-07

## Summary

Sprint 036 implements the read-only slot discovery slice from
`C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md`.

The sprint adds a shared manifest-only slot status serializer, mounts
feature-gated `/v1/slots` routes, and adds `doged slots` for local daemon
operators. It also updates the canonical FastAPI route authority from 90 to 93
HTTP routes.

This sprint makes built-in slots discoverable. It does not complete the full
OpenClaw-like Slot Platform.

## Scope

- Add ADR-0045 and this sprint CDD/governance trail.
- Add `build_slot_status_rows()` in
  `src/doge/bootstrap/runtime_factories/slots.py`.
- Reuse shared status rows in `doge slots list`.
- Add `src/doge/interfaces/gateway/routers/slots.py`.
- Mount:
  - `GET /v1/slots`
  - `GET /v1/slots/{slot_id}`
  - `GET /v1/slots/{slot_id}/health`
- Gate `/v1/slots` behind `DOGE_FEATURE_SLOT_PLATFORM`.
- Add `doged slots` and `doged slots --json`.
- Add slot API and doged tests.
- Update route authority to 93 HTTP routes across active API docs, entities
  registry, TR registry, architecture registry, traceability, ADR-0007,
  fastapi-service CDD, runtime-maturity, and governance tests.
- Update the OpenClaw-like plan file.

## Explicitly Out of Scope

- `SlotKernel`, `SlotLifecycle`, `SlotBundle`, `SlotPolicy`, or `SlotLoader`.
- `/v1/slot-bundles`, bundle activation, YAML manifests, third-party install,
  signing, or enterprise allowlist.
- Web Slot Center or SDK slot client source.
- Runtime consumers for data, document, gateway, UI, watcher, eval, or
  governance facets beyond existing prior proofs.
- Runtime permission/health enforcement or lifecycle hook invocation.
- Persistence schema, ModelRouter/ProfileRegistry, runtime dispatch, or worker
  behavior changes.
- Production readiness declaration or external/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows the
recent local platform sprint precedent where no new story-status tracking is
introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-036-slot-discovery-surfaces-manifest.md`.

Verification results:

- Focused slot API / doged / CLI suite passed: 37 tests.
- Route coverage and S017 governance route sync passed: 39 tests.
- Combined Sprint 036 focused + slot regression suite passed: 148 tests.
- SDK contract, import boundaries, docs authority/links/maturity, ADR/CDD
  maturity honesty, stale count, ADR index, governance YAML, plan closure, and
  whitespace checks passed.
