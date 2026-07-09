# Slot Governance Policy Provider Facet Local Acceptance - 2026-07-09

## Scope

P10 opens only the `governance_policies` provider facet for installed, v3
package-signed, operator-gated providers. Gateway routes remain the only
restricted provider facet after this step.

## Changes Verified

- `InstalledProviderSlot` now treats `SlotType.GOVERNANCE` as
  provider-executable.
- Governance providers may contribute `governance_policies` only.
- Provider governance policy factories and returned checker methods are wrapped
  in slot permission context when runtime interception is enabled.
- Entitlement composition remains monotonic:
  - `can_execute` uses all checkers.
  - `requires_approval` uses any checker.
- Provider policies cannot re-enable forbidden tools.
- Route facets remain rejected after the governance expansion.
- P8 provider-isolation honesty remains unchanged: provider contribution
  objects are in-process and not OS/container/WASM isolated.

## Verification

```text
cmd.exe /c "cd /d D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO && set PYTHONPATH=src&& py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\unit\platform\slots\test_builtin_governance_slot.py tests\contract\test_governance_slot_parity.py -q"
=> 28 passed

cmd.exe /c "cd /d D:\Users\WSMAN\Desktop\Coding Task\MY-DOGE-MICRO && set PYTHONPATH=src&& py -3 -m pytest tests\unit\platform\slots\test_slot_provider_execution.py tests\unit\platform\slots\test_builtin_governance_slot.py tests\contract\test_governance_slot_parity.py tests\contract\test_slot_api.py tests\cli\test_cli_slots.py -q"
=> 76 passed, 2 FastAPI deprecation warnings
```

## Non-Claims

- No route provider facets.
- No marketplace/catalog behavior.
- No URL or upload install.
- No YAML manifests.
- No transitive dependency signing.
- No filesystem mediation or malicious-code containment.
- No OS/container/WASM provider sandbox.
- No tenant-isolation expansion.
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
