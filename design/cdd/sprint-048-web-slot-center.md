# Sprint 048 CDD: Web Slot Center

Status: Ready for Acceptance / Local Verification Passed
Date: 2026-07-07

## 1. Overview

Sprint 048 adds a read-only Slot Center to the existing Web Admin center.

The sprint consumes existing `/v1/slots` and `/v1/slot-bundles` rows through
the Web platform API/store and renders installed slot, health, risk, feature
flag, and bundle status next to the current capability registry.

The sprint does not add bundle activation, persistent enable/disable state,
new backend routes, SDK slot clients, SlotLoader, third-party install, signing,
permission enforcement, active health probes, external gate closure, or
production-readiness changes.

## 2. User Promise / JTBD

An operator can inspect Slot Platform readiness from Web without switching to
CLI or daemon commands.

A platform engineer can verify whether a slot is resolved, disabled,
degraded, or high-risk from the same Admin surface that already exposes
capabilities.

A future activation/loader sprint has a Web read model to build on without
changing the current Admin layout.

## 3. Detailed Behavior

- `web/src/api/platform.ts` defines slot and bundle row types matching the
  existing backend responses.
- `listSlots()` calls `GET /v1/slots`.
- `listSlotBundles()` calls `GET /v1/slot-bundles`.
- The platform store caches `slotRows` and `slotBundles`.
- The platform store exposes `slotRowsById` and `slotBundlesById`.
- AdminCenterView loads capabilities, slots, and slot bundles on mount and on
  Refresh.
- Slot Center renders summary counts:
  - Installed;
  - Enabled;
  - Disabled;
  - Degraded;
  - High risk.
- Slot rows render name, id, type, status, health, risk, owner, maturity,
  tool/capability counts, and feature flags.
- Bundle rows render bundle name, id, status, enabled count, disabled count,
  and missing count.
- The existing Capability Registry remains visible below Slot Center.

## 4. Contracts / Data Model

Slot API helper:

```ts
export async function listSlots(): Promise<SlotStatusRow[]> {
  const payload = await dogeClient.request<SlotListResponse>('GET', '/v1/slots')
  return payload.slots
}
```

Bundle API helper:

```ts
export async function listSlotBundles(): Promise<SlotBundleRow[]> {
  const payload = await dogeClient.request<SlotBundleListResponse>('GET', '/v1/slot-bundles')
  return payload.bundles
}
```

Admin refresh behavior:

```ts
await Promise.allSettled([
  store.loadCapabilities(),
  store.loadSlots(),
  store.loadSlotBundles(),
])
```

Maturity posture:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 5. Edge Cases

- Slot API disabled: existing Admin warning alert shows the backend failure
  message and leaves empty slot/bundle lists.
- No slots: Slot Center displays `No slots`.
- No bundles: Slot Center displays `No bundles`.
- Unknown status strings: tag styling falls back to default.
- Long feature-flag or slot IDs wrap inside the row without resizing the page.

## 6. Dependencies

- ADR-0045 Slot Discovery Surfaces.
- ADR-0052 Slot Kernel, Bundles, Policy, and Lifecycle.
- ADR-0053 UI Slot Consumer.
- Existing AdminCenterView and platform store.
- Existing DogeClient request helper.

## 7. Configuration Knobs

- `DOGE_FEATURE_SLOT_PLATFORM`: backend gate for `/v1/slots` and
  `/v1/slot-bundles`.

No Web feature flag, activation flag, persistent layout flag, or SDK public
surface is added in this sprint.

## 8. Acceptance Criteria

- Web platform API exposes `listSlots()` and `listSlotBundles()`.
- Platform store caches slot and bundle rows and exposes id indexes.
- AdminCenterView renders read-only Slot Center before Capability Registry.
- Admin refresh loads capabilities, slots, and bundles.
- Focused Web tests cover store slot/bundle loading and Admin Slot Center
  rendering.
- Full Web test suite and Web build pass.
- No backend route count, SDK contract, SlotLoader, bundle activation,
  third-party install/signing, permission enforcement, production readiness
  declaration, or external/operator gate closure is added.

## 9. Validation Plan

```bash
cd web && npm run test -- src/views/AdminCenterView.spec.ts src/stores/platform.spec.ts
cd web && npm run test
cd web && npm run build
py -3 scripts/validate_docs_authority.py
py -3 scripts/validate_docs_links.py
py -3 scripts/validate_docs_maturity_claims.py
py -3 scripts/validate_alpha_maturity_honesty.py --file docs/architecture/adr-0054-web-slot-center.md
py -3 scripts/validate_alpha_maturity_honesty.py --file design/cdd/sprint-048-web-slot-center.md
py -3 scripts/validate_adr_index_completeness.py
py -3 scripts/validate_governance_yaml_shape.py
py -3 scripts/validate_plan_closure_gate.py --allow-open --source-plan C:/Users/WSMAN/.claude/plans/openclaw-like-magical-barto.md
git diff --check
cmd.exe /c git diff --check
```

## 10. Local Verification Result

Final local verification is recorded in
`production/qa/evidence/sprint-048-web-slot-center-manifest.md`.

## 11. Out of Scope

- Bundle activation and persistent enable/disable state.
- New backend routes.
- SDK slot client methods.
- SlotLoader and disk manifests.
- Third-party slot install, signing, and enterprise allowlist.
- Runtime permission enforcement and active health probes.
- Dynamic component loading or per-user UI layout state.
- Production readiness declaration or external/operator gate closure.
