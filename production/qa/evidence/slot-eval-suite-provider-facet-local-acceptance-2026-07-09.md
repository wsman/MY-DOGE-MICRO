# Slot Eval Suite Provider Facet Local Acceptance - 2026-07-09

## Scope

P10 opens only the `eval_suites` provider facet for installed, v3
package-signed, operator-gated providers. Gateway routes, UI panels, watchers,
and governance policies remain restricted provider facets.

## Changes Verified

- `InstalledProviderSlot` now treats `SlotType.EVAL` as provider-executable.
- Eval providers may contribute `eval_suites` only.
- Route facets remain rejected after the eval expansion.
- `build_slot_aware_eval_suites()` consumes installed-provider eval suites
  through the existing `SlotKernel` and `EvalSuiteRegistry` path.
- P8 provider-isolation honesty remains unchanged:
  provider contribution objects are in-process and not OS/container/WASM
  isolated.

## Verification

```text
cmd.exe /c "cd /d D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO && set PYTHONPATH=src&& py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\unit\platform\slots\test_builtin_eval_slot.py tests\unit\eval\test_eval_suite_registry.py -q"
=> 25 passed

cmd.exe /c "cd /d D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO && set PYTHONPATH=src&& py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\unit\platform\slots\test_builtin_eval_slot.py tests\unit\eval\test_eval_suite_registry.py tests\contract\test_slot_api.py tests\cli\test_cli_slots.py -q"
=> 73 passed, 2 FastAPI deprecation warnings
```

## Non-Claims

- No route provider facets.
- No UI panel provider facets.
- No watcher provider facets.
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
