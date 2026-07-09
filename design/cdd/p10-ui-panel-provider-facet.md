# P10 CDD: UI Panel Provider Facet

Status: Ready for Local Acceptance
Date: 2026-07-09

## 1. Overview

P10 continues restricted facet expansion by allowing installed, signed,
operator-gated providers to contribute UI panel metadata.

This is not dynamic frontend plugin loading. The backend accepts
`UIPanelContribution` metadata, and the existing Web `panelRegistry.ts` remains
the static allowlist for which Research workspace panels can render.

## 2. User Promise / JTBD

A workspace integrator can package UI panel metadata with a signed local slot
provider while the frontend still decides rendering through known static panel
ids and zones.

A security reviewer can verify that this opens only static metadata, not route
injection, runtime watchers, governance policy mutation, or frontend code
loading.

## 3. Scope

Included:

- Add `SlotType.UI` to the installed-provider executable type allowlist.
- Allow only the `ui_panels` contribution field for UI providers.
- Require the existing `slot_ui` flag for UI slot resolution.
- Keep route, watcher, and governance policy provider facets restricted.
- Reuse `build_slot_aware_ui_panels()` and `UIPanelRegistry`.
- Add provider execution tests for signed UI providers and route rejection.
- Add ADR, CDD, evidence, maturity, and registry updates.

Excluded:

- Dynamic component import from provider metadata.
- Frontend package distribution or remote component loading.
- Watcher provider facets.
- Governance policy provider facets.
- Gateway route provider facets.
- Marketplace/catalog behavior, URL/upload install, YAML manifests, remote
  registry trust, transitive dependency signing, or OS/container/WASM sandboxing.
- Any production maturity or external gate closure.

## 4. Configuration

No new feature flag is introduced. UI provider contributions require the
existing default-off chain:

```text
DOGE_FEATURE_SLOT_PLATFORM=1
DOGE_FEATURE_SLOT_LOADER=1
DOGE_FEATURE_SLOT_INSTALL=1
DOGE_FEATURE_SLOT_RUNTIME_INTERCEPTION=1
DOGE_FEATURE_SLOT_PROVIDER_EXECUTION=1
DOGE_FEATURE_SLOT_UI=1
```

Provider execution still also requires trusted publisher keys, signature
revocation storage, package-aware v3 sidecars, SlotKernel admission, and
enterprise allowlist when `DOGE_AUTH_MODE=enterprise`.

## 5. Runtime Behavior

When all provider gates pass and an installed provider manifest has
`type="ui"`, `InstalledProviderSlot` imports the signed package and accepts only
`ui_panels` from the provider contribution.

The contribution then flows through the existing UI registry path:

```text
InstalledProviderSlot
  -> SlotKernel.resolve_contributions(slot_type=SlotType.UI)
  -> build_slot_aware_ui_panels()
  -> UIPanelRegistry
```

If the provider contributes a route, watcher, governance policy, or a facet
belonging to another slot type, resolution fails closed with
`SlotConfigurationError`.

## 6. Acceptance Criteria

- A signed, installed UI provider contributes panel metadata through
  `build_slot_aware_ui_panels()`.
- The registry row includes provider panel id, workspace, zone,
  `component_module`, mode labels, and label.
- Existing UI registry tests still pass.
- Route facets remain restricted after UI panel expansion.
- Maturity posture remains:

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```

## 7. Verification Plan

Focused P10 UI:

```text
py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\contract\test_slot_ui_registry.py tests\unit\platform\workspace\test_ui_panel_registry.py -q
```

Slot API/CLI regression:

```text
py -3 -m pytest tests\contract\test_slot_api.py tests\cli\test_cli_slots.py -q
```

Governance:

```text
py -3 scripts\validate_alpha_maturity_honesty.py --file docs\progress\runtime-maturity.yaml
py -3 scripts\validate_alpha_maturity_honesty.py --file docs\architecture\adr-0069-slot-ui-panel-provider-facet.md
py -3 scripts\validate_alpha_maturity_honesty.py --file design\cdd\p10-ui-panel-provider-facet.md
py -3 scripts\validate_docs_maturity_claims.py
py -3 scripts\validate_governance_yaml_shape.py
py -3 scripts\validate_adr_index_completeness.py
git diff --check
```
