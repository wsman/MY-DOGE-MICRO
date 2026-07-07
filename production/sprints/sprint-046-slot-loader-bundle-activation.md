# Sprint 046 - Slot Loader and Bundle Activation

Status: Local implementation complete / local verification passed
Date: 2026-07-07

## Summary

Sprint 046 implements the SlotLoader and process-local bundle activation slice
from `C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md`.

The sprint adds JSON-only manifest loading, manifest-only disk slots,
`DOGE_FEATURE_SLOT_LOADER`, `DOGE_SLOT_MANIFEST_DIRS`, process-local active
bundle state, CLI bundle list/activate commands, and feature-gated
`POST /v1/slot-bundles/{bundle_id}/activate`.

This sprint does not complete the full OpenClaw-like Slot Platform.

## Scope

- Add ADR-0056 and this sprint CDD/governance trail.
- Add `SlotLoader` and `ManifestOnlySlot`.
- Add `SlotBundleActivationState` and `policy_for_activation()`.
- Add `DOGE_FEATURE_SLOT_LOADER` lifecycle metadata and settings field.
- Add `DOGE_SLOT_MANIFEST_DIRS` settings parsing.
- Expose `feature.slot_loader` through capability discovery.
- Register manifest-only slots when loader is enabled.
- Apply active bundle policy in built-in SlotKernel creation.
- Add CLI `doge slots bundle list` and `doge slots bundle activate`.
- Add feature-gated API activation route.
- Update HTTP route authority to 96 routes.
- Update configuration docs and the OpenClaw-like plan file.

## Explicitly Out of Scope

- YAML manifest parsing.
- Provider entrypoint import or arbitrary Python plugin execution.
- Third-party slot install, signing, and enterprise allowlist.
- Persistent activation state and cross-process synchronization.
- SDK slot client methods.
- OS sandboxing, subprocess isolation, network interception, filesystem
  mediation, or database/secret access interception.
- Production readiness declaration or external/operator gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows
the recent local platform sprint precedent where no new story-status tracking is
introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-046-slot-loader-bundle-activation-manifest.md`.

Local verification result:

- Focused settings/capability/loader/activation/API/CLI suite passed:
  138 tests including route-governance checks.
- Broad slot parity suite passed: 167 tests.
- SDK contract passed: 15 surfaces / 15 entity parity checks.
- Import boundaries, docs authority, docs links, docs maturity, ADR/CDD
  maturity honesty, ADR index, governance YAML, acceptable-open plan closure,
  and WSL/Windows whitespace checks passed.
- Closure posture remains intentionally open for operator-owned external gates:
  2 passed, 4 open, 0 failed, 0 invalid.
