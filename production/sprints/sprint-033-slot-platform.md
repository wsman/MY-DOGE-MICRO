# Sprint 033 - Slot Platform Foundation

Status: Local implementation complete / ready for local acceptance
Date: 2026-07-06

## Summary

Sprint 033 implements the Slot Platform Foundation plan from
`C:\Users\WSMAN\.claude\plans\openclaw-like-magical-barto.md`.

The sprint adds a declarative slot contract (`SlotManifest` v1 plus
`ISlot`/`SlotContribution`/`SlotContext`/`SlotRegistry`) and wires exactly one
built-in tool slot (`market.core`) into the existing tool registry through an
additive, feature-flagged dual path. With `DOGE_FEATURE_SLOT_PLATFORM` off,
tool-registry and runtime behavior are byte-identical to the legacy factory path.

## Scope

- Add ADR-0042 and this sprint CDD/governance trail.
- Add `src/doge/platform/slots/` (errors, manifest, contracts, registry, __init__).
- Add `src/doge/products/market/slot.py` (`MarketCoreSlot`) wrapping the existing
  six market-facing tool descriptors.
- Add `src/doge/bootstrap/runtime_factories/slots.py` and a flag branch in
  `src/doge/bootstrap/runtime_factories/tools.py`.
- Add `doge slots list/show` CLI (`src/doge/interfaces/cli/commands/slots.py`) and
  wire it into `commands/__init__.py` and `cli/main.py`.
- Add the `slot_platform` feature flag (`FEATURE_LIFECYCLES` + `FeatureConfig`).
- Add slot contract unit tests, a boundary ratchet, a tool-registry slot parity
  test with a frozen flag-off baseline, and CLI tests.
- Update `tests/test_settings.py` for the new feature lifecycle entry.
- Update active session state, runtime maturity, module boundaries, and source
  layout map.

## Explicitly Out of Scope

- `/v1` API surface or OpenAPI changes.
- SDK surface, Web UI, daemon command source, or ModelRouter changes.
- Model/workflow/data/document/ui/gateway/governance/eval/watcher slot types.
- `/v1/slots` HTTP API and `doged slots`.
- ADR-0019 CapabilityRegistry unification into slots.
- Migrating the remaining 17 tool methods into slots.
- YAML-on-disk manifest parsing, third-party slot install, and bundles.
- Watcher slots and runtime permission/health enforcement.
- Production readiness declaration or external gate closure.

## Registration

This sprint is not registered in `production/sprint-status.yaml`. It follows the
UX/product-acceptance and SDK-governance sprint precedent where no new
story-status tracking is introduced.

## Verification Status

Local verification is recorded in
`production/qa/evidence/sprint-033-slot-platform-manifest.md`.

Verification results:

- Focused slot-platform suite passed: slot contract, boundary ratchet, CLI, and
  parity tests.
- Settings lifecycle tests pass with `slot_platform` included.
- Existing tool-registry and golden runtime contract regressions stay green.
- SDK contract passed: 15 surfaces, 15 entity parity checks.
- Docs authority, docs links, docs maturity claims, import boundaries,
  ADR/CDD maturity honesty, plan closure, and whitespace checks passed.
- Plan closure posture remains controlled open: 4 open / 2 passed.
