# Slot UI Panel Provider Facet Local Acceptance - 2026-07-09

## Scope

P10 opens only the `ui_panels` provider facet for installed, v3 package-signed,
operator-gated providers. Gateway routes, watchers, and governance policies
remain restricted provider facets.

## Changes Verified

- `InstalledProviderSlot` now treats `SlotType.UI` as provider-executable.
- UI providers may contribute `ui_panels` only.
- Route facets remain rejected after the UI expansion.
- `build_slot_aware_ui_panels()` consumes installed-provider UI panel metadata
  through the existing `SlotKernel` and `UIPanelRegistry` path.
- Frontend rendering remains static and allowlisted by `web/src/views/panelRegistry.ts`;
  P10 UI does not add dynamic component loading.
- P8 provider-isolation honesty remains unchanged:
  provider contribution objects are in-process and not OS/container/WASM
  isolated.

## Verification

```text
cmd.exe /c "cd /d D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO && set PYTHONPATH=src&& py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\contract\test_slot_ui_registry.py tests\unit\platform\workspace\test_ui_panel_registry.py -q"
=> 27 passed

cmd.exe /c "cd /d D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO && set PYTHONPATH=src&& py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\contract\test_slot_ui_registry.py tests\unit\platform\workspace\test_ui_panel_registry.py tests\contract\test_slot_api.py tests\cli\test_cli_slots.py -q"
=> 75 passed, 2 FastAPI deprecation warnings
```

## Non-Claims

- No route provider facets.
- No watcher provider facets.
- No governance policy provider facets.
- No dynamic frontend component loading.
- No marketplace/catalog behavior.
- No URL or upload install.
- No YAML manifests.
- No transitive dependency signing.
- No filesystem mediation or malicious-code containment.
- No OS/container/WASM provider sandbox.
- No external/operator gate closure.
- No maturity promotion.

## Open Gates

- `S017-003`
- `W3-live`
- `AUTH-prod`
- `S017-007`

## Posture

```yaml
production_ready: false
stable_declaration: forbidden
level_3_sdk_platform: experimental
```
