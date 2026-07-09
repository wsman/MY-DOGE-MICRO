# Slot Watcher Provider Facet Local Acceptance - 2026-07-09

## Scope

P10 opens only the `watchers` provider facet for installed, v3 package-signed,
operator-gated providers. Gateway routes and governance policies remain
restricted provider facets.

## Changes Verified

- `InstalledProviderSlot` now treats `SlotType.WATCHER` as provider-executable.
- Watcher providers may contribute `watchers` only.
- Watcher `on_event` callables are wrapped in slot permission context when
  runtime interception is enabled.
- Route facets remain rejected after the watcher expansion.
- `build_slot_aware_runtime_event_watcher()` consumes installed-provider
  watchers through the existing `SlotKernel` and `RuntimeEventWatcherMiddleware`
  path.
- P8 provider-isolation honesty remains unchanged:
  provider contribution objects are in-process and not OS/container/WASM
  isolated.

## Verification

```text
cmd.exe /c "cd /d D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO && set PYTHONPATH=src&& py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\unit\platform\slots\test_builtin_watcher_slot.py tests\contract\test_watcher_slot_parity.py -q"
=> 29 passed

cmd.exe /c "cd /d D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO && set PYTHONPATH=src&& py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\unit\platform\slots\test_builtin_watcher_slot.py tests\contract\test_watcher_slot_parity.py tests\contract\test_slot_api.py tests\cli\test_cli_slots.py -q"
=> 77 passed, 2 FastAPI deprecation warnings
```

## Non-Claims

- No route provider facets.
- No governance policy provider facets.
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
